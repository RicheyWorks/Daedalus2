"""Build compatible hero LOD exports from the owned polish scene.

Blender --background --python SCRIPT -- OUTPUT INPUT_BLEND
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('portal_common.py').read_text(),__file__,'exec'))
source=Path(sys.argv[sys.argv.index('--')+2]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
mesh=bpy.data.objects['Mob_Portal_Knight_Polish'];rig=mesh.parent
if rig.type!='ARMATURE' or len(rig.data.bones)!=14:raise ValueError('Unexpected hero rig')
records=[]
for level,ratio in [(0,1.0),(1,.35),(2,.12)]:
    candidate=mesh if level==0 else mesh.copy()
    if level:
        candidate.data=mesh.data.copy();bpy.context.collection.objects.link(candidate)
        candidate.name=mesh.name+'_LOD'+str(level)
        bpy.ops.object.select_all(action='DESELECT');candidate.select_set(True);bpy.context.view_layer.objects.active=candidate
        modifier=candidate.modifiers.new('Production LOD reduction','DECIMATE');modifier.ratio=ratio;modifier.use_collapse_triangulate=True
        while candidate.modifiers.find(modifier.name)>0:bpy.ops.object.modifier_move_up(modifier=modifier.name)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        candidate.data.validate(verbose=True,clean_customdata=False);candidate.data.update()
        if candidate.data.validate(clean_customdata=False):raise ValueError('LOD topology remained invalid after repair')
    records.append(export_character(candidate,rig,'Hero visual LOD; same existing role','PortalHumanoidV1',
        {'role_count':0,'lod_level':level,'lod_group':mesh.name,'status':'native LOD import pending'}))
    if level:candidate.hide_render=True
if not records[0]['triangles']>records[1]['triangles']>records[2]['triangles']:raise ValueError('LOD reduction failed')
(OUT/'manifest.json').write_text(json.dumps({'assets':records,'clips':['Idle','Walk','Attack','Hurt'],
    'realm':'Portal Realm','status':'validated exports pending native switching'},indent=2))
(OUT/'portal.bba').write_text('BBA 1\n'+''.join(f"asset {r['id']} lod0 {r['triangles']} lod1 - radius {r['radius_cm']} switch {max(500,20*r['radius_cm'])}\n" for r in records))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'portal-hero-lods.blend'))
print('HERO_LODS_EXPORTED',[(r['lod_level'],r['triangles']) for r in records])
