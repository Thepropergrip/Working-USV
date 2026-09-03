import bpy, os
from pathlib import Path
from materials.materials import build_material_descriptions
from materials.material_tools import createEdmNodeGroup
from enums import NodeSocketInDefaultEnum

WORK = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
SRC = WORK / 'edm-artifacts' / 'LiveryTextures' / 'USA'
TEXDIR = WORK / 'edm-artifacts' / 'Textures'
TEXDIR.mkdir(parents=True, exist_ok=True)
MAT_DESCS = build_material_descriptions()
MATS = {}

KEYS = [
    'PYLON','PRICELED','STORE_SIGN','CANOPY_SIGN','PUMP_SCREEN','PAY','NOSMOKE',
    'GRADE1','GRADE2','GRADE3','DOOR_HOURS','DOOR_PUSH','AIRVAC','PROPANE',
    'ATM','ICE','NEWS','FIRE','AFRAME','AD_TACO','AD_COFFEE','AD_LOTTO','AD_WIPER'
]

def _texture_path(key):
    p = SRC / f'TPG_GS_L10N_{key}_USA.png'
    if not p.exists():
        raise FileNotFoundError(f'Missing USA livery source texture: {p}')
    return p

def _roughmet_path():
    p = TEXDIR / 'TPG_GS_L10N_RoughMet.png'
    if not p.exists():
        img = bpy.data.images.new('TPG_GS_L10N_RoughMet', width=8, height=8, alpha=True)
        img.pixels = [1.0, 0.50, 0.01, 1.0] * 64
        img.filepath_raw = str(p); img.file_format='PNG'; img.save()
    return p

def livery_mat(key, emissive=False):
    if key in MATS:
        return MATS[key]
    name=f'TPG_GS_L10N_{key}'
    m=bpy.data.materials.new(name); m.use_nodes=True; m.node_tree.nodes.clear()
    group=createEdmNodeGroup('EDM_Default_Material',m)
    group.post_init(MAT_DESCS['EDM_Default_Material']); group.name='Group'
    tex=m.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(_texture_path(key)),check_existing=True)
    m.node_tree.links.new(tex.outputs['Color'],group.inputs[NodeSocketInDefaultEnum.BASE_COLOR])
    rmo=m.node_tree.nodes.new('ShaderNodeTexImage')
    rmo.image=bpy.data.images.load(str(_roughmet_path()),check_existing=True)
    rmo.image.colorspace_settings.name='Non-Color'
    m.node_tree.links.new(rmo.outputs['Color'],group.inputs[NodeSocketInDefaultEnum.ROUGH_METAL])
    if emissive:
        em=m.node_tree.nodes.new('ShaderNodeTexImage')
        em.image=tex.image
        m.node_tree.links.new(em.outputs['Color'],group.inputs[NodeSocketInDefaultEnum.EMISSIVE])
        group.inputs[NodeSocketInDefaultEnum.EMISSIVE_VALUE].default_value=2.35
    MATS[key]=m
    return m

def panel(name, loc, dims, material, facing=-1):
    w,h=dims
    verts=[(-w/2,0,-h/2),(w/2,0,-h/2),(w/2,0,h/2),(-w/2,0,h/2)]
    face=(0,1,2,3) if facing < 0 else (3,2,1,0)
    mesh=bpy.data.meshes.new(name+'_mesh'); mesh.from_pydata(verts,[],[face]); mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    if facing < 0:
        uvs=[(0,0),(1,0),(1,1),(0,1)]
    else:
        uvs=[(0,1),(1,1),(1,0),(0,0)]
    for loop,co in zip(mesh.loops,uvs): uv.data[loop.index].uv=co
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o)
    o.location=loc; o.data.materials.append(material)
    return o

def add_livery_overlays():
    M={k:livery_mat(k,k=='PRICELED') for k in KEYS}
    panel('L10N_PYLON',(-14.7,7.385,6.37),(4.18,3.72),M['PYLON'],-1)
    panel('L10N_PRICELED',(-13.80,7.350,5.70),(1.30,2.10),M['PRICELED'],-1)
    panel('L10N_STORE_SIGN',(0,3.945,4.11),(9.48,.68),M['STORE_SIGN'],-1)
    panel('L10N_CANOPY_SIGN',(0,-10.505,5.23),(9.60,.40),M['CANOPY_SIGN'],-1)
    panel('L10N_DOOR_HOURS',(0,4.165,2.55),(1.18,.28),M['DOOR_HOURS'],-1)
    panel('L10N_DOOR_PUSH',(.43,4.165,1.72),(.26,.14),M['DOOR_PUSH'],-1)

    for i,x in enumerate((-7.5,-2.5,2.5,7.5),1):
        for side,face_y,facing in (('A',-3.820,-1),('B',-2.880,1)):
            panel(f'L10N_P{i}_{side}_SCREEN',(x,face_y,1.84),(.49,.21),M['PUMP_SCREEN'],facing)
            panel(f'L10N_P{i}_{side}_PAY',(x,face_y,2.20),(.60,.18),M['PAY'],facing)
            panel(f'L10N_P{i}_{side}_NOSMOKE',(x,face_y,.72),(.68,.19),M['NOSMOKE'],facing)
            for j,dx in enumerate((-.29,0,.29),1):
                panel(f'L10N_P{i}_{side}_GRADE{j}',(x+dx,face_y,1.14),(.245,.25),M[f'GRADE{j}'],facing)

    for key,x in (('AD_TACO',-6.55),('AD_COFFEE',-4.55),('AD_LOTTO',4.55),('AD_WIPER',6.55)):
        panel('L10N_'+key,(x,4.135,2.18),(1.18,.82),M[key],-1)

    panel('L10N_AIRVAC',(10.4,2.955,1.20),(.95,.30),M['AIRVAC'],-1)
    panel('L10N_PROPANE',(8.8,2.905,1.50),(1.20,.30),M['PROPANE'],-1)
    panel('L10N_ATM',(7.45,3.635,1.76),(.62,.24),M['ATM'],-1)
    panel('L10N_ICE',(-7.60,3.445,.95),(1.25,.48),M['ICE'],-1)
    panel('L10N_NEWS',(-6.05,3.505,.72),(.60,.24),M['NEWS'],-1)
    panel('L10N_FIRE',(8.18,3.815,1.18),(.40,.24),M['FIRE'],-1)
    panel('L10N_AFRAME',(-7.92,3.265,.79),(1.05,.70),M['AFRAME'],-1)
    print('[TPG] Added livery-driven USA/Russia/Syria language, price and unit overlays.')
