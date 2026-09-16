import bpy
import math
from pathlib import Path

# User-supplied reference upgrade layer.
# Geometry is rebuilt procedurally so it stays export-safe in the official ED exporter,
# while proportions/details follow the supplied Transformer.blend, ElectricalBox OBJ,
# electrical-control-box reference and 72.5/145 kV long-rod insulator CAD family.
# The final package replaces the placeholder PBR maps created here with the user's
# actual supplied texture maps.


def apply_prebuild_overrides(g):
    M = g["M"]
    DETAIL = g["DETAIL"]
    DESTROYED = g["DESTROYED"]
    box = g["box"]
    cyl = g["cyl"]
    torus = g["torus"]
    cable = g["cable"]
    sphere = g["sphere"]
    danger_sign = g["danger_sign"]
    equipment_label = g["equipment_label"]
    sign_plate = g["sign_plate"]
    edm_mat = g["edm_mat"]

    # Dedicated material names make it possible to inject the user's supplied PBR
    # textures into the final drop-in without disturbing the rest of the substation.
    xfmr_mat = bpy.data.materials.get("TPG_USER_Transformer") or edm_mat(
        "TPG_USER_Transformer", (.34, .36, .35), rough=.63, metal=.22,
        variation=.045, streak=True)
    panel_mat = bpy.data.materials.get("TPG_USER_ControlPanel") or edm_mat(
        "TPG_USER_ControlPanel", (.48, .50, .50), rough=.58, metal=.52,
        variation=.026, streak=True)
    panel_dark = bpy.data.materials.get("TPG_USER_ControlPanelDark") or edm_mat(
        "TPG_USER_ControlPanelDark", (.12, .13, .13), rough=.66, metal=.40,
        variation=.020, streak=True)
    ceramic_mat = bpy.data.materials.get("TPG_USER_LongRodCeramic") or edm_mat(
        "TPG_USER_LongRodCeramic", (.60, .66, .72), rough=.24, metal=.01,
        variation=.010, streak=False)

    def user_long_rod(name, loc, height, M_unused, detail=2, brown=False):
        """Long-rod porcelain/polymer profile based on the supplied 72.5/145 kV CAD family.

        Compared with the old station-post approximation this has a slimmer continuous
        core, many thin umbrella sheds, proper end fittings, and voltage-scaled shed count.
        """
        x, y, zc = loc
        h = max(.70, float(height))
        z0 = zc - h/2.0
        z1 = zc + h/2.0

        # 72.5 kV family is the shorter stack; 145 kV family is taller/more sheds.
        if h >= 2.65:
            nominal_sheds = 16 if h < 3.35 else 19
            core_r = .105
            major_r = .315
            minor_r = .275
        elif h >= 1.70:
            nominal_sheds = 11
            core_r = .095
            major_r = .275
            minor_r = .240
        else:
            nominal_sheds = 8
            core_r = .085
            major_r = .235
            minor_r = .205

        if detail >= 2:
            sheds = nominal_sheds
            seg = 36
        elif detail == 1:
            sheds = max(7, int(round(nominal_sheds * .72)))
            seg = 24
        else:
            sheds = max(4, int(round(nominal_sheds * .46)))
            seg = 14

        # Continuous ceramic trunk, intentionally visible between sheds like the CAD model.
        usable0 = z0 + .18
        usable1 = z1 - .22
        cyl(name + "_CORE", (x, y, (usable0+usable1)/2), core_r,
            usable1-usable0, ceramic_mat, seg)

        # Thin umbrella sheds. Cone frusta reproduce the CAD's long-rod silhouette rather
        # than the old bead/ring look. Slight major/minor alternation adds realistic creepage.
        step = (usable1-usable0) / max(1, sheds)
        for i in range(sheds):
            zz = usable0 + (i+.5)*step
            r = major_r if i % 3 != 2 else minor_r
            thick = min(.065, step*.38)
            bpy.ops.mesh.primitive_cone_add(
                vertices=seg,
                radius1=r,
                radius2=core_r*1.20,
                depth=thick,
                location=(x, y, zz),
            )
            o = bpy.context.object
            o.name = f"{name}_SHED_{i:02d}"
            o.data.materials.append(ceramic_mat)
            for p in o.data.polygons:
                p.use_smooth = abs(p.normal.z) < .92
            if detail >= 1:
                bpy.ops.mesh.primitive_torus_add(
                    major_radius=max(core_r*1.12, r*.52),
                    minor_radius=.018 if detail >= 2 else .014,
                    major_segments=seg,
                    minor_segments=8 if detail >= 2 else 5,
                    location=(x, y, zz-thick*.18),
                )
                lip = bpy.context.object
                lip.name = f"{name}_SHEDLIP_{i:02d}"
                lip.data.materials.append(ceramic_mat)
                for p in lip.data.polygons: p.use_smooth = True

        # Ball/socket and galvanized end fittings from the supplied assembly family.
        cyl(name + "_BOTTOM_FERRULE", (x,y,z0+.10), core_r*1.50,.20,M["galv"],24)
        cyl(name + "_BOTTOM_PIN", (x,y,z0-.05), core_r*.58,.28,M["galv"],18)
        sphere(name + "_TOP_BALL", (x,y,z1+.02), core_r*1.42, M["galv"], 24, 12)
        cyl(name + "_TOP_STEM", (x,y,z1+.19), core_r*.62,.34,M["galv"],18)
        if detail >= 1:
            # U-shaped socket/clevis cue visible on the supplied CAD renders.
            torus(name + "_TOP_SOCKET", (x,y,z1+.38), core_r*1.50, core_r*.30,
                  M["galv"], rot=(math.radians(90),0,0), major_segments=24, minor_segments=8)
            box(name + "_TOP_SOCKET_CUT", (x,y,z1+.38),
                (core_r*3.2, core_r*.90, core_r*1.35), M["galv"], .012)
        return bpy.context.object

    # All breakers, CT/PTs, arresters, transformer bushings and line-entry strings call
    # this global at execution time, so this swaps the entire yard to the CAD-driven family.
    g["insulator_stack"] = user_long_rod

    def panel_box(name, x, y, z, sx=1.35, sy=.65, sz=2.15, face_axis="-Y", green=False):
        mat = M["green"] if green else panel_mat
        box(name + "_CAB", (x,y,z), (sx,sy,sz), mat, .055)
        # Raised door/panel face, perimeter gasket, hinges, latch, analog meter and buttons.
        fy = y - sy/2 - .025 if face_axis == "-Y" else y + sy/2 + .025
        box(name + "_DOOR", (x,fy,z+.03), (sx*.88,.055,sz*.86), panel_mat, .020)
        if DETAIL >= 1:
            # gasket rails
            for zz in (z-sz*.34, z+sz*.34):
                box(name + f"_GASK_H_{zz:.2f}", (x,fy-.032,zz),(sx*.72,.018,.025),panel_dark,.002)
            for xx in (x-sx*.34, x+sx*.34):
                box(name + f"_GASK_V_{xx:.2f}", (xx,fy-.032,z),(.025,.018,sz*.66),panel_dark,.002)
            for hi,zz in enumerate((z-sz*.24,z+sz*.24)):
                cyl(name + f"_HINGE_{hi}",(x+sx*.41,fy-.055,zz),.045,.18,M["steel"],12,rot=(math.radians(90),0,0))
            box(name + "_LATCH",(x-sx*.28,fy-.075,z),(0.10,.05,.28),M["steel"],.012)
        if DETAIL >= 2:
            cyl(name + "_METER",(x,fy-.075,z+sz*.20),.18,.07,M["white"],24,rot=(math.radians(90),0,0))
            cyl(name + "_METER_RIM",(x,fy-.110,z+sz*.20),.205,.035,panel_dark,24,rot=(math.radians(90),0,0))
            for bi,(bx,bz,bm) in enumerate(((x-.22,z-.28,M["red"]),(x,z-.28,M["green"]),(x+.22,z-.28,M["yellow"]))):
                cyl(name + f"_PB_{bi}",(bx,fy-.080,bz),.065,.055,bm,16,rot=(math.radians(90),0,0))
        danger_sign(name + "_WARN", (x,fy-.070,z-sz*.25), M, width=sx*.60, height=.32)
        return name

    old_control_building = g["control_building"]
    def upgraded_control_building():
        old_control_building()
        # Replace the old flat-panel feel with dimensional cabinets inspired by the
        # supplied electrical-control-box model and ElectricalBox OBJ.
        bx, by = -41, -27
        wall_y = by - 6.34
        for i,(dx,scale) in enumerate(((-7.1,.90),(-5.35,.82),(-3.75,.74))):
            panel_box(f"USER_CTRL_PANEL_{i}", bx+dx, wall_y, 1.32,
                      sx=1.40*scale, sy=.48, sz=2.25*scale)
            # conduit and junction run into wall/grade
            cable(f"USER_CTRL_CONDUIT_{i}",[(bx+dx,wall_y-.28,.20),(bx+dx,wall_y-.28,2.45),(bx+dx+.45,wall_y-.28,2.75)],M["galv"],.035)
        # Yard-side freestanding control/meter boxes, positioned beside existing service cabinets.
        panel_box("USER_YARD_METERBOX_A",-20.2,-22.8,1.20,sx=1.55,sy=.78,sz=2.30)
        panel_box("USER_YARD_METERBOX_B",-15.8,-21.2,1.05,sx=1.20,sy=.70,sz=1.95,green=True)
        if DETAIL >= 1:
            for j,(px,py) in enumerate(((-21.0,-20.5),(-16.5,-19.0))):
                cyl(f"USER_PANEL_PIPE_{j}",(px,py,.72),.055,1.25,M["galv"],16)
                cyl(f"USER_PANEL_PIPE_CAP_{j}",(px,py,1.37),.080,.10,M["galv"],16)
    g["control_building"] = upgraded_control_building

    def transformer_user(cx, cy, idx, damaged=False):
        """Rebuilt power transformer using the supplied Transformer.blend as visual reference.

        Uses a lower rectangular tank, external corrugated radiator banks, conservator,
        real long-rod bushings, top manifolds, cooling fans, marshalling cabinet and
        cable boxes. The old transformer function is completely replaced.
        """
        z0 = .80
        body = M["burnt"] if damaged else xfmr_mat
        dark = M["burnt"] if damaged else M["xfmr_dark"]

        # Lower carriage/rails and main oil tank.
        for ry in (-1.65,1.65):
            box(f"UXF{idx}_RAIL_{ry}",(cx,cy+ry,z0+.16),(8.4,.24,.24),M["steel"],.025)
        box(f"UXF{idx}_LOWER",(cx,cy,z0+.72),(7.8,4.55,1.15),body,.12)
        box(f"UXF{idx}_TANK",(cx,cy,z0+3.00),(7.45,4.35,4.55),body,.18)
        # Shoulder/top cover breaks up the slab silhouette from the old version.
        box(f"UXF{idx}_SHOULDER",(cx,cy,z0+5.23),(7.85,4.65,.42),body,.09)
        box(f"UXF{idx}_TOP",(cx,cy,z0+5.52),(8.12,4.92,.18),M["steel"] if damaged else body,.055)

        if DETAIL >= 1:
            # Realistic stiffeners/ribs on tank walls.
            for xx in (-3.20,-2.15,-1.08,0,1.08,2.15,3.20):
                box(f"UXF{idx}_RIB_F_{xx}",(cx+xx,cy-2.23,z0+3.0),(.12,.16,4.05),dark,.015)
                box(f"UXF{idx}_RIB_R_{xx}",(cx+xx,cy+2.23,z0+3.0),(.12,.16,4.05),dark,.015)

        # Separate radiator banks with deep corrugated fins, headers and fan cages.
        for side in (-1,1):
            sy = cy + side*3.10
            for bank in range(4):
                bx = cx - 2.75 + bank*1.82
                box(f"UXF{idx}_RAD_FRAME_{side}_{bank}",(bx,sy,z0+2.85),(1.55,.32,4.70),dark,.030)
                if DETAIL >= 1:
                    fins = 10 if DETAIL >= 2 else 5
                    for fi in range(fins):
                        fx = bx - .66 + fi*(1.32/max(1,fins-1))
                        box(f"UXF{idx}_FIN_{side}_{bank}_{fi}",(fx,sy+side*.20,z0+2.85),(.040,.18,4.36),body,.003)
                if DETAIL >= 2 and bank in (0,2):
                    g["fan_guard"](f"UXF{idx}_FAN_{side}_{bank}",(bx,sy+side*.40,z0+2.75),.52,M,DETAIL)
            cyl(f"UXF{idx}_HDR_TOP_{side}",(cx,sy,z0+4.92),.135,7.2,M["steel"],20,rot=(0,math.radians(90),0))
            cyl(f"UXF{idx}_HDR_LOW_{side}",(cx,sy,z0+.86),.135,7.2,M["steel"],20,rot=(0,math.radians(90),0))
            for bank in range(4):
                bx=cx-2.75+bank*1.82
                cyl(f"UXF{idx}_RAD_PIPE_T_{side}_{bank}",(bx,sy,z0+4.92),.075,.75,M["steel"],14,rot=(math.radians(90),0,0))
                cyl(f"UXF{idx}_RAD_PIPE_B_{side}_{bank}",(bx,sy,z0+.86),.075,.75,M["steel"],14,rot=(math.radians(90),0,0))

        # Conservator, Buchholz pipe and expansion plumbing.
        cyl(f"UXF{idx}_CONS",(cx,cy+3.30,z0+6.45),.68,5.25,body,36,rot=(0,math.radians(90),0))
        for xx in (-1.85,1.85):
            box(f"UXF{idx}_CONS_LEG_{xx}",(cx+xx,cy+3.02,z0+5.72),(.20,.26,1.25),M["galv"],.022)
        cable(f"UXF{idx}_BUCHHOLZ",[(cx+2.20,cy+2.90,z0+6.20),(cx+2.55,cy+2.10,z0+5.62),(cx+2.35,cy+1.35,z0+5.42)],M["steel"],.085)
        cyl(f"UXF{idx}_BUCHHOLZ_BODY",(cx+2.46,cy+2.45,z0+5.90),.16,.48,M["galv"],18,rot=(math.radians(65),0,0))

        # 145 kV-looking HV long-rod bushings; 72.5 kV/secondary shorter row.
        for phase,dx in enumerate((-2.35,0,2.35)):
            bx=cx+dx; by=cy-.68
            user_long_rod(f"UXF{idx}_HV_{phase}",(bx,by,z0+7.20),3.15,M,DETAIL,brown=True)
            cyl(f"UXF{idx}_HV_STUD_{phase}",(bx,by,z0+8.93),.075,.40,M["copper"],18)
            if DETAIL >= 1:
                torus(f"UXF{idx}_HV_CORONA_{phase}",(bx,by,z0+8.72),.37,.038,M["alum"],major_segments=28,minor_segments=8)
            equipment_label(f"UXF{idx}_PH_{phase}",(bx,cy-2.27,z0+4.70),M,("A","B","C")[phase],
                            width=.42,height=.34,text_size=.20,plate="blue",ink="white")
        for phase,dx in enumerate((-2.70,-.90,.90,2.70)):
            bx=cx+dx; by=cy+1.00
            user_long_rod(f"UXF{idx}_LV_{phase}",(bx,by,z0+6.58),1.95,M,DETAIL,brown=False)
            cyl(f"UXF{idx}_LV_STUD_{phase}",(bx,by,z0+7.72),.065,.30,M["copper"],16)

        # Top bus jumpers/manifold cues.
        if DETAIL >= 1:
            for phase,dx in enumerate((-2.35,0,2.35)):
                cable(f"UXF{idx}_TOP_JUMPER_{phase}",[(cx+dx,cy-.68,z0+8.95),(cx+dx,cy-1.60,z0+9.20),(cx+dx,cy-2.15,z0+9.05)],M["alum"],.045)

        # Transformer-mounted terminal/cable boxes and a real marshalling cabinet.
        panel_box(f"UXF{idx}_MARSH",cx-2.25,cy-2.58,z0+1.72,sx=1.35,sy=.62,sz=2.25)
        panel_box(f"UXF{idx}_TERM",cx+2.45,cy-2.55,z0+1.25,sx=1.05,sy=.58,sz=1.50)
        if DETAIL >= 1:
            for pi,px in enumerate((cx-3.05,cx+3.00)):
                cyl(f"UXF{idx}_SIDE_CONDUIT_{pi}",(px,cy-2.45,z0+.72),.050,1.10,M["galv"],14)

        # Gauges/nameplate/drain/grounding details.
        sign_plate(f"UXF{idx}_NAMEPLATE",(cx,cy-2.235,z0+3.00),2.45,1.10,M["white"],
                   f"TPG GRID  T-{idx}",M["black"],M,text_size=.17,depth=.006,
                   subtext="POWER TRANSFORMER",subtext_mat=M["black"],subtext_size=.11)
        if DETAIL >= 2:
            for gi,gx in enumerate((-1.05,0,1.05)):
                cyl(f"UXF{idx}_GAUGE_{gi}",(cx+gx,cy-2.33,z0+1.20),.23,.075,M["white"],24,rot=(math.radians(90),0,0))
                cyl(f"UXF{idx}_GAUGE_RIM_{gi}",(cx+gx,cy-2.38,z0+1.20),.255,.035,panel_dark,24,rot=(math.radians(90),0,0))
            cyl(f"UXF{idx}_DRAIN",(cx+3.46,cy-2.37,z0+.46),.14,.50,M["steel"],16,rot=(math.radians(90),0,0))
            cable(f"UXF{idx}_GROUND",[(cx-3.52,cy+2.12,z0+.34),(cx-3.95,cy+2.85,.18)],M["copper"],.035)
            danger_sign(f"UXF{idx}_DANGER",(cx+2.45,cy-2.235,z0+4.12),M,width=1.28,height=.65)

        if damaged:
            box(f"UXF{idx}_SCORCH",(cx,cy-2.31,z0+3.15),(6.8,.045,3.2),M["soot"],.004)
            box(f"UXF{idx}_OILPOOL",(cx+1.0,cy-4.45,.14),(7.8,4.7,.035),M["oil"],.003)
            for k in range(3):
                cable(f"UXF{idx}_HANG_{k}",[(cx-2.2+k*2.2,cy-.65,z0+8.6),(cx-1.6+k*2.0,cy-1.7,z0+5.7),(cx-2.4+k*2.0,cy-2.6,z0+3.9)],M["black"],.052)

    g["transformer"] = transformer_user
    print("TPG user-asset visual overrides installed: transformer replacement, long-rod insulators, dimensional electrical/control boxes")
