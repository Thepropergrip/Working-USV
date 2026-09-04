import runpy, math
from pathlib import Path
import bpy
import numpy as np

# Build the corrected FBX/wheel-rig version first.
ns = runpy.run_path("edm-jobs/build_tpg_tacoma_quality_patch2.py", run_name="__main__")
M = ns['M']; box = ns['box']; cyl = ns['cyl']; torus = ns['torus']; text_obj = ns['text_obj']; mat = ns['mat']
TEXDIR = ns['TEXDIR']; MAT_DESCS = ns['MAT_DESCS']; LOD = ns['LOD']

# The user's photos show the low-profile rack on the cab, not an invented second rack on the camper shell.
for o in list(bpy.data.objects):
    if o.name.startswith(('RACK_RAIL_1_', 'RACK_FOOT_1_', 'RACK_BAR_1_')):
        bpy.data.objects.remove(o, do_unlink=True)

# Dedicated materials for custom hardware so factory lamps are not forced permanently emissive.
M['alloy'] = mat('TPG_TACOMA_Alloy', (.34,.35,.36), .24, .86)
M['aux_led'] = mat('TPG_TACOMA_AuxLED', (.82,.88,.92), .11, .05)
M['aux_amber'] = mat('TPG_TACOMA_AuxAmber', (.93,.34,.018), .18, .03)

def replace_mat(obj, m):
    if obj and getattr(obj, 'data', None) and hasattr(obj.data, 'materials'):
        obj.data.materials.clear(); obj.data.materials.append(m)

for o in bpy.data.objects:
    if o.name.startswith('BLACK_OAK_LED_'):
        replace_mat(o, M['aux_led'])
    elif o.name.startswith('REAR_AMBER_'):
        replace_mat(o, M['aux_amber'])

# Exact visible custom item from the frontal reference: slim LED bar beneath the grille.
box('FRONT_LED_BAR_BODY', (2.735,0,.555), (.055,1.18,.075), M['metal'], .012)
box('FRONT_LED_BAR_LENS', (2.765,0,.555), (.010,1.08,.035), M['aux_led'], .004)

# Fictional plate in the real front-plate location; never reproduce the owner's actual plate.
box('FRONT_PLATE', (2.775,0,.405), (.012,.310,.152), M['white'], .007)
if LOD == 0:
    text_obj('DCS 4X4', 'FRONT_PLATE_TEXT', (2.785,0,.405), .050, M['blue'], rot=(math.pi/2,0,math.pi/2), extrude=.002)

# Add a restrained TRD-style outer wheel face over the supplied FBX road wheels.
# This preserves the supplied tire/rim mesh while giving the close side view the machined/dark six-spoke character in the user's photo.
for cx, axle in ((1.7855,'F'),(-1.7855,'R')):
    for s in (-1,1):
        y = s*.966
        torus(f'TRD_RIM_LIP_{axle}_{s}', (cx,y,.405), .292,.016, M['alloy'], rot=(math.pi/2,0,0))
        cyl(f'TRD_HUB_{axle}_{s}', (cx,y,.405), .090,.025, M['black'], 32, rot=(math.pi/2,0,0))
        for i in range(6):
            th = i*math.tau/6.0
            rr = .205
            x = cx + rr*math.cos(th); z = .405 + rr*math.sin(th)
            box(f'TRD_SPOKE_{axle}_{s}_{i}', (x,y,z), (.205,.026,.066), M['alloy'], .008, rot=(0,-th,0))
        if LOD == 0:
            for i in range(6):
                th=i*math.tau/6.0
                x=cx+.057*math.cos(th); z=.405+.057*math.sin(th)
                cyl(f'TRD_LUG_{axle}_{s}_{i}',(x,y+s*.015,z),.010,.010,M['metal'],12,rot=(math.pi/2,0,0))

# Convert the cabin/camper glass material from opaque default shading to the official ED glass shader.
try:
    from materials.material_tools import createEdmNodeGroup
    from enums import NodeSocketInGlassEnum, NodeSocketInDefaultEnum
    gm=M['glass']; gm.use_nodes=True; gm.node_tree.nodes.clear()
    gg=createEdmNodeGroup('EDM_Glass_Material',gm); gg.post_init(MAT_DESCS['EDM_Glass_Material']); gg.name='Group'
    glass_img=bpy.data.images.get('TPG_TACOMA_TintedGlass')
    if glass_img is None:
        glass_img=bpy.data.images.load(str(TEXDIR/'TPG_TACOMA_TintedGlass.png'),check_existing=True)
    gn=gm.node_tree.nodes.new('ShaderNodeTexImage');gn.image=glass_img
    gm.node_tree.links.new(gn.outputs['Color'],gg.inputs[NodeSocketInGlassEnum.GLASS_COLOR])
    rimg=bpy.data.images.get('TPG_TACOMA_TintedGlass_RoughMet')
    if rimg is None:
        rimg=bpy.data.images.load(str(TEXDIR/'TPG_TACOMA_TintedGlass_RoughMet.png'),check_existing=True)
    rimg.colorspace_settings.name='Non-Color';rn=gm.node_tree.nodes.new('ShaderNodeTexImage');rn.image=rimg
    gm.node_tree.links.new(rn.outputs['Color'],gg.inputs[NodeSocketInGlassEnum.ROUGH_METAL])
    try: gg.inputs[NodeSocketInGlassEnum.OPACITY_VALUE].default_value=.42
    except: pass
    print('[TPG TACOMA] official ED tinted-glass material enabled')
except Exception as e:
    print('[TPG TACOMA] glass upgrade skipped:', repr(e))

# Self-illumination only for the added auxiliary lenses; factory headlamp material remains unchanged.
def emissive(m, image_name, value):
    try:
        from enums import NodeSocketInDefaultEnum
        g=None
        for n in m.node_tree.nodes:
            if hasattr(n,'inputs') and NodeSocketInDefaultEnum.EMISSIVE in n.inputs:
                g=n;break
        if g is None:return
        im=bpy.data.images.get(image_name)
        if im is None: im=bpy.data.images.load(str(TEXDIR/(image_name+'.png')),check_existing=True)
        tn=m.node_tree.nodes.new('ShaderNodeTexImage');tn.image=im
        m.node_tree.links.new(tn.outputs['Color'],g.inputs[NodeSocketInDefaultEnum.EMISSIVE])
        try:g.inputs[NodeSocketInDefaultEnum.EMISSIVE_MASK].default_value=1.0
        except:pass
        try:g.inputs[NodeSocketInDefaultEnum.EMISSIVE_VALUE].default_value=value
        except:pass
    except Exception as e:
        print('[TPG TACOMA] emissive setup skipped',m.name,repr(e))

emissive(M['aux_led'],'TPG_TACOMA_AuxLED',2.0)
emissive(M['aux_amber'],'TPG_TACOMA_AuxAmber',2.4)

# Replace placeholder 8x8 flat fills with deterministic 256x256 material maps.
# Variation is deliberately subtle on paint/glass and stronger on rubber/black hardware.
def write_tex(name, base, rough, metal, variation=.02, rough_var=.025):
    N=256; yy,xx=np.mgrid[0:N,0:N]; seed=sum((i+1)*ord(c) for i,c in enumerate(name)) & 0xffffffff
    rng=np.random.default_rng(seed)
    fine=rng.normal(0,1,(N,N)).astype(np.float32)
    wave=(np.sin(xx*.075+seed%17)+np.sin(yy*.061+seed%13)+np.sin((xx+yy)*.027))/3.0
    noise=np.clip(.55*wave+.20*fine,-1,1)
    rgb=np.empty((N,N,4),np.float32)
    b=np.asarray(base,dtype=np.float32)
    rgb[:,:,:3]=np.clip(b[None,None,:]*(1.0+variation*noise[:,:,None]),0,1);rgb[:,:,3]=1
    img=bpy.data.images.new(name+'_HQWRITE',width=N,height=N,alpha=True);img.pixels.foreach_set(rgb.ravel());img.filepath_raw=str(TEXDIR/(name+'.png'));img.file_format='PNG';img.save();bpy.data.images.remove(img)
    rm=np.empty((N,N,4),np.float32);rm[:,:,0]=1.0;rm[:,:,1]=np.clip(rough+rough_var*noise,0,1);rm[:,:,2]=metal;rm[:,:,3]=1.0
    im2=bpy.data.images.new(name+'_RM_HQWRITE',width=N,height=N,alpha=True);im2.pixels.foreach_set(rm.ravel());im2.filepath_raw=str(TEXDIR/(name+'_RoughMet.png'));im2.file_format='PNG';im2.save();bpy.data.images.remove(im2)

spec={
'TPG_TACOMA_Quicksand_4T8':((.585,.525,.414),.42,.04,.018,.015),
'TPG_TACOMA_Black':((.025,.027,.028),.78,.10,.080,.050),
'TPG_TACOMA_BlackMetal':((.018,.020,.021),.45,.72,.070,.035),
'TPG_TACOMA_Rubber':((.015,.016,.016),.94,.01,.180,.035),
'TPG_TACOMA_TintedGlass':((.018,.035,.043),.12,.04,.020,.010),
'TPG_TACOMA_Lamp':((.72,.78,.80),.13,.05,.010,.008),
'TPG_TACOMA_RedLens':((.58,.018,.015),.22,.03,.025,.012),
'TPG_TACOMA_AmberLens':((.88,.28,.012),.20,.03,.025,.012),
'TPG_TACOMA_Wheel':((.11,.12,.13),.30,.78,.060,.025),
'TPG_TACOMA_BrakeRed':((.55,.012,.006),.35,.25,.045,.030),
'TPG_TACOMA_White':((.80,.82,.80),.35,.02,.012,.012),
'TPG_TACOMA_PlateBlue':((.02,.08,.28),.42,.02,.020,.015),
'TPG_TACOMA_Burnt':((.050,.037,.028),.90,.18,.160,.050),
'TPG_TACOMA_Soot':((.010,.009,.008),.98,.01,.220,.020),
'TPG_TACOMA_Alloy':((.34,.35,.36),.24,.86,.050,.020),
'TPG_TACOMA_AuxLED':((.82,.88,.92),.11,.05,.010,.006),
'TPG_TACOMA_AuxAmber':((.93,.34,.018),.18,.03,.020,.010),
}
for n,v in spec.items(): write_tex(n,*v)
print('[TPG TACOMA] 256px material quality pass complete')

# Export must remain neutral.
bpy.context.scene.frame_set(100)
