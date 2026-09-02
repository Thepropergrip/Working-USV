import bpy, math, os, random
from tpg_substation_common import *

DESTROYED = os.environ.get("TPG_SUB_DESTROYED","0") == "1"
LOD = int(os.environ.get("TPG_SUB_LOD","0"))
DETAIL = 2 if LOD==0 else (1 if LOD==1 else 0)

bpy.ops.wm.read_factory_settings(use_empty=True)
M=mats()

def base():
    box("YARD_GRAVEL",(0,0,-.18),(120,90,.36),M["gravel"],.0,coll=True)
    # perimeter concrete curb / transformer containment pads
    box("CTRL_PAD",(-39,-28,.10),(19,13,.20),M["concrete"],.03,coll=True)
    for x in (-20,20):
        box(f"XFMR_PAD_{x}",(x,0,.18),(18,14,.36),M["concrete"],.05,coll=True)
        box(f"XFMR_BUND_{x}",(x,0,.31),(20,16,.22),M["concrete"],.02)
    # access road and cable trench covers
    box("ACCESS_ROAD",(0,-35,.04),(110,9,.10),M["concrete"],.01)
    for y in (-18,-8,8,18):
        box(f"TRENCH_{y}",(0,y,.08),(92,1.0,.14),M["concrete"],.015)
        if DETAIL>=1:
            for x in range(-44,45,4):
                box(f"TRENCH_JOINT_{y}_{x}",(x,y,.158),(.05,.96,.018),M["steel"],.0)

def fence():
    if DETAIL==0:
        for y in (-43.5,43.5):
            box(f"FENCE_{y}",(0,y,1.35),(118,.06,2.7),M["galv"],.01)
        for x in (-58.5,58.5):
            box(f"FENCE_{x}",(x,0,1.35),(.06,87,2.7),M["galv"],.01)
        return
    # posts + rails + wire mesh suggestion
    for y in (-43.5,43.5):
        for x in range(-58,59,4):
            cyl(f"FPOST_{x}_{y}",(x,y,1.45),.055,2.9,M["galv"],10)
        for z in (.55,1.55,2.55):
            box(f"FRAIL_{y}_{z}",(0,y,z),(116,.045,.045),M["galv"],.004)
        if DETAIL>=2:
            for x in range(-56,57,2):
                cable(f"FMESH_V_{y}_{x}",[(x,y,.25),(x,y,2.65)],M["galv"],.006,0)
    for x in (-58.5,58.5):
        for y in range(-40,41,4):
            cyl(f"FPOST_{x}_{y}",(x,y,1.45),.055,2.9,M["galv"],10)
        for z in (.55,1.55,2.55):
            box(f"FRAIL_{x}_{z}",(x,0,z),(.045,84,.045),M["galv"],.004)
    # vehicle gate
    box("GATE_LEFT",(-7,-43.6,1.45),(13,.08,2.7),M["galv"],.01)
    box("GATE_RIGHT",(7,-43.6,1.45),(13,.08,2.7),M["galv"],.01)
    if DETAIL>=2:
        text_obj("DANGER  HIGH VOLTAGE","GATE_WARNING",(0,-43.72,1.65),.34,M["red"],extrude=.009)

def control_building():
    x,y=-39,-28
    box("CTRL_BUILDING",(x,y,2.7),(17,11,5.4),M["xfmr_dark"],.06,coll=True)
    box("CTRL_ROOF",(x,y,5.62),(17.8,11.8,.44),M["roof"],.05,coll=True)
    # doors / windows / utility signage
    box("CTRL_DOOR",(x+5.4,y-5.54,1.45),(2.05,.12,2.9),M["green"],.025)
    box("CTRL_DOORFRAME",(x+5.4,y-5.64,1.45),(2.28,.05,3.12),M["galv"],.015)
    box("CTRL_WINDOW",(x-2.8,y-5.56,2.55),(3.2,.10,1.5),M["black"],.02)
    text_obj("SUBSTATION CONTROL","CTRL_LABEL",(x,y-5.67,4.42),.42,M["white"],extrude=.010)
    text_obj("AUTHORIZED PERSONNEL ONLY","CTRL_WARN",(x+4.2,y-5.69,.55),.18,M["yellow"],extrude=.006)
    # exterior cabinets and HVAC
    for i,dx in enumerate((-5.5,-3.5,-1.5)):
        box(f"CTRL_CAB_{i}",(x+dx,y+5.7,1.15),(1.35,.75,2.3),M["galv"],.035)
        if DETAIL>=2:
            for z in (.55,1.05,1.55):
                box(f"CTRL_CAB_LOUVER_{i}_{z}",(x+dx,y+6.085,z),(1.0,.025,.06),M["black"],.004)
    for i,dx in enumerate((2.8,5.6)):
        box(f"HVAC_{i}",(x+dx,y+5.72,1.15),(2.25,1.05,2.0),M["xfmr"],.05)
        fan_guard(f"HVAC_FAN_{i}",(x+dx,y+6.27,1.25),.58,M,DETAIL)
        if DETAIL>=2:
            for j in range(10):
                box(f"HVAC_FIN_{i}_{j}",(x+dx-0.85+j*.19,y+6.28,.55),(.10,.025,.55),M["steel"],.002)
    # roof vents/conduit
    for i,dx in enumerate((-5,-1.5,2,5)):
        cyl(f"ROOFVENT_{i}",(x+dx,y,6.15),.22,1.0,M["galv"],14)
        cyl(f"ROOFVENTCAP_{i}",(x+dx,y,6.68),.34,.10,M["galv"],14)

def transformer(cx,cy,idx,damaged=False):
    z=.8
    body_mat=M["burnt"] if damaged else M["xfmr"]
    # main tank and bolted top cover
    box(f"XF{idx}_TANK",(cx,cy,z+2.7),(7.6,4.7,5.4),body_mat,.14,coll=True)
    box(f"XF{idx}_TOP",(cx,cy,z+5.48),(8.1,5.15,.28),body_mat,.06)
    if DETAIL>=2:
        for x in (-3.5,-1.75,0,1.75,3.5):
            for y in (-2.15,2.15):
                cyl(f"XF{idx}_TOPBOLT_{x}_{y}",(cx+x,cy+y,z+5.67),.045,.08,M["steel"],8)
    # conservator tank
    cyl(f"XF{idx}_CONS",(cx,cy+3.2,z+6.35),.75,5.0,body_mat,24,rot=(0,math.radians(90),0))
    box(f"XF{idx}_CONS_BRKT",(cx,cy+2.72,z+5.6),(4.7,.30,1.0),M["galv"],.03)
    # radiators and fans on both sides
    for side,sy in ((-1,-3.15),(1,3.15)):
        for bank in range(5):
            bx=cx-3.0+bank*1.5
            box(f"XF{idx}_RAD_{side}_{bank}",(bx,cy+sy,z+2.65),(1.15,.34,4.75),body_mat,.025)
            if DETAIL>=1:
                for fin in range(9 if DETAIL>=2 else 4):
                    fx=bx-.48+fin*(.96/(8 if DETAIL>=2 else 3))
                    box(f"XF{idx}_FIN_{side}_{bank}_{fin}",(fx,cy+sy+side*.20,z+2.65),(.035,.18,4.35),M["steel"],.002)
            if DETAIL>=2 and bank in (1,3):
                fan_guard(f"XF{idx}_FAN_{side}_{bank}",(bx,cy+sy+side*.37,z+2.65),.48,M,DETAIL)
        # headers and pipes
        cyl(f"XF{idx}_HEADER_TOP_{side}",(cx,cy+sy,z+4.8),.12,7.3,M["steel"],14,rot=(0,math.radians(90),0))
        cyl(f"XF{idx}_HEADER_LOW_{side}",(cx,cy+sy,z+1.0),.12,7.3,M["steel"],14,rot=(0,math.radians(90),0))
    # bushings, phases, corona rings
    for i,dx in enumerate((-2.4,0,2.4)):
        bx=cx+dx; by=cy-.6
        insulator_stack(f"XF{idx}_HV_BUSH_{i}",(bx,by,z+7.2),3.0,M,DETAIL,brown=True)
        if DETAIL>=1: torus(f"XF{idx}_CORONA_{i}",(bx,by,z+8.55),.34,.035,M["alum"],major_segments=18)
        text_obj(("A","B","C")[i],f"XF{idx}_PHASE_{i}",(bx,cy-2.39,z+4.7),.24,M["white"],extrude=.006)
    for i,dx in enumerate((-2.7,-.9,.9,2.7)):
        insulator_stack(f"XF{idx}_LV_BUSH_{i}",(cx+dx,cy+1.0,z+6.65),1.85,M,DETAIL,brown=False)
    # gauges, nameplate, drain, grounding straps
    box(f"XF{idx}_NAMEPLATE",(cx,cy-2.39,z+2.65),(2.15,.035,1.05),M["white"],.004)
    text_obj(f"TPG GRID  T-{idx}\nPOWER TRANSFORMER",f"XF{idx}_NPTEXT",(cx,cy-2.425,z+2.72),.18,M["black"],extrude=.004)
    if DETAIL>=2:
        for gi,gx in enumerate((-1.1,0,1.1)):
            cyl(f"XF{idx}_GAUGE_{gi}",(cx+gx,cy-2.47,z+1.55),.26,.08,M["white"],20,rot=(math.radians(90),0,0))
            cyl(f"XF{idx}_GAUGEHUB_{gi}",(cx+gx,cy-2.52,z+1.55),.035,.06,M["black"],10,rot=(math.radians(90),0,0))
        cyl(f"XF{idx}_DRAIN",(cx+3.55,cy-2.5,z+.55),.15,.55,M["steel"],14,rot=(math.radians(90),0,0))
        cable(f"XF{idx}_GROUND",[(cx-3.6,cy+2.4,z+.4),(cx-4.0,cy+3.0,.2)],M["copper"],.035)
        # service/warning decals
        text_obj("DANGER","XF{}_DANGER".format(idx),(cx+2.6,cy-2.43,z+4.0),.22,M["red"],extrude=.006)
        text_obj("OIL FILLED","XF{}_OIL".format(idx),(cx-2.7,cy-2.43,z+.85),.16,M["yellow"],extrude=.005)
    if damaged:
        # rupture, scorch and hanging conductor cues
        box(f"XF{idx}_SCORCH",(cx,cy-2.41,z+3.2),(6.5,.05,3.0),M["soot"],.005)
        for k in range(3):
            cable(f"XF{idx}_HANG_{k}",[(cx-2+k*2,cy-.6,z+8.4),(cx-1.5+k*2,cy-1.8,z+5.4),(cx-2.2+k*2,cy-2.7,z+3.7)],M["black"],.05)
        box(f"XF{idx}_OILPOOL",(cx+1.2,cy-4.5,.17),(7.5,4.5,.035),M["oil"],.005)

def support_gantry(name,x,y,w=12,h=10):
    lattice_post(name+"_L",x-w/2,y,.2,h,M,DETAIL,.80)
    lattice_post(name+"_R",x+w/2,y,.2,h,M,DETAIL,.80)
    box(name+"_TOP",(x,y,h+.15),(w+.8,.24,.24),M["galv"],.015)
    if DETAIL>=1:
        box(name+"_MID",(x,y,h-1.1),(w+.2,.14,.14),M["galv"],.012)
    return h+.15

def breaker(name,x,y):
    # three-pole dead-tank breaker arrangement
    for p,dx in enumerate((-1.6,0,1.6)):
        box(f"{name}_BASE_{p}",(x+dx,y,.25),(1.15,1.1,.5),M["concrete"],.03)
        cyl(f"{name}_TANK_{p}",(x+dx,y,1.65),.52,2.35,M["xfmr"],20)
        insulator_stack(f"{name}_INS_L_{p}",(x+dx-.30,y,3.75),1.95,M,DETAIL)
        insulator_stack(f"{name}_INS_R_{p}",(x+dx+.30,y,3.75),1.95,M,DETAIL)
        if DETAIL>=2:
            box(f"{name}_MECH_{p}",(x+dx,y-.70,1.15),(.78,.54,.92),M["galv"],.025)
            text_obj(("A","B","C")[p],f"{name}_PH_{p}",(x+dx,y-.995,1.35),.20,M["blue"],extrude=.005)

def disconnect(name,x,y,z=5.0,open_phase=False):
    # elevated three-pole air-break disconnector
    for p,dx in enumerate((-1.6,0,1.6)):
        box(f"{name}_PED_{p}",(x+dx,y,.22),(.70,.70,.44),M["concrete"],.02)
        insulator_stack(f"{name}_POSTA_{p}",(x+dx-.34,y,z/2+.35),z-.7,M,DETAIL)
        insulator_stack(f"{name}_POSTB_{p}",(x+dx+.34,y,z/2+.35),z-.7,M,DETAIL)
        angle=math.radians(24 if (open_phase and p==1) else 0)
        box(f"{name}_BLADE_{p}",(x+dx,y,z+.12),(.95,.08,.08),M["alum"],.008,rot=(0,angle,0))
        if DETAIL>=2:
            cyl(f"{name}_PIVOT_{p}",(x+dx-.39,y,z+.12),.10,.13,M["copper"],12,rot=(math.radians(90),0,0))

def instrument_transformer(name,x,y,kind="CT"):
    for p,dx in enumerate((-1.5,0,1.5)):
        box(f"{name}_PAD_{p}",(x+dx,y,.18),(.82,.82,.36),M["concrete"],.02)
        insulator_stack(f"{name}_INS_{p}",(x+dx,y,2.45),3.65,M,DETAIL,brown=(kind=="PT"))
        if kind=="CT":
            torus(f"{name}_HEAD_{p}",(x+dx,y,4.45),.40,.16,M["xfmr"],major_segments=18,minor_segments=8)
        else:
            cyl(f"{name}_HEAD_{p}",(x+dx,y,4.25),.38,.85,M["xfmr"],18)
        if DETAIL>=2:
            box(f"{name}_BOX_{p}",(x+dx,y-.48,.75),(.56,.42,.70),M["galv"],.02)

def arresters(name,x,y):
    for p,dx in enumerate((-1.5,0,1.5)):
        box(f"{name}_PAD_{p}",(x+dx,y,.15),(.55,.55,.30),M["concrete"],.02)
        insulator_stack(f"{name}_AR_{p}",(x+dx,y,2.1),3.5,M,DETAIL)
        cable(f"{name}_GROUND_{p}",[(x+dx,y,0.5),(x+dx+.35,y+.35,.08)],M["copper"],.025)

def buswork():
    # major gantries and rigid bus bars
    for y in (-20,-10,10,20):
        support_gantry(f"GANTRY_{y}",0,y,94,10.5)
    phases=(-2.2,0,2.2)
    for y in (-20,-10,10,20):
        for p,zoff in enumerate(phases):
            cable(f"BUS_{y}_{p}",[(-44,y,10.7+zoff*.10),(0,y,10.9+zoff*.10),(44,y,10.7+zoff*.10)],M["alum"],.065 if DETAIL>=1 else .09)
    # vertical drops into bays
    for x in (-40,-24,-8,8,24,40):
        for y in (-20,20):
            for p,dx in enumerate((-1.5,0,1.5)):
                cable(f"DROP_{x}_{y}_{p}",[(x+dx,y,10.7),(x+dx,y*.72,7.2),(x+dx,y*.62,5.4)],M["alum"],.045 if DETAIL>=1 else .07)

def switchyard():
    # six densely populated bays
    xs=(-40,-24,-8,8,24,40)
    for i,x in enumerate(xs):
        breaker(f"BRK_N_{i}",x,13.2)
        disconnect(f"DS_N_{i}",x,6.6,5.2,open_phase=(i==4))
        instrument_transformer(f"CT_N_{i}",x,2.0,"CT")
        arresters(f"SA_N_{i}",x,-2.5)
        instrument_transformer(f"PT_S_{i}",x,-8.0,"PT")
        disconnect(f"DS_S_{i}",x,-14.0,5.2,open_phase=False)
        if DETAIL>=1:
            # local marshalling kiosk, cable conduit and bay ID
            box(f"MK_{i}",(x+3.0,10.0,1.0),(1.25,.85,2.0),M["galv"],.03)
            text_obj(f"BAY {i+1:02d}",f"BAYLBL_{i}",(x+3.0,9.55,1.25),.16,M["black"],extrude=.004)
            cable(f"MKCONDUIT_{i}",[(x+3.0,10.0,.1),(x+3.0,7.0,.08),(x,6.0,.08)],M["steel"],.035)

def towers_and_lines():
    # line entrance towers at north edge
    for x in (-32,0,32):
        lattice_post(f"LINE_TOWER_{x}",x,36,.2,18,M,DETAIL,2.0)
        box(f"LINE_ARM_{x}",(x,36,16.2),(9,.35,.25),M["galv"],.02)
        for p,dx in enumerate((-3.5,0,3.5)):
            insulator_stack(f"LINE_INS_{x}_{p}",(x+dx,36,14.7),2.4,M,DETAIL)
            cable(f"LINE_COND_{x}_{p}",[(x+dx,36,13.5),(x+dx,28,12.0),(x+dx,20,10.8)],M["alum"],.055)
    if DETAIL>=2:
        # shield wire and tower labels
        for x in (-32,0,32):
            cable(f"SHIELD_{x}",[(x,36,18.2),(x,28,16.0),(x,20,12.0)],M["steel"],.028)
            text_obj(f"L{x:+03d}",f"TOWER_ID_{x}",(x,35.0,3.0),.22,M["white"],extrude=.005)

def yard_details():
    if DETAIL==0: return
    rng=random.Random(11431)
    # ground grid inspection wells, fire extinguishers, bollards, lights
    for i in range(16):
        x=rng.uniform(-50,50); y=rng.uniform(-32,30)
        cyl(f"GROUND_WELL_{i}",(x,y,.11),.24,.12,M["steel"],14)
    for i,(x,y) in enumerate(((-28,4),(28,4),(-28,-4),(28,-4),(-48,-25))):
        cyl(f"FIREPOST_{i}",(x,y,.85),.07,1.7,M["red"],12)
        box(f"FIREBOX_{i}",(x,y,1.5),(.5,.28,.75),M["red"],.03)
    for i,x in enumerate(range(-48,49,16)):
        cyl(f"LIGHTPOLE_{i}",(x,-31,4.0),.09,8.0,M["galv"],12)
        box(f"LIGHTHEAD_{i}",(x,-30.6,7.8),(1.0,.65,.28),M["black"],.03,rot=(math.radians(-12),0,0))
    if DETAIL>=2:
        # dense little ID plates / stickers
        for i,x in enumerate(range(-44,45,8)):
            box(f"IDPOST_{i}",(x,25,.65),(.06,.06,1.3),M["galv"],.004)
            box(f"IDPLATE_{i}",(x,24.94,1.0),(.65,.035,.35),M["white"],.003)
            text_obj(f"{100+i}",f"IDTEXT_{i}",(x,24.90,1.0),.12,M["black"],extrude=.003)

def destroyed_overlays():
    if not DESTROYED: return
    # collapsed lattice, snapped bus, scorched gravel, fractured control building edge
    box("BURN_FIELD",(16,3,.03),(34,24,.035),M["soot"],.0)
    for i,x in enumerate((8,24,40)):
        box(f"FALLEN_STEEL_{i}",(x,9,1.5),(13,.30,.30),M["burnt"],.02,rot=(0,math.radians(15+i*8),math.radians(8+i*4)))
        cable(f"SNAPPED_BUS_{i}",[(x-5,12,7),(x,8,3.5),(x+6,5,.4)],M["black"],.07)
    box("CTRL_DAMAGE_PATCH",(-31.0,-28,3.0),(1.0,9.0,4.0),M["soot"],.02,rot=(0,math.radians(8),0))
    box("CTRL_ROOF_FALL",(-34,-25,4.2),(7,5,.35),M["burnt"],.04,rot=(math.radians(8),math.radians(-10),math.radians(6)))

base()
fence()
control_building()
transformer(-20,0,1,DESTROYED)
transformer(20,0,2,DESTROYED)
buswork()
switchyard()
towers_and_lines()
yard_details()
destroyed_overlays()

# Dedicated simple collision masses for large objects/yard limits; visual mesh collision flags are already set on major masses.
box("COLL_CTRL",(-39,-28,2.7),(17,11,5.4),None,0,coll=True)
for x in (-20,20):
    box(f"COLL_XFMR_{x}",(x,0,3.0),(9,7,6.0),None,0,coll=True)

# World origin helper kept tiny and hidden below grade; ensures stable bounds.
box("ORIGIN_HELPER",(0,0,-.45),(.1,.1,.1),M["gravel"],0)

print(f"TPG substation build complete destroyed={DESTROYED} lod={LOD} detail={DETAIL}")
