"""Private editor authoring: reuse WorldPackage materials and import original Ocean vessels.
Set OCEAN_VESSEL_DELIVERY and OCEAN_SCENE_ASSET_PROOF in this commandlet's environment.
"""
import importlib.util
import json
import os
from pathlib import Path
import unreal

source=Path(unreal.Paths.project_plugins_dir())/'DaedalusLink/Content/Python/import_world_package.py'
spec=importlib.util.spec_from_file_location('ocean_world_package_helpers',source)
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
helpers.CONTENT_ROOT='/DaedalusLink/Ocean'
mel=unreal.MaterialEditingLibrary;eal=unreal.EditorAssetLibrary
assets=unreal.AssetToolsHelpers.get_asset_tools()
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DaedalusLink/Ocean'],True)

def expression(material,kind):return mel.create_material_expression(material,kind)
def connect(a,slot,b,input_name):
    # Single-input nodes expose an unnamed first pin in UE5.8.
    if input_name in ['Input','VectorInput']:input_name=''
    if not mel.connect_material_expressions(a,slot,b,input_name):raise RuntimeError('Material expression connection failed: '+input_name)
def constant(material,value):
    node=expression(material,unreal.MaterialExpressionConstant);node.set_editor_property('r',value);return node
def multiply(material,a,b):
    node=expression(material,unreal.MaterialExpressionMultiply);connect(a,'',node,'A');connect(b,'',node,'B');return node

opaque=helpers._material('M_OceanOpaque',False)
water=helpers._material('M_OceanWater',True)
water.set_editor_property('used_with_nanite',False)
water.set_editor_property('tangent_space_normal',False)
water.set_editor_property('translucency_lighting_mode',unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
mel.delete_all_material_expressions(water)  # This newly owned material is rebuilt idempotently.
vertex=expression(water,unreal.MaterialExpressionVertexColor)
tint=expression(water,unreal.MaterialExpressionVectorParameter)
tint.set_editor_property('parameter_name','OceanTint');tint.set_editor_property('default_value',unreal.LinearColor(1,1,1,1))
base=expression(water,unreal.MaterialExpressionMultiply);connect(vertex,'',base,'A');connect(tint,'',base,'B')
mel.connect_material_property(base,'',unreal.MaterialProperty.MP_BASE_COLOR)
world=expression(water,unreal.MaterialExpressionWorldPosition)
time=expression(water,unreal.MaterialExpressionTime)
normals=[]
for channel,frequency,speed,amplitude in [('r',.0007,.045,.09),('g',.0011,.032,.055)]:
    mask=expression(water,unreal.MaterialExpressionComponentMask)
    for name in ['r','g','b','a']:mask.set_editor_property(name,name==channel)
    connect(world,'',mask,'Input')
    phase=expression(water,unreal.MaterialExpressionAdd)
    connect(multiply(water,mask,constant(water,frequency)),'',phase,'A')
    connect(multiply(water,time,constant(water,speed)),'',phase,'B')
    wave=expression(water,unreal.MaterialExpressionCosine);connect(phase,'',wave,'Input')
    normals.append(multiply(water,wave,constant(water,amplitude)))
xy=expression(water,unreal.MaterialExpressionAppendVector);connect(normals[0],'',xy,'A');connect(normals[1],'',xy,'B')
xyz=expression(water,unreal.MaterialExpressionAppendVector);connect(xy,'',xyz,'A');connect(constant(water,1),'',xyz,'B')
normal=expression(water,unreal.MaterialExpressionNormalize);connect(xyz,'',normal,'VectorInput')
mel.connect_material_property(normal,'',unreal.MaterialProperty.MP_NORMAL)
mel.connect_material_property(constant(water,.23),'',unreal.MaterialProperty.MP_ROUGHNESS)
mel.connect_material_property(constant(water,0),'',unreal.MaterialProperty.MP_METALLIC)
mel.connect_material_property(constant(water,.18),'',unreal.MaterialProperty.MP_SPECULAR)
fresnel=expression(water,unreal.MaterialExpressionFresnel)
alpha=expression(water,unreal.MaterialExpressionAdd)
connect(multiply(water,fresnel,constant(water,.10)),'',alpha,'A');connect(constant(water,.88),'',alpha,'B')
mel.connect_material_property(alpha,'',unreal.MaterialProperty.MP_OPACITY)
sky=helpers._material('M_OceanSky',False);mel.delete_all_material_expressions(sky)
sky.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT);sky.set_editor_property('two_sided',True)
normal=expression(sky,unreal.MaterialExpressionPixelNormalWS)
height=expression(sky,unreal.MaterialExpressionComponentMask);height.set_editor_property('b',True);height.set_editor_property('r',False);height.set_editor_property('g',False)
connect(normal,'',height,'Input')
absolute=expression(sky,unreal.MaterialExpressionAbs);connect(height,'',absolute,'Input')
gradient=expression(sky,unreal.MaterialExpressionLinearInterpolate)
for slot,color in [('A',(.20,.48,.78)),('B',(.025,.10,.26))]:
    node=expression(sky,unreal.MaterialExpressionConstant3Vector);node.set_editor_property('constant',unreal.LinearColor(*color,1));connect(node,'',gradient,slot)
connect(absolute,'',gradient,'Alpha');mel.connect_material_property(gradient,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
for material in [opaque,water,sky]:
    errors=mel.recompile_material(material)
    if errors:raise RuntimeError('Ocean material compile failed: '+str(errors))
    if not eal.save_loaded_asset(material):raise RuntimeError('Material save failed')

root=Path(os.environ['OCEAN_VESSEL_DELIVERY']);manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
meshes={}
for record in manifest['assets']:
    destination='/DaedalusLink/Ocean/Vessels/'+record['id']
    if eal.does_directory_exist(destination):
        imported=[eal.load_asset(path) for path in eal.list_assets(destination,recursive=True,include_folder=False)]
    else:imported=helpers._import(str(root/record['file']),destination)
    candidates=[obj for obj in imported if isinstance(obj,unreal.StaticMesh)]
    if len(candidates)!=1:raise RuntimeError('Expected exactly one joined static mesh: '+record['id'])
    previous=eal.get_metadata_tag(candidates[0],'OceanSourceSHA256')
    if previous and previous!=record['sha256']:raise RuntimeError('Existing Ocean mesh source differs; explicit reimport required')
    eal.set_metadata_tag(candidates[0],'OceanSourceSHA256',record['sha256']);eal.save_loaded_asset(candidates[0])
    meshes[record['id']]=candidates[0].get_path_name()
proof={'opaque_material':opaque.get_path_name(),'water_material':water.get_path_name(),'sky_material':sky.get_path_name(),'meshes':meshes,
       'material_compile_errors':0,'native_collision_accepted':False,'rendered_gameplay_accepted':False}
Path(os.environ['OCEAN_SCENE_ASSET_PROOF']).write_text(json.dumps(proof,indent=2),encoding='utf-8')
unreal.log('OCEAN_SCENE_ASSETS_PASS '+json.dumps(proof))
