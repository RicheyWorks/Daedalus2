# SPDX-License-Identifier: MIT
"""Strict Residents response validation and file-only completed-R1 verification.

The validators have no side effects. Future callers may wrap an existing reader
with checked_read_native; this module does not dispatch native operations. The
verify_saved command reads frozen delivery evidence and writes one NEW receipt.
It never imports, saves, finalizes, renews/releases leases or edits old receipts.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import inspect
import itertools
import json
import math
from pathlib import Path

NAME = 'TidePen_r1_Residents'
UNIT = 'source_metres_unit100_build1_actor1_v1'
WORLD = '/Game/Daedalus/DaedalusWorld.DaedalusWorld'
MATERIAL = '/Game/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour.M_VoxelVertexColour'
DESTINATION = '/Game/Daedalus/Art/Islands/CodexContest/Ingestion/TidePenResidentsR1_a82c0e1ee724138f'
NATIVE_PATH = DESTINATION + '/' + NAME + '.' + NAME
SOURCE_FP = {'bytes': 22588, 'sha256': 'a82c0e1ee724138fabad7996a5b623a41a6f74c2a200ddfa4e405a404cd5b4bd'}
SHARED_FP = {'bytes': 22414, 'sha256': '00e48d8a86cd377250c439d6992a5bec6deb09b0f77e9607bf7beebd324d1d03'}
NATIVE_SHA = 'b318d059e3fab006b9e9084c1de65561375c0f532ad141b998911771e98578a7'
BOUNDS = {'min': [-11.925145149230957, -7.020364284515381, -.5],
          'max': [14.629093170166016, 8.424022674560547, 2.5]}
PALETTE = [[65,65,71,255], [136,164,128,255], [148,210,158,255],
           [158,186,148,255], [237,136,123,255], [249,217,123,255], [253,237,136,255]]
SOURCE_UNITS = 'metres; FBX UnitScaleFactor100; native centimetres; build1; actor1'
HELD = 'held; asset-only save; native appearance, collision and runtime acceptance unverified'


def _require(condition, message):
    if not condition:
        raise ValueError('Residents receipt contract: ' + message)


def _count(value, expected, name):
    _require(type(value) is int and value == expected, name)


def _object(value, name):
    _require(isinstance(value, dict) and bool(value), name + ' must be a nonempty object')
    _require(not any(key in value for key in ('error', 'error_type', 'exception')), name + ' contains error')
    if 'issues' in value:
        _require(value['issues'] == [], name + ' issues are not empty')
    return value


def _item(cfg):
    _object(cfg, 'config')
    items = cfg.get('items')
    _require(isinstance(items, list) and len(items) == 1, 'exactly one source item')
    item = _object(items[0], 'source item')
    _require(item.get('name') == NAME and item.get('destination') == DESTINATION, 'source identity')
    _require(item.get('fingerprint') == SOURCE_FP and item.get('source_bounds') == BOUNDS,
             'source fingerprint/bounds')
    _count(item.get('triangles'),650,'source triangles')
    _require(item.get('rgba_bytes') == PALETTE, 'source palette')
    _require(item.get('source_unit_scale_factor') == 100 and item.get('required_future_actor_scale') == [1.,1.,1.],
             'source metre units/actor scale')
    _require(bool(item.get('provenance')) and isinstance(item.get('author'), str), 'source provenance/author')
    return item


def _guard(value):
    value = _object(value, 'native guard')
    for key in ('dirty_map_packages', 'dirty_content_packages', 'other_running_generators'):
        _require(value.get(key) == [], key)
    for key in ('queued_jobs', 'unfinished_async_job_boxes'):
        _require(type(value.get(key)) is int and value[key] == 0, key)
    for key in ('pie_running', 'remote_execution_lock_locked'):
        _require(value.get(key) is False, key)
    _require(value.get('editor_world') == WORLD, 'editor world')
    # These are explicitly unqueried in the established native guard, not inferred clear.
    for key in ('background_compilation', 'epic_mcp_other_sessions'):
        _require(value.get(key) == 'not_queried', key + ' witness scope')


def _vector(value, name):
    _require(isinstance(value, list) and len(value) == 3
             and all(type(v) in (int, float) and math.isfinite(v) for v in value), name)
    return value


def _box(value, name):
    _object(value, name)
    lo, hi = _vector(value.get('min'), name + '.min'), _vector(value.get('max'), name + '.max')
    _require(all(a < b for a,b in zip(lo,hi)), name + ' positive dimensions')
    return lo, hi


def _close(actual, expected, tolerance=.1):
    return len(actual) == len(expected) and all(abs(a-b) <= tolerance for a,b in zip(actual,expected))


def _metadata(item):
    provenance = item['provenance']
    if not isinstance(provenance, str):
        provenance = json.dumps(provenance, sort_keys=True, allow_nan=False)
    dimensions = [(BOUNDS['max'][i] - BOUNDS['min'][i])*100 for i in range(3)]
    return {'codex_owner': 'codex-contest', 'codex_sha256': SOURCE_FP['sha256'],
            'codex_source_fbx': str(item['fbx']), 'codex_author': item['author'],
            'codex_source_provenance': provenance, 'codex_unit_contract': UNIT,
            'codex_required_actor_scale': '1,1,1',
            'codex_intended_dimensions_cm': ','.join(format(v, '.12g') for v in dimensions),
            'codex_world_placement': HELD}


def _observed(value, item):
    value = _object(value, 'observed mesh')
    _require(value.get('issues') == [], 'mesh issues')
    _require(value.get('native_path') == NATIVE_PATH and value.get('native_class') == 'StaticMesh', 'native identity')
    _require(value.get('source_bounds') == BOUNDS, 'geometry source')
    _count(value.get('triangles'),650,'native triangle count')
    for key in ('observed_build_scale3d', 'required_future_actor_scale'):
        _require(value.get(key) == [1.,1.,1.], key)
    _require(value.get('unit_contract') == UNIT and value.get('source_units') == SOURCE_UNITS, 'native unit contract')
    _require(value.get('import_data_class') == 'InterchangeAssetImportData', 'Interchange readback')
    for key in ('nanite_enabled', 'observed_generate_lightmap_u_vs', 'persistent_mesh_modified'):
        _require(value.get(key) is False, key)
    _require(type(value.get('simple_collision_count')) is int and value['simple_collision_count'] == 0, 'simple collision')
    _require(value.get('slots') == [{'slot':'VoxelVertexColour', 'material':MATERIAL}], 'single inherited palette slot')
    _require(value.get('metadata') == _metadata(item), 'exact nine source/native metadata values')
    _require(value.get('source_copy_outcome') == '<GeometryScriptOutcomePins.SUCCESS: 1>', 'source copy success')
    lo,hi = _box(value.get('native_bounds_cm'), 'native bounds')
    dims = _vector(value.get('native_dimensions_cm'), 'native dimensions')
    _require(_close(dims, [hi[i]-lo[i] for i in range(3)], 1e-5), 'bounds/dimensions disagreement')
    projected = _vector(value.get('projected_dimensions_cm_at_required_actor_scale'), 'projected dimensions')
    _require(projected == dims, 'actor1 projected dimensions')
    slo,shi = _box(value.get('native_source_bounds_with_build_scale'), 'native source bounds')
    _require(_close(lo,slo) and _close(hi,shi), 'render/source bounds agreement')
    _require(value.get('expected_native_bounds_cm') == {k:[v*100 for v in BOUNDS[k]] for k in ('min','max')},
             'unconverted expected source bounds')
    conversions = value.get('matching_fbx_axis_conversions')
    _require(isinstance(conversions,list) and bool(conversions), 'missing actual axis conversion witness')
    permitted = []
    for axes in ((0,1),(1,0)):
        for signs in itertools.product((-1,1),repeat=2):
            lower,upper = [],[]
            for axis,sign in zip(axes+(2,), signs+(1,)):
                ends = [BOUNDS[k][axis]*100*sign for k in ('min','max')]
                lower.append(min(ends)); upper.append(max(ends))
            if _close(lo,lower) and _close(hi,upper):
                permitted.append({'native_x_source_axis':'xy'[axes[0]], 'native_x_sign':signs[0],
                    'native_y_source_axis':'xy'[axes[1]], 'native_y_sign':signs[1],
                    'native_z_source_axis':'z', 'native_z_sign':1, 'unit_multiplier':100,
                    'expected_native_bounds_cm':{'min':lower,'max':upper}})
    _require(conversions == permitted and bool(permitted), 'axis/source-unit proof differs')
    colours = _object(value.get('vertex_colours'), 'vertex colours')
    _count(colours.get('triangles'),650,'vertex colour triangle count')
    _require(colours.get('all_triangle_corners_valid') is True
             and colours.get('all_triangle_faces_flat') is True, 'flat triangle colours')
    _require(colours.get('source_match') == 'direct_rgba_bytes'
             and colours.get('direct_rgba_bytes') == PALETTE and colours.get('expected_rgba_bytes') == PALETTE
             and colours.get('persistent_mesh_modified') is False, 'direct byte palette/no source mutation')
    floats = colours.get('unique_rgba')
    _require(isinstance(floats,list) and len(floats) == len(PALETTE), 'float palette count')
    for row,expected in zip(floats,PALETTE):
        _require(isinstance(row,list) and len(row)==4 and all(type(v) in (int,float) and math.isfinite(v) for v in row)
                 and _close(row,[v/255 for v in expected],1e-6), 'float/direct byte palette disagreement')


def validate_preflight(value, cfg):
    """Validate a decoded native preflight response; return it unchanged."""
    item = _item(cfg); value = _object(value, 'preflight response')
    _guard(value.get('guard'))
    _require(value.get('items') == [item], 'preflight exact item')
    _count(value.get('requested_count'),1,'preflight requested count')
    _require(value.get('destinations') == [{'name':NAME,'destination_absent':True,'global_name_collisions':[]}],
             'fresh destination proof')
    _require(value.get('material') == MATERIAL and value.get('shared_helpers') == SHARED_FP, 'shared helper/material pins')
    _require(value.get('shared_guard_label_scope') == 'private fresh namespace only'
             and value.get('max_source_triangles_per_asset') == 3000, 'preflight profile')
    return value


def validate_readback(value, cfg):
    """Validate the actual native contract (which has no stage field)."""
    item = _item(cfg); value = _object(value, 'readback response')
    _guard(value.get('preflight')); _guard(value.get('post_read_preflight'))
    _count(value.get('requested_packet_count'),1,'readback requested count')
    _count(value.get('readback_count'),1,'readback count')
    _require(value.get('not_read_back_names') == [], 'readback omitted names')
    for key in ('world_saved','shared_material_modified','persistent_mesh_modified'):
        _require(value.get(key) is False, key)
    _require(type(value.get('world_placed')) is int and value['world_placed'] == 0
             and value.get('world_references') == [], 'world-held proof')
    rows = value.get('items')
    _require(isinstance(rows,list) and len(rows)==1, 'one readback item')
    row = _object(rows[0], 'readback item')
    _require(row.get('name') == NAME and row.get('native_path') == NATIVE_PATH, 'readback role/path')
    _observed(row.get('observed'),item)
    return value


def checked_read_native(reader, value, cfg, operation):
    """Explicit opt-in wrapper; never replace or dispatch a reader implicitly."""
    _require(operation in ('preflight','readback'), 'unsupported reader operation')
    result = reader(value,cfg,operation)
    return {'preflight':validate_preflight,'readback':validate_readback}[operation](result,cfg)


def _snapshot_self_request(d):
    """Reconstruct only the pinned snapshot's string expression, without dispatch."""
    function=d._scene_snapshot
    tree=ast.parse(inspect.getsource(function))
    assignment=next(node for node in tree.body[0].body if isinstance(node,ast.Assign)
                    and any(isinstance(target,ast.Name) and target.id=='code' for target in node.targets))
    def text(node):
        if isinstance(node,ast.Constant) and isinstance(node.value,str): return node.value
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add): return text(node.left)+text(node.right)
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='_snap_definition'
                and not node.args and not node.keywords):
            return function.__globals__['_snap_definition']()
        raise ValueError('Residents receipt contract: snapshot source expression changed')
    return {'type':'execute_python','code_sha256':hashlib.sha256(text(assignment.value).encode()).hexdigest()}


def verify_saved(folder=None):
    """File-only verification of the already completed R1; no native calls."""
    import codex_qualified_static_delivery as d
    import codex_tidepen_residents_delivery as h
    folder = Path(folder) if folder is not None else h.DELIVERY
    _require(folder.resolve() == h.DELIVERY.resolve(), 'exact completed R1 folder required')
    target = folder/'strict-receipt-verification.json'
    _require(not target.exists(), 'retained strict verification exists; never overwrite')
    paths = {name:folder/name for name in ('prepared.json','dispatch.json','native.json','native-readback.json',
             'readback.json','compute-release.json','saved-production-baseline.json')}
    pins = {name:d.pin(path) for name,path in paths.items()}
    saved = {name:d.load(path) for name,path in paths.items()}
    prepared,dispatch,native,report,final,release,baseline = [saved[name] for name in paths]
    for key in ('qualification','baseline','native_source','shared_source'):
        d._check(prepared[key])
    for pin in prepared['source_pins']: d._check(pin)
    _require(prepared['native_source']['sha256'] == NATIVE_SHA and d.fp(prepared['shared_source']) == SHARED_FP,
             'exact frozen native sources')
    admission=d.load(prepared['qualification']['path']); qualification=d.load(h.QUALIFICATION)
    _require(d.pin(h.QUALIFICATION)['sha256'] == h.QUALIFICATION_SHA
             and d.pin(h.F/'source-audit.json')['sha256'] == h.AUDIT_SHA, 'original qualification/audit pins')
    _require(admission['items'] == qualification['items'] == prepared['items'], 'admission/source/prepared identity')
    _require(admission.get('native_dispatch_eligible') is True and admission.get('unit_metadata_blocker_resolved') is True
             and admission.get('native_intake_profile_blocker') is None, 'closed adapter admission')
    d._check(admission['original_source_qualification']); d._check(admission['producer_release'])
    _require(admission['original_source_qualification'] == d.pin(h.QUALIFICATION), 'qualification provenance identity')
    producer=d.load(admission['producer_release']['path'])
    _require(producer.get('id')==32582 and producer.get('from')=='unreal-team'
             and producer.get('to')=='codex-play-guard' and producer.get('reply_to')==32563
             and 'Asset-only import/save of small static roles into YOUR OWN CodexContest namespace is released'
             in producer['body']['text'], 'exact asset-only producer release')
    cfg={'items':prepared['items']}; item=_item(cfg)
    validate_preflight(dispatch['native_preflight'],cfg); validate_preflight(native['initial_preflight'],cfg)
    _require(dispatch.get('stage')=='qualified_static_assets_saved_world_held'
             and dispatch.get('replay_permitted') is False, 'dispatch complete/no replay')
    _require(native.get('schema')=='daedalus.codex-tidepen-residents-native.v1'
             and native.get('stage')=='qualified_static_assets_saved_world_held'
             and native.get('save_return') is True and native.get('requested_count')==1
             and native.get('completed_count')==1 and native.get('replay_permitted') is False,
             'actual native terminal first-save success')
    _count(native.get('requested_count'),1,'native requested count')
    _count(native.get('completed_count'),1,'native completed count')
    _count(native.get('world_placed'),0,'native world placement count')
    _require(native.get('unit_contract')==UNIT and native.get('required_future_actor_scale')==[1.,1.,1.]
             and native.get('source_units')==SOURCE_UNITS and native.get('world_placed')==0
             and native.get('world_saved') is False and native.get('shared_material_modified') is False,
             'native unit/world contract')
    _require(isinstance(native.get('items'),list) and len(native['items'])==1, 'native single item')
    row=native['items'][0]
    _require(row.get('name')==NAME and row.get('source')==item and row.get('native_path')==NATIVE_PATH
             and row.get('stage')=='asset_saved_world_held' and row.get('save_return') is True
             and row.get('imported_object_paths')==[NATIVE_PATH] and row.get('destination_asset_paths')==[NATIVE_PATH],
             'single exact imported/saved output')
    expected_options={'backend':'explicit_InterchangePipelineStackOverride','build_scale3d':[1.,1.,1.],
        'vertex_colors':'REPLACE','bake_meshes':True,'build_nanite':False,'generate_lightmap_u_vs':False,
        'collision':False,'import_materials':False,'replace_existing':False,'task_save':False}
    _require(native.get('requested_options')==expected_options, 'exact requested import/save options')
    for key in ('bake_meshes','build_nanite','generate_lightmap_u_vs','collision','import_materials','replace_existing','task_save'):
        _require(native['requested_options'][key] is expected_options[key], 'option type '+key)
    intents=row.get('mutation_intents')
    _require(isinstance(intents,list) and len(intents)==3, 'exact three mutation intents')
    for intent,operation,path_key in zip(intents,('import_exact_one_static','bind_existing_material_and_source_metadata',
            'save_exact_owned_asset'),('expected_path','path','path')):
        _require(intent.get('operation')==operation and intent.get(path_key)==NATIVE_PATH, 'bounded intent operation/path')
    _require(row.get('expected_metadata')==_metadata(item), 'native intended metadata')
    _observed(row.get('observed'),item); _guard(row.get('post_save_preflight'))
    validate_readback(report.get('native_readback'),cfg)
    _require(report.get('stage')=='qualified_static_assets_saved_readback_complete' and report.get('issues')==[],
             'completed independent readback')
    for name in ('dispatch.json','native.json'):
        _require(report['original_receipts'][name]==pins[name], 'original receipt pin '+name)
    _require(dispatch['prepared']==pins['prepared.json'] and dispatch['native']==pins['native.json'], 'dispatch source/journal pins')
    output={NATIVE_PATH:d.fingerprint(d._asset_file(NATIVE_PATH))}
    _require(dispatch['outputs']==report['outputs']==final['outputs']==output, 'actual output hash')
    for key,value in report.items(): _require(final.get(key)==value, 'final receipt differs '+key)
    _require(final['native_readback_receipt']==pins['native-readback.json']
             and final['baseline']==pins['saved-production-baseline.json']
             and final.get('native_mutations_in_finalize')==0
             and final.get('compute_release_status')=='packet_lease_released_verified', 'file finalization pins')
    _require(release.get('stage')=='released_verified' and release.get('reply',{}).get('ok') is True
             and release['reply'].get('lock') is None and not release.get('locks_after',{}).get('compute'),
             'historical compute release receipt')
    old=d.load(prepared['baseline']['path']); d.protect(old); d.protect(baseline)
    _require(len(old['packages'])==217 and len(baseline['packages'])==218 and baseline['package_count']==218
             and baseline['packages']=={**old['packages'],**output}, 'exact package increment')
    d._same_scene(report['scene'],old['scene'])
    _require(baseline['scene']==old['scene'] and len(old['scene']['actors'])==145
             and baseline['map']==old['map'] and report['map']==d.fp(old['map']), 'unchanged scene/map')
    scene=report['scene']
    _require(scene.get('pie') is False and scene.get('remote_locked') is False
             and scene.get('dirty_maps')==[] and scene.get('dirty_content')==[], 'file-retained scene guard states')
    _require(scene.get('running') in ([],[_snapshot_self_request(d)]), 'only exact snapshot self request may be running')
    _count(scene.get('queued'),0,'scene queue count')
    _count(scene.get('unfinished_async_job_boxes'),0,'scene async boxes')
    _require(baseline['provenance']=={'previous_baseline':prepared['baseline'],'increment':pins['native-readback.json']},
             'baseline provenance chain')
    for key in ('world_placed','world_saved','import_replayed','save_replayed'):
        _require(report.get(key)=={'world_placed':0,'world_saved':False,'import_replayed':False,'save_replayed':False}[key],
                 'readback scope '+key)
    _require(report.get('prior_packages_preserved')==217 and report.get('total_tracked_packages')==218
             and report.get('source_files_preserved')==184 and report.get('readback_names')==[NAME]
             and report.get('not_read_back_names')==[], 'readback totals')
    for name,pin in pins.items(): d._check(pin)
    proof={'schema':'daedalus.codex-tidepen-residents-strict-receipt-verification.v1',
           'utc':datetime.now(timezone.utc).isoformat(), 'stage':'saved_r1_strict_contract_verified', 'issues':[],
           'verifier':d.pin(__file__), 'receipts':pins, 'qualification':d.pin(h.QUALIFICATION),
           'admission':prepared['qualification'], 'producer_release':admission['producer_release'],
           'outputs':output, 'native_path':NATIVE_PATH, 'triangles':650, 'palette_entries':7,
           'unit_contract':UNIT, 'actor_scale':[1.,1.,1.], 'packages':218, 'preserved_actors':145,
           'accepted_source_files':184, 'world_placed':0, 'world_saved':False,
           'native_calls':0, 'import_replayed':False, 'save_replayed':False,
           'original_receipts_modified':False,
           'limits':'File-only qualification of retained native witnesses and current saved bytes; no fresh editor/appearance/runtime observation.'}
    d.write_new(target,proof)
    return {'stage':proof['stage'],'receipt':d.pin(target),'outputs':output,'native_calls':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('verify_saved',))
    parser.add_argument('--folder',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify_saved(args.folder),indent=2,allow_nan=False))
