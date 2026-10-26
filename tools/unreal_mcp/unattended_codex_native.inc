# SPDX-License-Identifier: MIT
# Embedded in the existing retained owner guard, with CFG and unreal supplied.
import copy, hashlib, importlib.util, math, time
from datetime import datetime, timezone

def source(row):
    raw = Path(row['path']).read_bytes()
    if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
        raise RuntimeError('Pinned owner source/input changed')
    return raw

def palette_matches(mesh, palette):
    # Compare the actual existing UObject, not package text against object text.
    return palette is not None and all(mesh.get_material(i) == palette
        for i in range(len(mesh.get_editor_property('static_materials'))))

cfg, item = CFG['policy'], CFG['item']
manifest = json.loads(source(cfg['source_manifest']))
entry = next(row for row in manifest['assets'] if row['name'] == cfg['selected_name'])
ns = {'__name__': '_frozen_codex_coupler_importer', '__file__': cfg['importer']['path']}
exec(compile(source(cfg['importer']), cfg['importer']['path'], 'exec'), ns)
if ns['MATERIAL'] != '/Game/Daedalus/Art/Islands/ClaudeIslands/M_VoxelVertexColour':
    raise RuntimeError('Read-only existing palette identity differs')
source(cfg['material'])
phase = CFG['phase']
ar = unreal.AssetRegistryHelpers.get_asset_registry()
tool = unreal.get_default_object(unreal.AutomationTestToolset)
status = json.loads(tool.call_method('GetTestStatus'))
if (ar.is_loading_assets() or status.get('state') == 'Running'
        or unreal.InterchangeManager.get_interchange_manager_scripted().is_interchange_active()
        or unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).get_active_executor() is not None):
    raise RuntimeError('Active native work; no queue effect')
version = unreal.SystemLibrary.get_engine_version()
if version != CFG['frozen']['engine_version']:raise RuntimeError('Exact engine version differs')
existing = ar.get_assets_by_path(item['destination'], recursive=True)
if phase == 'admit':
    value = {'engine_version': version, 'idle': True, 'policy_verified': True,
             'destination_vacant': not existing}
else:
    if phase == 'import':
        if existing or unreal.EditorAssetLibrary.does_directory_exist(item['destination']):
            raise RuntimeError('Owned destination occupied; never replace/reimport')
        if time.time() > datetime.fromisoformat(cfg['start_by_utc'].replace('Z','+00:00')).timestamp():
            raise RuntimeError('Finite start window expired')
        snapshot = CFG['snapshots'][0];source(snapshot)
        private = copy.deepcopy(manifest)
        selected = next(row for row in private['assets'] if row['name'] == cfg['selected_name'])
        selected['fbx']['path'] = snapshot['path'];selected['destination'] = item['destination']
        file = Path(CFG['folder']) / 'selected-source-manifest.json'
        with file.open('x',encoding='utf-8') as out:json.dump(private,out,indent=2)
        record('ONE_EXISTING_IMPORTER_IMPORT_SAVE_INTENT', {'source': snapshot, 'destination': item['destination']})
        report = ns['import_all'](str(file), str(Path(CFG['folder'])/'existing-importer-report.json'),
                                  deadline_epoch=time.time()+240, asset_names=[cfg['selected_name']])
        record('EXISTING_IMPORTER_RETURNED', report)
        if report['stage'] != 'assets_saved' or report['saved_groups'] != 1 or len(report['results']) != 1:
            raise RuntimeError('Existing importer did not save one qualified group')
        row = report['results'][0]
        if row['import_skipped'] or row['destination'] != item['destination']:
            raise RuntimeError('Expected exactly one fresh effect, not reuse')
        assets = [v['path'] for v in row['meshes']]
        if len(assets) != 1 or any(v['save_return'] is not True for v in row['meshes']):
            raise RuntimeError('Exact one new saved mesh required')
    else:
        assets = CFG['assets']
    meshes = [unreal.EditorAssetLibrary.load_asset(p) for p in assets]
    if len(meshes) != 1 or any(not isinstance(m,unreal.StaticMesh) for m in meshes):
        raise RuntimeError('Exact existing StaticMesh readback absent')
    ns['_verify'](entry, meshes)
    mesh = meshes[0]
    if not mesh.get_path_name().startswith(item['destination']+'/'):
        raise RuntimeError('Output namespace differs')
    slots = mesh.get_editor_property('static_materials')
    body = mesh.get_editor_property('body_setup')
    agg = body.get_editor_property('agg_geom') if body else None
    simple = sum(len(agg.get_editor_property(k)) for k in ('box_elems','sphere_elems','sphyl_elems','convex_elems','tapered_capsule_elems')) if agg else 0
    nanite = bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
    facts = {'path': mesh.get_path_name(), 'triangles': mesh.get_num_triangles(0),
        'material_slots': len(slots), 'simple_collision': simple, 'nanite': nanite,
        'materials': [mesh.get_material(i).get_path_name() if mesh.get_material(i) else None for i in range(len(slots))]}
    palette = unreal.EditorAssetLibrary.load_asset(ns['MATERIAL'])
    if ({k:facts[k] for k in cfg['expect']} != cfg['expect']
            or not isinstance(palette, unreal.MaterialInterface) or not palette_matches(mesh, palette)
            or any(unreal.EditorAssetLibrary.get_metadata_tag(mesh,k) != v for k,v in ns['_tags'](entry).items())):
        raise RuntimeError('Strict source/material/options/metadata profile differs: '+json.dumps(facts))
    if len(ar.get_assets_by_path(item['destination'], recursive=True)) != 1:
        raise RuntimeError('Native inventory expanded beyond one mesh')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Save/preservation incomplete; no blanket save or reset')
    source(cfg['material'])
    if phase == 'validate':
        record('EXACT_NATIVE_VALIDATION_INTENT', {'assets':assets})
        # Match native FDateTime::ToIso8601 millisecond precision (installed
        # DateTime.cpp216-218/281). These are real call-boundary reads, not
        # reconstructed timestamps or a freshness/tolerance override.
        start = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        raw = unreal.DaedalusEditorAcceptanceLibrary.validate_named_assets(assets, item['destination'], False)
        end = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        envelope = json.loads(raw)
        record('EXACT_NATIVE_VALIDATION_RETURNED', envelope)
        value = {'engine_version':version,'envelope':envelope,'start_utc':start,'end_utc':end,
                 'assets':assets,'facts':facts,'qualified_readback':True}
    else:
        value = {'engine_version':version,'assets':assets,'facts':facts,'qualified_readback':True,
                 'fresh_import':phase=='import','new_only_saved':phase=='import'}
