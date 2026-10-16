# SPDX-License-Identifier: MIT
"""Closed32923 greenhouse intake: seven opaque groups, transmission glass held.

Uses pinned existing inventory, geometry, material and queue helpers privately.
Never invokes their old packet entry points. Imports once, validates every owned
output before first saves, and saves only the thirteen accepted opaque assets.
The host separately owns the guarded seven-actor placement/map/camera phases.
"""
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import time
from types import SimpleNamespace
import unreal

LABEL = 'Codex SkyFarm GreenhouseBayR1 partial opaque intake32923'
ROOT = '/Game/Daedalus/Art/SkyFarm/GreenhouseBayR1'
GLASS = 'SFG_R1_glass_glass'
SOURCE_SHA = '1e208959d249b8b781027ad2bae69dbb70bb4472db01e9bf12da707d93ad7d0a'
MANIFEST_SHA = '7082cd07018dfa21254023ab5e715645e11e099a455a13cd81d59e2ad4f62a96'
HELPERS = {
    'sunspool': 'b571284f8d7b13fb1b135072c7f438e4ae036711d3b0bab053dc751844f2e047',
    'geometry': 'e3012aa9819ae60b90adcbcb6f6b37428e35daa5747313c9964918b485428dac',
    'miri': '5a434e398dcaafc0cb5f66d399aca372f322dcd51a29bf7c3687e78fed05c059',
    'catalogue': '00e48d8a86cd377250c439d6992a5bec6deb09b0f77e9607bf7beebd324d1d03',
    'queue': 'ff67f266fa45b276d287d69d5fa750b445353960d7213234dede15bc1f135df0',
}


def pin(path, sha):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        raise RuntimeError('exact reviewed source differs: ' + str(path))
    return data


def setup(cfg):
    if cfg['destination'] != ROOT:
        raise ValueError('exact fresh greenhouse namespace required')
    pin(cfg['glb'], SOURCE_SHA); pin(cfg['manifest'], MANIFEST_SHA)
    packet = json.loads(pin(cfg['source_packet'], cfg['source_packet_sha256']))
    if len(packet['nodes']) != 8 or sum(r['triangles'] for r in packet['nodes']) != 1452:
        raise RuntimeError('closed eight-group greenhouse source required')
    scopes = {}
    for key, sha in HELPERS.items():
        scope = {'__name__': '_codex_skyfarm_private_' + key, '__file__': cfg[key]}
        exec(compile(pin(cfg[key], sha), cfg[key], 'exec'), scope)
        scope.update(ROOT=ROOT, LABEL=LABEL,
            ROLES={r['name']: (r['triangles'], r['material']['name']) for r in packet['nodes']})
        scopes[key] = scope
    guard = scopes['queue']['_shared']({'shared_source': cfg['catalogue'],
        'shared_source_fingerprint': {'bytes': 22414, 'sha256': HELPERS['catalogue']}})
    guard.update(ROOT=ROOT, LABEL=LABEL)
    scopes['catalogue'] = guard
    if (not isinstance(cfg['deadline_epoch'],(float,int)) or not math.isfinite(cfg['deadline_epoch'])
            or not Path(cfg['journal']).is_absolute() or not Path(cfg['journal']).parent.is_dir()
            or Path(cfg['journal']).with_name(Path(cfg['journal']).name+'.write-pending').exists()
            or Path(cfg['content_dir']).resolve()!=Path('C:/Unreal/DaedalusRealm/Content').resolve()):
        raise ValueError('finite deadline, fresh absolute journal and actual fixed content root required')
    return packet, scopes


def _utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _memory():
    class Status(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ('total_physical', 'available_physical',
            'total_commit', 'available_commit', 'total_virtual', 'available_virtual', 'reserved')]
    row = Status(); row.length = ctypes.sizeof(row)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(row)):
        raise RuntimeError('fresh OS memory unavailable')
    if row.available_physical < 1700000*1024 or row.available_commit < 2200000*1024:
        raise RuntimeError('unchanged explicit memory floor; preserve partial output')
    return {'physical_bytes': int(row.available_physical), 'commit_bytes': int(row.available_commit)}


def _file(obj, cfg):
    package = obj.get_path_name().split('.')[0]
    if not package.startswith(ROOT + '/'):
        raise RuntimeError('foreign package')
    return Path(cfg['content_dir']) / (package.removeprefix('/Game/') + '.uasset')


def _tags(role):
    return {'codex_owner': 'codex-play-guard', 'codex_source_owner': 'pootscoot',
        'codex_source_glb_sha256': SOURCE_SHA, 'codex_source_manifest_sha256': MANIFEST_SHA,
        'codex_source_role': role, 'codex_receiving_scope': '32923 partial opaque7groups; transmission glass held',
        'codex_unit_contract': 'identity glTF roots; absolute XZY*100 baked; sharedactororigin; scale1',
        'codex_collision_scope': 'decorative nonblocking; no navigation/walking/crop/grapple acceptance'}


def inspect(cfg, packet, scopes, metadata=False):
    helper = scopes['sunspool']; objects = helper['_assets']()
    meshes = [o for o in objects.values() if isinstance(o, unreal.StaticMesh)]
    materials = [o for o in objects.values() if isinstance(o, unreal.MaterialInstanceConstant)]
    if len(objects) != 15 or len(meshes) != 8 or len(materials) != 7:
        raise RuntimeError('actual inventory must account for all8 meshes and7 MICs')
    rows=[]; accepted={}; held={}; roles={}; used_meshes=set(); used_mats=set()
    for source in packet['nodes']:
        candidates = [o for o in meshes if helper['_normal'](o.get_name()).endswith(helper['_normal'](source['name']))]
        if len(candidates) != 1:raise RuntimeError('ambiguous actual source role: '+source['name'])
        mesh=candidates[0]
        if mesh.get_path_name() in used_meshes:raise RuntimeError('duplicate role mapping')
        used_meshes.add(mesh.get_path_name())
        slots=list(mesh.get_editor_property('static_materials'))
        mat=mesh.get_material(0) if len(slots)==1 else None
        if (not isinstance(mat,unreal.MaterialInstanceConstant) or mat.get_path_name() not in objects
                or not helper['_normal'](mat.get_name()).endswith(helper['_normal'](source['material']['name']))):
            raise RuntimeError('exact one-slot owned source MIC required: '+source['name'])
        used_mats.add(mat.get_path_name())
        row={'source_role':source['name'],'path':mesh.get_path_name(),'material_path':mat.get_path_name(),
             'source_material':source['material']['name']}
        if source['name']==GLASS:
            held.update({mesh.get_path_name():mesh,mat.get_path_name():mat})
            row.update(status='HELD_UNSAVED_UNPLACED',reason='No qualified KHR_materials_transmission receiver; no alpha-only or opaque fallback')
        else:
            geometry=scopes['geometry']['_geometry'](mesh,source)
            physical=scopes['geometry']['_material'](mat,source['material'],scopes['miri'],helper)
            if geometry['issues'] or geometry['simple_collision_count'] != 0 or physical['readback_errors']:
                raise RuntimeError('native greenhouse geometry/material/options differ: '+json.dumps({'role':source['name'],'geometry':geometry,'material':physical}))
            accepted.update({mesh.get_path_name():mesh,mat.get_path_name():mat})
            roles.update({mesh.get_path_name():source['name'],mat.get_path_name():source['material']['name']})
            row.update(geometry=geometry,material=physical,status='OPAQUE_ACCEPTED')
        rows.append(row)
    if used_meshes|used_mats != set(objects) or len(accepted)!=13 or len(held)!=2 or set(accepted)&set(held):
        raise RuntimeError('7opaque/6sharedMIC + exact2held partition differs')
    if sum(r['geometry']['triangles'] for r in rows if r['status']=='OPAQUE_ACCEPTED') != 1404:
        raise RuntimeError('opaque triangle total differs')
    if metadata:
        for path,obj in accepted.items():
            if {k:unreal.EditorAssetLibrary.get_metadata_tag(obj,k) for k in _tags(roles[path])} != _tags(roles[path]):
                raise RuntimeError('new owned source metadata differs')
    return {'stage':'PARTIAL_OPAQUE_BAY_ACCEPTED_GLASS_HELD','items':rows,
            'accepted_paths':sorted(accepted),'held_paths':sorted(held),'opaque_triangles':1404,
            'source_triangles':1452,'held_glass_triangles':48,
            'material_shared_copper_preserved':True},objects,accepted,held,roles


def preflight(cfg):
    packet,scopes=setup(cfg)
    scopes['catalogue']['_deadline'](cfg); _memory()
    state=scopes['catalogue']['_preflight']()
    if Path(cfg['journal']).exists():raise RuntimeError('retained native journal; no replay')
    absent=scopes['sunspool']['_absent']()
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    if any(a.get_actor_label().startswith('CodexSkyFarm_GreenhouseBayR1_') for a in actors):
        raise RuntimeError('intended actor identity occupied')
    return {'stage':'greenhouse_preflight_complete','state':state,'absent':absent,
            'glass_policy':'HOLD UNSAVED/UNPLACED','native_mutations':0}


def steps(cfg):
    packet,scopes=setup(cfg);helper=scopes['sunspool'];guard=scopes['catalogue']
    journal=Path(cfg['journal'])
    if journal.exists():raise RuntimeError('retained native journal; no replay')
    report={'stage':'source_admitted','intents':[],'saves':[],'imported_object_paths':[],
            'glass_status':'HELD_UNSAVED_UNPLACED','requested_pipeline':{'import_materials':True,
            'bake_meshes':True,'build_scale':[1,1,1],'nanite':False,'lightmap_uvs':False,'collision':False}}
    with journal.open('x',encoding='utf-8') as stream:helper['_flush'](stream,report)
    def keep():helper['_write'](journal,report)
    def on_wait(row):report.setdefault('guard_waits',[]).append(row);keep()
    def intent(operation,**fields):
        _memory()
        current=helper['_assets']()
        yield from scopes['queue']['_preflight_steps'](guard,cfg,[p.split('.')[0] for p in current],on_wait=on_wait)
        report['intents'].append({'utc':_utc(),'operation':operation,**fields});keep()
    try:
        yield from intent('import_exact_original_greenhouse_glb')
        helper['_absent']();pin(cfg['glb'],SOURCE_SHA)
        pipeline=unreal.InterchangeGenericAssetsPipeline()
        mesh_options=pipeline.get_editor_property('mesh_pipeline')
        for key,value in {'build_nanite':False,'generate_lightmap_u_vs':False,'collision':False,'build_scale3d':unreal.Vector(1,1,1)}.items():mesh_options.set_editor_property(key,value)
        common=pipeline.get_editor_property('common_meshes_properties')
        common.set_editor_property('bake_meshes',True)
        common.set_editor_property('vertex_color_import_option',unreal.InterchangeVertexColorImportOption.IVCIO_REPLACE)
        pipeline.get_editor_property('material_pipeline').set_editor_property('import_materials',True)
        stack=unreal.InterchangePipelineStackOverride();stack.add_pipeline(pipeline)
        task=unreal.AssetImportTask();task.filename=cfg['glb'];task.destination_path=ROOT
        task.destination_name='SkyFarm_GreenhouseBay_R1';task.automated=True;task.replace_existing=False;task.save=False;task.options=stack
        started=time.perf_counter();unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        report.update(stage='import_returned',import_seconds=time.perf_counter()-started,
                      imported_object_paths=[str(p) for p in task.imported_object_paths]);keep()
        objects=helper['_assets']()
        if set(report['imported_object_paths'])!=set(objects) or len(objects)!=15:
            raise RuntimeError('actual import receipt/complete namespace inventory differs')
        if any(_file(obj,cfg).exists() for obj in objects.values()):raise RuntimeError('unexpected implicit save; preserve without replay')
        subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        for obj in objects.values():
            if not isinstance(obj,unreal.StaticMesh) or helper['_normal'](obj.get_name()).endswith(helper['_normal'](GLASS)):continue
            settings=obj.get_editor_property('nanite_settings')
            if settings.enabled:
                yield from intent('set_only_new_opaque_mesh_nanite_false',path=obj.get_path_name())
                settings.enabled=False;subsystem.set_nanite_settings(obj,settings,True)
        observed,objects,accepted,held,roles=inspect(cfg,packet,scopes)
        report['before_metadata']=observed;keep()
        for path,obj in accepted.items():
            yield from intent('tag_only_new_accepted_object',path=path,role=roles[path])
            for key,value in _tags(roles[path]).items():unreal.EditorAssetLibrary.set_metadata_tag(obj,key,value)
        observed,objects,accepted,held,roles=inspect(cfg,packet,scopes,metadata=True)
        report['before_first_save']=observed;keep()
        if any(_file(obj,cfg).exists() for obj in objects.values()):raise RuntimeError('all validation must precede first save')
        for path,obj in sorted(accepted.items(),key=lambda row:(isinstance(row[1],unreal.StaticMesh),row[0])):
            yield from intent('first_save_only_accepted_opaque_asset',path=path)
            started=time.perf_counter();saved=bool(unreal.EditorAssetLibrary.save_loaded_asset(obj,only_if_is_dirty=False))
            report['saves'].append({'path':path,'returned':saved,'seconds':time.perf_counter()-started});keep()
            if not saved or not _file(obj,cfg).exists():raise RuntimeError('first save unconfirmed; no replay')
        final,objects,accepted,held,roles=inspect(cfg,packet,scopes,metadata=True)
        if any(_file(obj,cfg).exists() for obj in held.values()):raise RuntimeError('held glass unexpectedly saved')
        report.update(stage='PARTIAL_OPAQUE13_SAVED_GLASS2_HELD',final=final)
        report['post_guard']=guard['_preflight']([p.split('.')[0] for p in held]);keep()
        return report
    except Exception as exc:
        report.update(stage='halted_preserve_partial',error=str(exc),error_type=type(exc).__name__);keep()
        raise


def readback(cfg):
    packet,scopes=setup(cfg)
    scopes['catalogue']['_deadline'](cfg);_memory()
    observed,objects,accepted,held,roles=inspect(cfg,packet,scopes,metadata=True)
    guard=scopes['catalogue']['_preflight']([p.split('.')[0] for p in held])
    if any(not _file(o,cfg).exists() for o in accepted.values()) or any(_file(o,cfg).exists() for o in held.values()):
        raise RuntimeError('accepted saved /held absent file partition differs')
    return {'stage':'PARTIAL_OPAQUE13_SAVED_INDEPENDENT_READBACK_GLASS2_HELD','inspection':observed,'guard':guard,'native_mutations':0}


# Owned append-only world phases. The asset intake functions above are separate.
WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
MAP = '/Game/Daedalus/DaedalusWorld'
FARM_PREFIX = 'CodexSkyFarm_GreenhouseBayR1_'
FARM_FOLDER = 'Codex/SkyFarm/GreenhouseBayR1'
FARM_ANCHOR = [-5000., -19000., 5218.]
FARM_HELPER_SHA = '3ea20e729950c1bb34bf5d36ba62398746bd1b400c88a05027f8e83f7cbad2c4'
FARM_SUPPORT = WORLD + ':PersistentLevel.DaedalusLandDistrict_215'
FARM_MARKER = '# Codex SkyFarm GreenhouseBayR1 closed32923 world phase'


def _farm_context(cfg):
    packet, scopes = setup(cfg)
    e = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = e.get_editor_world()
    if world is None or world.get_path_name() != WORLD:
        raise RuntimeError('exact existing Daedalus editor world required')
    if (cfg.get('support_actor_path') != FARM_SUPPORT
            or cfg.get('support_component_path') != FARM_SUPPORT + '.Ground'
            or cfg.get('support_instance') != 0):
        raise ValueError('only verified floor_215.Ground instance0 support admitted')
    if cfg.get('world_helper_sha256') != FARM_HELPER_SHA:
        raise ValueError('exact retained world preservation helper required')
    private = {'__name__': '_codex_skyfarm_private_world', 'unreal': unreal,
               'math': math, 'json': json, 'hashlib': hashlib,
               'e': e, 'world': world, 'sub': sub}
    # The host supplies only the retained pure snap definition, never its host.
    import ast
    snap_raw = pin(cfg['snap_source'], cfg['snap_source_sha256'])
    tree = ast.parse(snap_raw, filename=cfg['snap_source'])
    if (len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef)
            or tree.body[0].name != 'snap'):
        raise ValueError('one pinned pure snap function definition required')
    exec(compile(tree, cfg['snap_source'], 'exec'), private)
    exec(compile(pin(cfg['world_helper'], FARM_HELPER_SHA), cfg['world_helper'], 'exec'), private)
    return packet, scopes, private, e, world, sub


def _farm_paths(cfg):
    keys = ('world_before', 'world_journal', 'world_save_journal', 'camera_journal')
    paths = {key: Path(cfg[key]) for key in keys}
    protected = {Path(cfg[key]).resolve() for key in
                 ('glb', 'manifest', 'source_packet', 'journal', 'baseline',
                  'world_helper', 'snap_source')}
    if (len({path.resolve() for path in paths.values()}) != len(paths)
            or any(not path.is_absolute() or path.suffix != '.json'
                   or not path.parent.is_dir() or path.resolve() in protected
                   for path in paths.values())):
        raise ValueError('distinct absolute owned world journal paths required')
    return paths


def _farm_new_file(path):
    if path.exists() or path.with_name(path.name + '.write-pending').exists():
        raise RuntimeError('retained world journal/pending write; reconcile without replay: ' + str(path))


def _farm_guard(cfg, scopes, held, allow_map=False):
    import sys
    scopes['catalogue']['_deadline'](cfg)
    _memory()
    bridge = sys.modules.get('claude_unreal_bridge')
    if bridge is None or not all(hasattr(bridge, key) for key in
                               ('_jobs', '_running', '_job_boxes', '_remote_lock')):
        raise RuntimeError('existing bridge queue state unavailable')
    running = list(bridge._running)
    others = [req.get('type') for gen, req, box in running
              if req.get('type') != 'execute_python'
              or not (req.get('params') or {}).get('code', '').startswith(FARM_MARKER)]
    if (len(running) != 1 or others or bridge._jobs.qsize() or bridge._remote_lock.locked()
            or any(not box['done'].is_set() for box, stamp in list(bridge._job_boxes.values()))):
        raise RuntimeError('conflicting/unfinished native operation; preserve world phase')
    maps = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    content = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    allowed = {p.split('.')[0] for p in held}
    if (not set(content).issubset(allowed)
            or not set(maps).issubset({MAP} if allow_map else set())):
        raise RuntimeError('unexpected dirty map/content; only own map and held glass may differ')
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE running; no world phase')
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name() != WORLD:
        raise RuntimeError('editor map changed')
    return {'dirty_maps': maps, 'dirty_content': content, 'held_dirty_allowed': sorted(allowed),
            'queue_empty': True, 'pie_running': False, 'native_world': WORLD}


def _farm_assets(cfg, packet, scopes):
    saved = json.loads(Path(cfg['journal']).read_text(encoding='utf-8'))
    if (saved.get('stage') != 'PARTIAL_OPAQUE13_SAVED_GLASS2_HELD'
            or len(saved.get('saves', [])) != 13
            or any(row.get('returned') is not True for row in saved['saves'])):
        raise RuntimeError('exact thirteen confirmed first asset saves required before placement')
    observed, objects, accepted, held, roles = inspect(cfg, packet, scopes, metadata=True)
    if ({row['path'] for row in saved['saves']} != set(accepted)
            or saved.get('final', {}).get('accepted_paths') != sorted(accepted)
            or any(not _file(obj, cfg).exists() for obj in accepted.values())
            or any(_file(obj, cfg).exists() for obj in held.values())):
        raise RuntimeError('saved opaque/unsaved glass receipt partition differs')
    expected = {row['source_role']: row for row in observed['items'] if row['status'] == 'OPAQUE_ACCEPTED'}
    if len(expected) != 7:
        raise RuntimeError('exact seven saved opaque mesh roles required')
    return expected, held


def _farm_camera(e):
    location, rotation = e.get_level_viewport_camera_info()
    result = {'location': [float(getattr(location, k)) for k in ('x', 'y', 'z')],
              'rotation': [float(getattr(rotation, k)) for k in ('pitch', 'yaw', 'roll')]}
    if any(not math.isfinite(v) for row in result.values() for v in row):
        raise RuntimeError('nonfinite viewport camera')
    return result


def _farm_camera_same(actual, expected):
    return all(abs(a-b) <= 1e-5 for key in ('location', 'rotation')
               for a, b in zip(actual[key], expected[key]))


def _farm_before(cfg):
    value = json.loads(Path(cfg['world_before']).read_text(encoding='utf-8'))
    if value.get('stage') != 'SKYFARM_WORLD_PREFLIGHT_COMPLETE' or len(value['scene']['actors']) != 145:
        raise RuntimeError('exact retained original145 world preflight required')
    return value


def _farm_assert_old(private, before, new_paths=()):
    actors = private['_world_actors']()
    now = {actor.get_path_name(): actor for actor in actors}
    old = set(before['actor_paths'])
    extra = set(new_paths)
    if len(now) != len(actors) or set(now) != old | extra or old & extra:
        raise RuntimeError('exact all-world oldpathset plus declared new actors required')
    # Reuse the unchanged digest over the original exact actor set. The helper's
    # closed Winter4 zero/two exclusions are never relaxed or invoked for seven.
    original = private['_world_actors']
    private['_world_actors'] = lambda: [now[path] for path in sorted(old)]
    try:
        observed = private['world_existing_actor_digest']()
    finally:
        private['_world_actors'] = original
    if observed != before['world_digest']:
        raise RuntimeError('original all-world actor/component digest changed')
    scene = private['snapshot_scene']()
    old_rows = {row['path']: row for row in before['scene']['actors']}
    current = {row['path']: row for row in scene['actors']}
    if (any(current.get(path) != row for path, row in old_rows.items())
            or len(current) != 145 + len(extra)
            or set(current) != set(old_rows) | extra):
        raise RuntimeError('original145 records or declared Codex additions differ')
    return {'scene': scene, 'old_world_digest': observed, 'old_actor_paths_preserved': len(old),
            'new_actor_paths': sorted(extra), 'limits': observed['limits']}


def _farm_clearance(private, excluded=()):
    support = []
    for dx, dy in ((0.,0.),(-320.,-510.),(-320.,510.),(320.,-510.),(320.,510.)):
        x,y = FARM_ANCHOR[0]+dx,FARM_ANCHOR[1]+dy
        hit = unreal.SystemLibrary.line_trace_single(private['world'],
            unreal.Vector(x,y,5238.), unreal.Vector(x,y,5198.),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        t = hit.to_tuple() if hit is not None else None
        if (not t or len(t) != 18 or not t[0] or t[9] is None or t[10] is None
                or t[9].get_path_name() != FARM_SUPPORT
                or t[10].get_path_name() != FARM_SUPPORT+'.Ground' or t[13] != 0
                or abs(float(t[5].z)-5218.) > .2 or float(t[7].z) < .999):
            raise RuntimeError('fresh exact floor_215.Ground instance0 contact unavailable')
        support.append({'xy':[x,y], 'z':float(t[5].z), 'normal':private['_xyz'](t[7]),
                        'actor':t[9].get_path_name(),'component':t[10].get_path_name(),'instance':int(t[13])})
    box = ([-5324.2,-19515.,5218.5],[-4675.8,-18485.,5615.])
    blockers=[]; counts={'actors':0,'components':0,'instances':0}
    for actor in private['_world_actors']():
        if actor.get_path_name() in excluded:
            continue
        counts['actors'] += 1
        center, extent = actor.get_actor_bounds(False)
        if not private['_intersects'](private['_center_box'](center,extent),box):
            continue
        for comp in actor.get_components_by_class(unreal.PrimitiveComponent):
            counts['components'] += 1
            if counts['components'] > 200000:
                raise RuntimeError('bounded component clearance exceeded')
            if not private['_intersects'](private['_component_box'](comp),box):
                continue
            if isinstance(comp,unreal.InstancedStaticMeshComponent):
                mesh=comp.static_mesh
                if mesh is None:raise RuntimeError('unresolved overlapping ISM mesh')
                bounds=mesh.get_bounding_box()
                local=private['_box'](private['_xyz'](bounds.min),private['_xyz'](bounds.max))
                count=comp.get_instance_count()
                scale=float(comp.get_editor_property('bounds_scale'))
                if type(count) is not int or count < 0 or not math.isfinite(scale) or scale < 0:
                    raise RuntimeError('invalid overlapping ISM count/bounds scale')
                counts['instances'] += count
                if counts['instances'] > 100000:raise RuntimeError('bounded actual ISM clearance exceeded')
                for index in range(count):
                    actual=private['_transformed_box'](local,comp.get_instance_transform(index,world_space=True))
                    c=[(actual[0][i]+actual[1][i])*.5 for i in range(3)]
                    r=[(actual[1][i]-actual[0][i])*.5*max(1.,scale) for i in range(3)]
                    actual=([c[i]-r[i] for i in range(3)],[c[i]+r[i] for i in range(3)])
                    if private['_intersects'](actual,box):
                        blockers.append({'actor':actor.get_path_name(),'component':comp.get_path_name(),'instance':index,'bounds':actual})
            else:
                blockers.append({'actor':actor.get_path_name(),'component':comp.get_path_name(),
                                 'bounds':private['_component_box'](comp)})
    if blockers:raise RuntimeError('fresh farm clearance blocked: '+json.dumps(blockers[:20]))
    return {'support':support,'box_cm':box,'blockers':[],'counts':counts,
            'limits':'Conservative actual static/ISM AABBs and five point contacts; no collision/nav/walking/interaction acceptance.'}


def _farm_validate(private, expected, paths):
    actors={a.get_path_name():a for a in private['_world_actors']()}
    rows=[]
    if len(paths)!=7 or len(set(paths))!=7:raise RuntimeError('exact seven new actor paths required')
    for role,path in paths.items():
        actor=actors.get(path)
        if (actor is None or role not in expected or actor.get_class().get_path_name()!='/Script/Engine.StaticMeshActor'
                or actor.get_actor_label()!=FARM_PREFIX+role or str(actor.get_folder_path())!=FARM_FOLDER
                or private['_xyz'](actor.get_actor_location())!=FARM_ANCHOR
                or private['_xyz'](actor.get_actor_scale3d())!=[1.,1.,1.]
                or any(abs(float(getattr(actor.get_actor_rotation(),k)))>1e-6 for k in ('pitch','yaw','roll'))
                or actor.get_actor_enable_collision() is not False or actor.get_attach_parent_actor() is not None):
            raise RuntimeError('new farm actor identity/pose/collision differs: '+role)
        components=list(actor.get_components_by_class(unreal.StaticMeshComponent))
        if len(components)!=1:raise RuntimeError('one exact static component required')
        comp=components[0]
        if (comp.static_mesh.get_path_name()!=expected[role]['path'] or comp.get_num_materials()!=1
                or comp.get_material(0).get_path_name()!=expected[role]['material_path']
                or comp.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION
                or comp.is_simulating_physics() is not False
                or bool(comp.get_editor_property('can_ever_affect_navigation'))):
            raise RuntimeError('new farm mesh/material/nonblocking/nav policy differs: '+role)
        rows.append({'role':role,'path':path,'mesh':comp.static_mesh.get_path_name(),
                     'material':comp.get_material(0).get_path_name(),'snapshot':private['snap'](actor),
                     'collision':'NO_COLLISION','actor_collision':False,'affect_navigation':False})
    return rows


def world_preflight(cfg):
    packet,scopes,private,e,world,sub=_farm_context(cfg)
    paths=_farm_paths(cfg)
    for path in paths.values():_farm_new_file(path)
    _farm_new_file(Path(cfg['journal']))
    scopes['sunspool']['_absent']()
    held={}
    guard=_farm_guard(cfg,scopes,held)
    scene=private['snapshot_scene']()
    baseline=json.loads(Path(cfg['baseline']).read_text(encoding='utf-8'))
    old_scene=baseline.get('scene') or baseline.get('native',{}).get('scene')
    if old_scene is None or scene['world']!=old_scene['world'] or scene['actors']!=old_scene['actors'] or len(scene['actors'])!=145:
        raise RuntimeError('fresh scene differs from exact saved original145 baseline')
    if any(a.get_actor_label().startswith(FARM_PREFIX) for a in private['_world_actors']()):
        raise RuntimeError('new farm actor identity occupied')
    before={'stage':'SKYFARM_WORLD_PREFLIGHT_COMPLETE','utc':_utc(),'scene':scene,
            'camera':_farm_camera(e),'actor_paths':sorted(a.get_path_name() for a in private['_world_actors']()),
            'world_digest':private['world_existing_actor_digest'](),
            'clearance':_farm_clearance(private),'guard':guard,'native_mutations':0}
    scopes['sunspool']['_write'](paths['world_before'],before)
    return before


def world_place(cfg):
    packet,scopes,private,e,world,sub=_farm_context(cfg)
    paths=_farm_paths(cfg);_farm_new_file(paths['world_journal'])
    before=_farm_before(cfg);expected,held=_farm_assets(cfg,packet,scopes)
    _farm_guard(cfg,scopes,held);_farm_assert_old(private,before)
    if not _farm_camera_same(_farm_camera(e),before['camera']):raise RuntimeError('original camera changed')
    clearance=_farm_clearance(private)
    report={'stage':'WORLD_PLACE_STARTED','utc':_utc(),'intents':[],'actors':{},'clearance':clearance,'replay_permitted':False}
    with paths['world_journal'].open('x',encoding='utf-8') as stream:scopes['sunspool']['_flush'](stream,report)
    def intent(operation,**fields):
        _farm_guard(cfg,scopes,held,allow_map=bool(report['actors']))
        report['intents'].append({'utc':_utc(),'operation':operation,**fields})
        scopes['sunspool']['_write'](paths['world_journal'],report)
    try:
        for role,row in sorted(expected.items()):
            intent('spawn_one_accepted_opaque_role',role=role,mesh=row['path'])
            actor=sub.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*FARM_ANCHOR),unreal.Rotator(0,0,0))
            if actor is None:raise RuntimeError('spawn returned no actor; do not replay')
            report['actors'][role]=actor.get_path_name()
            scopes['sunspool']['_write'](paths['world_journal'],report)
            intent('configure_exact_new_actor',role=role,path=actor.get_path_name())
            actor.set_actor_label(FARM_PREFIX+role);actor.set_folder_path(FARM_FOLDER)
            actor.set_actor_scale3d(unreal.Vector(1,1,1));actor.set_actor_enable_collision(False)
            comp=actor.static_mesh_component
            comp.set_static_mesh(unreal.EditorAssetLibrary.load_asset(row['path']))
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            comp.set_editor_property('can_ever_affect_navigation',False)
        report['new_actors']=_farm_validate(private,expected,report['actors'])
        report['preservation']=_farm_assert_old(private,before,report['actors'].values())
        report['clearance_after']=_farm_clearance(private,report['actors'].values())
        if not _farm_camera_same(_farm_camera(e),before['camera']):raise RuntimeError('camera changed during placement')
        report['post_guard']=_farm_guard(cfg,scopes,held,True)
        report.update(stage='SEVEN_OPAQUE_ACTORS_PLACED_UNSAVED',native_new_actor_count=7)
        scopes['sunspool']['_write'](paths['world_journal'],report);return report
    except Exception as exc:
        report.update(stage='HALTED_PRESERVE_PARTIAL_WORLD',error=str(exc),error_type=type(exc).__name__)
        scopes['sunspool']['_write'](paths['world_journal'],report);raise


def world_save(cfg):
    packet,scopes,private,e,world,sub=_farm_context(cfg)
    paths=_farm_paths(cfg);_farm_new_file(paths['world_save_journal'])
    before=_farm_before(cfg);expected,held=_farm_assets(cfg,packet,scopes)
    placed=json.loads(paths['world_journal'].read_text(encoding='utf-8'))
    if placed.get('stage')!='SEVEN_OPAQUE_ACTORS_PLACED_UNSAVED':raise RuntimeError('exact completed placement journal required')
    _farm_guard(cfg,scopes,held,True)
    preservation=_farm_assert_old(private,before,placed['actors'].values())
    rows=_farm_validate(private,expected,placed['actors'])
    clearance=_farm_clearance(private,placed['actors'].values())
    if not _farm_camera_same(_farm_camera(e),before['camera']):raise RuntimeError('original camera must be restored before one save')
    report={'stage':'MAP_SAVE_INTENT','utc':_utc(),'save_return':None,'new_actors':rows,
            'preservation':preservation,'clearance':clearance,'map':MAP,'replay_permitted':False}
    with paths['world_save_journal'].open('x',encoding='utf-8') as stream:scopes['sunspool']['_flush'](stream,report)
    _farm_guard(cfg,scopes,held,True)
    started=time.perf_counter()
    report['save_return']=bool(unreal.EditorLoadingAndSavingUtils.save_map(world,MAP))
    report['save_seconds']=time.perf_counter()-started
    report['stage']='ONE_MAP_SAVE_TRUE' if report['save_return'] else 'MAP_SAVE_FALSE_PRESERVE_NO_REPLAY'
    scopes['sunspool']['_write'](paths['world_save_journal'],report)
    if report['save_return'] is not True:raise RuntimeError('map save returned false; no replay')
    report['post_guard']=_farm_guard(cfg,scopes,held)
    report['after']=_farm_assert_old(private,before,placed['actors'].values())
    scopes['sunspool']['_write'](paths['world_save_journal'],report);return report


def camera(cfg, mode):
    if mode not in ('frame','restore'):raise ValueError('camera frame/restore only')
    packet,scopes,private,e,world,sub=_farm_context(cfg)
    paths=_farm_paths(cfg);before=_farm_before(cfg)
    expected,held=_farm_assets(cfg,packet,scopes)
    placed=json.loads(paths['world_journal'].read_text(encoding='utf-8'))
    if placed.get('stage')!='SEVEN_OPAQUE_ACTORS_PLACED_UNSAVED':raise RuntimeError('completed placement required')
    _farm_guard(cfg,scopes,held,True)
    _farm_assert_old(private,before,placed['actors'].values());_farm_validate(private,expected,placed['actors'])
    journal=paths['camera_journal']
    if mode=='frame':
        _farm_new_file(journal)
        if not _farm_camera_same(_farm_camera(e),before['camera']):raise RuntimeError('pre-frame camera changed')
        report={'stage':'CAMERA_FRAME_INTENT','utc':_utc(),'original':before['camera'],'intents':['frame']}
        with journal.open('x',encoding='utf-8') as stream:scopes['sunspool']['_flush'](stream,report)
        target={'location':[-4020.,-20260.,6070.],'rotation':[-24.,128.,0.]}
    else:
        report=json.loads(journal.read_text(encoding='utf-8'))
        if report.get('stage')!='CAMERA_FRAMED':raise RuntimeError('only exact completed frame may be restored once')
        if not _farm_camera_same(_farm_camera(e),report['observed']):raise RuntimeError('camera moved after owned frame; preserve it')
        report.update(stage='CAMERA_RESTORE_INTENT');report['intents'].append('restore')
        scopes['sunspool']['_write'](journal,report);target=before['camera']
    _farm_guard(cfg,scopes,held,True)
    e.set_level_viewport_camera_info(unreal.Vector(*target['location']),
        unreal.Rotator(pitch=target['rotation'][0],yaw=target['rotation'][1],roll=target['rotation'][2]))
    observed=_farm_camera(e)
    if not _farm_camera_same(observed,target):raise RuntimeError('camera write/readback differs; preserve journal')
    report.update(stage='CAMERA_FRAMED' if mode=='frame' else 'CAMERA_RESTORED',observed=observed)
    scopes['sunspool']['_write'](journal,report);return report


def world_readback(cfg):
    packet,scopes,private,e,world,sub=_farm_context(cfg)
    paths=_farm_paths(cfg);before=_farm_before(cfg)
    expected,held=_farm_assets(cfg,packet,scopes)
    placed=json.loads(paths['world_journal'].read_text(encoding='utf-8'))
    saved=json.loads(paths['world_save_journal'].read_text(encoding='utf-8'))
    if (placed.get('stage')!='SEVEN_OPAQUE_ACTORS_PLACED_UNSAVED'
            or saved.get('stage')!='ONE_MAP_SAVE_TRUE' or saved.get('save_return') is not True):
        raise RuntimeError('exact seven placed actors and one TRUE map save receipt required')
    guard=_farm_guard(cfg,scopes,held)
    preservation=_farm_assert_old(private,before,placed['actors'].values())
    rows=_farm_validate(private,expected,placed['actors'])
    if not _farm_camera_same(_farm_camera(e),before['camera']):raise RuntimeError('original camera not restored')
    return {'stage':'PARTIAL_GREENHOUSE_SEVEN_PLACED_ONE_MAP_SAVED_READBACK','scene':preservation['scene'],
            'preservation':preservation,'new_actors':rows,'tracked_actor_count':152,'new_actor_count':7,
            'accepted_package_count':13,'held_glass_objects':sorted(held),'guard':guard,'native_mutations':0,
            'limits':'Partial opaque decorative bay; glass absent from world; collision/nav/walking/crops/gameplay unverified.'}
