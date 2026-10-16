# SPDX-License-Identifier: MIT
"""Corn existing-alias recovery; prepare is file-only, run needs a NEW grant.

Reuse the existing transport, dispatch retention, opaque GLB pipeline, graph/
geometry inspectors and preservation helpers. No automatic replay or cleanup.
"""
import argparse
import ast
import base64
import copy
import ctypes
from datetime import datetime,timezone
import hashlib
import json
import re
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

import codex_skyfarm_greenhouse_delivery as receiving
from codex_tidepen_queue_manifest import glb

d=receiving.d
REPO=Path(__file__).resolve().parents[2]
TASK=REPO.parent
NATIVE=REPO/'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_skyfarm_corn.py'
ROOT='/Game/Daedalus/Art/SkyFarm/CornPolishR1'
SOURCE_MESH='Prop_Harvest3_Corn_Polish_R1'
NAMES=('Harvest3_CornPolish_R1','H3C_R1_AFTER_stalk','H3C_R1_AFTER_leaf','H3C_R1_AFTER_cob')
PATHS=tuple(ROOT+'/'+n+'.'+n for n in NAMES)
HELD=tuple('/Game/Daedalus/Art/SkyFarm/GreenhouseBayR1/'+n for n in ('SFG_R1_glass','SFG_R1_glass_glass'))
MARKER='# Codex SkyFarm CornPolishR1 closed33079'
START_BY=datetime(2026,10,16,11,30,tzinfo=timezone.utc).timestamp()
SOURCE=Path('C:/Users/730ri/Documents/Codex/2026-10-13/task-3/harvest3-corn-polish-delivery-r2')
BASE=TASK/'native-ingestion/SkyFarmGreenhouseBayR1/DeliveryR1/RecoveryR2/saved-production-baseline.json'
ORIGINAL=TASK/'native-ingestion/Harvest3CornR1/BoundR2'
RUNTIME_ASSIGNMENT='skyfarm-corn-alias-recovery-r1'
_old_file=d._asset_file


def asset_file(path):
    if path.startswith(ROOT+'/'):
        name=path[len(ROOT)+1:].split('.')[0]
        if name not in NAMES or path not in (ROOT+'/'+name,ROOT+'/'+name+'.'+name):raise ValueError('closed Corn allowlist required')
        return Path('C:/Unreal/DaedalusRealm/Content/Daedalus/Art/SkyFarm/CornPolishR1')/(name+'.uasset')
    return _old_file(path)


d._asset_file=asset_file


def prepare(a):
    if a.folder.exists():raise RuntimeError('fresh packet folder required; retain all old evidence')
    if a.folder.resolve()!=TASK/'native-ingestion/Harvest3CornR1/AliasRecoveryR2':raise ValueError('exact distinct recovery packet required')
    original=d.load(ORIGINAL/'native.json');released=d.load(ORIGINAL/'compute-release.json')
    if (d.fingerprint(ORIGINAL/'native.json')['sha256']!='69d92bbfe85c5fab610bf003ebc9f2741ff909b199ec8d226844119860754878'
            or d.fingerprint(ORIGINAL/'compute-release.json')['sha256']!='e77ffa0eb697d295cb2136e8792310817163444b6b2b4a116175014a4c82a1e6'
            or original.get('stage')!='CORN_KNOWN_TERMINAL_PARTIAL_HOLD' or original.get('saves')!=[]
            or original.get('new_actor')is not None or original.get('map_save_return')is not None
            or len(original.get('intents',[]))!=1 or set(original['imported_object_paths'])!=set(PATHS)
            or released.get('reply')!={'ok':True,'lock':None}):raise RuntimeError('exact released one-import/zero-save alias boundary required')
    source=SOURCE/'after/Prop_Harvest3_Corn_Polish_R1.glb';manifest=SOURCE/'manifest.json'
    if d.fingerprint(source)!=dict(bytes=156624,sha256='9925a5462ff97be7c69496c70453a7ff45ea268ea11583902f8dad0cc7301127'):raise ValueError('accepted AFTER GLB changed')
    if d.fingerprint(manifest)!=dict(bytes=12074,sha256='0411f227423f33fed0b8b625a1274fef435b1d0fb7369b413b609cd919031bb7'):raise ValueError('accepted Corn manifest changed')
    data=glb(source);nodes=data['nodes']
    if len(nodes)!=1 or nodes[0]['authored_transform_fields'] or len(nodes[0]['primitives'])!=3 or len(data['materials'])!=3 or data['images'] or data['textures']:raise ValueError('exact identity joined3primitive factor-only payload required')
    primitives=nodes[0]['primitives']
    if (nodes[0]['name']!=SOURCE_MESH or [p['material_index'] for p in primitives]!=[0,1,2]
            or sum(p['triangles_decoded_from_index_count'] for p in primitives)!=2592
            or any(set(p['attributes'])!={'POSITION','NORMAL'} for p in primitives)
            or [m['name'] for m in data['materials']]!=list(NAMES[1:])):raise ValueError('exact names/material order/2592tri/source normals required')
    bounds={edge:[(min if edge=='min' else max)(p['position_bounds_decoded_node_world'][edge][i] for p in primitives) for i in range(3)] for edge in ('min','max')}
    baseline=d.load(BASE)
    if d.fingerprint(BASE)['sha256']!='7d7a33679e79b909b7f382a42144bbceccff475281e3cdbd2248e0b829e4614e':raise RuntimeError('exact current saved baseline required')
    witness=TASK/'native-ingestion/SkyFarmGreenhouseBayR1/GlassGraphR1/CompatibilityR2/native-terminal.json'
    if d.fingerprint(witness)['sha256']!='3bc8f316c87c3a338ef9da1594c83d776d08bfa7eb109a34fce848e180324a45':raise RuntimeError('exact retained current world witness required')
    scope=d.load(a.scope)
    if not any(m.get('id')==33079 and m.get('from')=='pootscoot-coordination' and m.get('to')=='codex-play-guard' for m in scope['messages']):raise ValueError('actual33079 scope required')
    if not any(m.get('id')==33103 and m.get('from')=='pootscoot-coordination' and m.get('type')=='source.continuation' for m in scope['messages']):raise ValueError('actual source-only recovery assignment required')
    if any(asset_file(path).exists() for path in PATHS):raise RuntimeError('all Corn first saves must remain unattempted')
    a.folder.mkdir(parents=True);(a.folder/'graph-witnesses').mkdir()
    packet={'mesh':{'name':SOURCE_MESH,'triangles':2592,'local_bounds':bounds,'world_bounds':bounds,'transform':{}},
        'materials':data['materials'],'source_primitives':primitives,'original_source_anchor':'UNBOUND lineage only'}
    d.write_new(a.folder/'source-packet.json',packet)
    snap=a.folder/'snap.py';snap.write_text(receiving.original._snap_definition(),encoding='utf-8')
    native_dir=NATIVE.parent
    helpers={k:d.pin(native_dir/name) for k,name in {
        'inventory':'daedalus_codex_sunspool_subset.py','geometry':'daedalus_codex_copperfall_subset.py',
        'direct':'daedalus_codex_skyfarm_direct_material.py','graph':'daedalus_codex_canal_material.py',
        'farm':'daedalus_codex_skyfarm_greenhouse.py','catalogue':'daedalus_codex_catalogue.py'}.items()}
    world=d.load(witness);camera=baseline['scene']['camera']
    original_camera={group:[camera[group][k] for k in keys] for group,keys in [('location',('x','y','z')),('rotation',('pitch','yaw','roll'))]}
    cfg={'source':d.pin(source),'manifest':d.pin(manifest),'packet':d.pin(a.folder/'source-packet.json'),'baseline':d.pin(BASE),
        'helpers':helpers,'snap':d.pin(snap),'world_helper':d.pin(REPO/'tools/unreal/codex_canal_water_placement_native.py'),
        'expected_world_digest':world['after']['world_digest'],'original_camera':original_camera,
        'original_import':d.pin(ORIGINAL/'native.json'),
        'journal':str(a.folder/'native.json'),'camera_journal':str(a.folder/'camera-native.json'),
        'witness_directory':str(a.folder/'graph-witnesses')}
    after=d.load(manifest)['variants']['after'];d._check(after['hero'])
    value={'stage':'CORN_ALIAS_RECOVERY_SOURCE_ONLY_RUNTIME_UNGRANTED','utc':d._utc(),'scope':d.pin(a.scope),'cfg':cfg,
        'native_source':d.pin(NATIVE),'host_source':d.pin(Path(__file__)),
        'world_guard':d.pin(TASK/'build_gallery_dispatch_spur.py'),'source_view':after['hero'],
        'source_view_personally_inspected_by_operator':True,'exact_native_allowlist':list(PATHS),
        'actor_label':'CodexSkyFarm_CornPolishR1_Decorative','native_calls':0,'compute_claims':0,
        'original_release':d.pin(ORIGINAL/'compute-release.json'),
        'gate':'New source CLEAR plus DISTINCT finite runtime grant required; no consumed33079 replay.',
        'runtime_assignment':RUNTIME_ASSIGNMENT,'runtime_authorized':False}
    d.write_new(a.folder/'prepared.json',value)
    print(json.dumps({'stage':value['stage'],'prepared':d.pin(a.folder/'prepared.json'),'native_calls':0}))


def prepared(a):
    p=d.load(a.folder/'prepared.json')
    for key in ('native_source','host_source','world_guard','source_view','scope','original_release'):d._check(p[key])
    cfg=p['cfg']
    for key in ('source','manifest','packet','baseline','snap','world_helper','original_import'):d._check(cfg[key])
    for row in cfg['helpers'].values():d._check(row)
    return p


def dispatch(a,p,cfg,name,function,arg=None):
    guards(a,p,cfg)
    row=p['native_source']
    body=('from pathlib import Path\nimport hashlib\npin='+repr(row)+'\nraw=Path(pin["path"]).read_bytes()\n'
        'if hashlib.sha256(raw).hexdigest()!=pin["sha256"]:raise RuntimeError("Corn source changed")\n'
        'scope={"__name__":"_corn_delivery","__file__":pin["path"]}\nexec(compile(raw,pin["path"],"exec"),scope)\n'
        'result=scope['+repr(function)+']('+repr(cfg)+((', '+repr(arg)) if arg is not None else '')+')\n')
    tree=ast.parse(Path(p['world_guard']['path']).read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='native')
    value=next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
    code=eval(compile(ast.Expression(value),'<existing-guarded-route>','eval'),dict(MARKER=MARKER,body=body,dirty=False,owned=list(HELD)+[p.split('.')[0] for p in PATHS]))
    return receiving.retained_call(a,name,'execute_python',code,unattended=False,timeout=240 if function=='run' else 110)


def guards(a,p,cfg):
    prepared(a);d._lease();receiving.resources()
    claim=d.load(a.folder/'claim.json')['compute_claim']['lock']
    if not d.same_compute_lease(d.locks().get('compute',{}),claim):raise RuntimeError('exact compute reservation changed')
    if time.time()>cfg['deadline_epoch']-90:raise RuntimeError('absolute90second reserve reached; no renewal/replay')


def run(a):
    p=prepared(a)
    if (a.folder/'claim.json').exists():raise RuntimeError('retained claim; reconcile without replay')
    if time.time()>START_BY:raise RuntimeError('33079 start-by passed; no launch')
    clear=json.loads(a.review.read_text(encoding='utf-8-sig'))
    if clear.get('clear')is not True or clear.get('prepared_sha256')!=d.fingerprint(a.folder/'prepared.json')['sha256']:
        raise RuntimeError('exact Corn source gate missing; no claim/dispatch')
    # A source CLEAR or the consumed33079/33091 receipts grant no new attempt.
    # Require an addressed, finite NEW runtime grant from the established hub.
    prerequisite=json.loads(a.prerequisite.read_text(encoding='utf-8-sig'))
    rows=prerequisite['messages']
    grants=[m for m in rows if m.get('from')=='pootscoot-coordination' and m.get('to')=='codex-play-guard'
        and m.get('id',0)>33103 and m.get('type')=='grant'
        and m.get('body',{}).get('assignment_id')==RUNTIME_ASSIGNMENT]
    if len(grants)!=1:raise ValueError('distinct addressed alias-recovery runtime grant required')
    granted_start=datetime.fromisoformat(grants[0]['body']['start_by_utc'].replace('Z','+00:00'))
    if granted_start.tzinfo is None or granted_start.utcoffset()!=timezone.utc.utcoffset(granted_start):
        raise ValueError('runtime start-by must have explicit zero-offset UTC timezone')
    start_by=min(START_BY,granted_start.timestamp())
    if time.time()>start_by:raise RuntimeError('new finite runtime start-by passed; no claim')
    d.protect(d.load(p['cfg']['baseline']['path']));lease=d._lease();memory=receiving.resources()
    if d.locks().get('compute'):raise RuntimeError('competing compute; wait actual terminal/release')
    process=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        "Get-Process -Id 42564 -ErrorAction Stop | Select-Object Id,Path,@{n='start_utc';e={$_.StartTime.ToUniversalTime().ToString('o')}} | ConvertTo-Json -Compress"],text=True))
    if process['Id']!=42564 or not process['Path'].endswith('UnrealEditor.exe'):raise RuntimeError('existing editor42564 identity differs')
    receiving.exclusive_copy(d.MAP_FILE,a.folder/'before-corn.umap')
    d.write_new(a.folder/'admission.json',{'utc':d._utc(),'memory':memory,'editor':process,'prerequisite':d.pin(a.prerequisite),'prepared':d.pin(a.folder/'prepared.json')})
    if time.time()>start_by:raise RuntimeError('start-by reached before claim')
    reply=d.post('/lock',{'me':d.OWNER,'name':'compute','ttl':600,'note':'NEW Corn existing-alias recovery: ZERO imports;4firstsaves/at most1decorative actor/one map save/capture+restore. Preserve held2glass and original world. No Play/build/Blender/oldactor moves.'})
    if reply.get('ok')is not True or not d.same_compute_lease(d.locks().get('compute',{}),reply.get('lock',{})):raise RuntimeError('claim unconfirmed; no launch')
    cfg={**p['cfg'],'deadline_epoch':min(reply['lock']['at']+600,lease['at']+lease['ttl'])}
    d.write_new(a.folder/'claim.json',{'utc':d._utc(),'compute_claim':reply,'cfg':cfg})
    if time.time()>start_by:raise RuntimeError('start-by reached; retain reservation for explicit closure')
    native=dispatch(a,p,cfg,'intake','run')
    if native.get('known_terminal')is not True:raise RuntimeError('unknown native outcome; retain custody/lease')
    capture=None;restored=None;readback=None;capture_error=None
    if native['stage']=='CORN_FOUR_ASSETS_ONE_ACTOR_ONE_MAP_SAVED':
        framed=False;uncertain=False
        try:
            frame=dispatch(a,p,cfg,'camera-frame','camera','frame')
            if not isinstance(frame,dict) or frame.get('stage')!='FRAMED':raise RuntimeError('frame outcome not confirmed; reconcile without capture/forced restore')
            framed=True
            guards(a,p,cfg);d.write_new(a.folder/'capture-dispatch.json',{'utc':d._utc(),'replay_permitted':False})
            try:raw=d.wire.call(d.wire.UNREAL,'viewport_screenshot',width=1280,height=720,timeout=70,side='Unreal')
            except Exception:uncertain=True;raise
            d.write_new(a.folder/'capture-reply.json',raw);result=raw.get('result',raw)
            image=base64.b64decode(result['image_png_base64'],validate=True)
            if not image.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('actual PNG missing')
            with (a.folder/'native-corn.png').open('xb') as stream:stream.write(image)
            capture=d.pin(a.folder/'native-corn.png')
        except Exception as exc:
            if uncertain or not framed:raise
            capture_error={'type':type(exc).__name__,'error':str(exc)}
        finally:
            if framed and not uncertain:
                restored=dispatch(a,p,cfg,'camera-restore','camera','restore')
                if not isinstance(restored,dict) or restored.get('stage')!='RESTORED':raise RuntimeError('camera restore not confirmed; retain custody/journal')
        readback=dispatch(a,p,cfg,'independent-readback','readback')
        if not isinstance(readback,dict) or readback.get('stage')!='CORN_SAVED_INDEPENDENT_READBACK':raise RuntimeError('independent readback unconfirmed; preserve partial state')
    terminal={'utc':d._utc(),'stage':'CORN_SAVED_CAPTURE_FAILED' if capture_error else native['stage'],'native':d.pin(a.folder/'native.json'),'capture':capture,'capture_error':capture_error,'restored':restored,
        'readback':d.pin(a.folder/'independent-readback-result.json') if readback else None,'known_terminal':True,
        'limits':'Native graph/bounds and one decorative patch only; no harvest/navigation/realm/deed authority.'}
    d.write_new(a.folder/'terminal.json',terminal)
    if not d.same_compute_lease(d.locks().get('compute',{}),reply['lock']):raise RuntimeError('lease identity differs; no release')
    unlock=d.post('/unlock',{'me':d.OWNER,'name':'compute'});after=d.locks()
    if unlock.get('ok')is not True or after.get('compute'):raise RuntimeError('normal release unconfirmed')
    d.write_new(a.folder/'compute-release.json',{'utc':d._utc(),'reply':unlock,'locks_after':after,'terminal':d.pin(a.folder/'terminal.json')})
    print(json.dumps({'stage':terminal['stage'],'terminal':d.pin(a.folder/'terminal.json'),'release':d.pin(a.folder/'compute-release.json')}))


def prepare_normal_repair(a):
    """SOURCE ONLY33219. There is deliberately no repair-dispatch CLI phase."""
    expected=TASK/'native-ingestion/Harvest3CornR1/NormalRepairSourceR1'
    if a.folder.resolve()!=expected or (a.folder/'prepared.json').exists():raise RuntimeError('exact fresh normal-repair source packet required')
    scope=d.load(a.scope)
    if not any(m.get('id')==33219 and m.get('type')=='source.assignment'
               and m.get('from')=='pootscoot-coordination' and m.get('body',{}).get('source_only')is True for m in scope['messages']):
        raise RuntimeError('actual source-only33219 assignment required')
    evidence=TASK/'native-ingestion/Harvest3CornR1/RenderNormalsR1'
    report=d.load(evidence/'diagnosis-and-proposal.json')
    if (d.fingerprint(evidence/'diagnosis-and-proposal.json')['sha256']!='bf9b3da53974b63548660c9680cb7b50bd7fe4010ef37e32997b73d0e62464d0'
            or report['full_multiplicity_normal_comparison']['source_quantized_mismatch_components']!=144):
        raise RuntimeError('exact actual authored-normal mismatch evidence required')
    previous=d.load(TASK/'native-ingestion/Harvest3CornR1/AliasRecoveryR2/prepared.json')
    # The prior packet remains byte-for-byte frozen; its executed source was
    # archived before these own source edits. No native state is queried here.
    supports={
        'reader':evidence/'native-reader.py','normal_contract':evidence.parent/'NormalDiagnosisR1/normal_contract.py',
        'raw_contract':evidence/'render_compare.py','source_normals':evidence.parent/'NormalDiagnosisR1/source-normal-triangles.json',
        'prior_raw':evidence/'native.json','archived_corn':a.folder/'native-used-4911c6fd.py',
        'engine_types':Path('C:/Program Files/Epic Games/UE_5.8/Engine/Source/Runtime/Engine/Classes/Engine/EngineTypes.h')}
    if d.fingerprint(supports['archived_corn'])['sha256']!='32f06960a47ce6bc5ce8eee48c2a2dc4fbc01773fbdd368e945e88b558cf1788':
        raise RuntimeError('exact executed Corn source archive required')
    witnesses=a.folder/'graph-witnesses';witnesses.mkdir()
    cfg={**previous['cfg'],'source_only':True,'repair_runtime_grant':None,'witness_directory':str(witnesses),
         'repair_support':{k:d.pin(v) for k,v in supports.items()},
         'normal_repair_journal':str(a.folder/'normal-repair-native.json'),
         'normal_repair_before_journal':str(a.folder/'normal-repair-before-native.json'),
         'normal_repair_after_journal':str(a.folder/'normal-repair-after-native.json')}
    value={'stage':'CORN_NORMAL_REPAIR_SOURCE_ONLY_RUNTIME_DENIED','utc':d._utc(),'cfg':cfg,
           'native_source':d.pin(NATIVE),'host_source':d.pin(Path(__file__)),
           'test_source':d.pin(REPO/'tools/unreal/test_codex_skyfarm_corn_recovery.py'),
           'scope':d.pin(a.scope),'diagnosis':d.pin(evidence/'diagnosis-and-proposal.json'),
           'runtime_authorized':False,'runtime_dispatch_entrypoint':None,'native_calls':0,'compute_claims':0,
           'prospective_effects':'ONE target CornLOD0 recompute_normals true->false via copied full settings and ONE setter/implicit asset rebuild; strict full stored/raw/PBR/preservation readback. ZERO saves/imports/placement/map/camera.',
           'blocker':'ROOT automatic approval review rejected downstream runtime authorization; source clearance/publication grants no execution.'}
    d.write_new(a.folder/'prepared.json',value)
    print(json.dumps({'stage':value['stage'],'prepared':d.pin(a.folder/'prepared.json'),'native_calls':0,'runtime_authorized':False}))


REPAIR_VERSION='corn-authored-normal-repair-caller-v2'
REPAIR_OPERATION='corn-authored-normal-repair-only-v1'
REPAIR_NATIVE_SHA='4561dd8d37804e6f331e2de5210fe560ec52b57086c33c590a60cae256af0fce'
REPAIR_SOURCE_SHA='ae64e9cab2c5f9cfc9f0a89c127c56087de1f50f7b53ff3492f297bf0695aa87'
REPAIR_SOURCE=TASK/'native-ingestion/Harvest3CornR1/NormalRepairCallerSourceR2'
REPAIR_ATTEMPTS=TASK/'native-ingestion/Harvest3CornR1/NormalRepairAttempts'
REPAIR_EDITOR='C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe'
REPAIR_EDITOR_START='2026-10-16T05:00:48.3931312Z'


def _repair_utc():return datetime.now(timezone.utc).isoformat()


def prepare_repair_caller(a):
    """File-only source plan. No external tools, reservations or dispatch."""
    if a.folder.resolve()!=REPAIR_SOURCE or (a.folder/'prepared.json').exists():raise RuntimeError('fresh exact caller source packet required')
    scope=d.load(a.scope)
    if not any(m.get('id')==33316 and m.get('type')=='task.assign' and m.get('from')=='pootscoot-coordination'
               and m.get('to')=='codex-play-guard' and m.get('body',{}).get('source_only')is True for m in scope['messages']):raise RuntimeError('addressed source-only33316 assignment required')
    source=TASK/'native-ingestion/Harvest3CornR1/NormalRepairSourceR2/prepared.json'
    if d.fingerprint(source)['sha256']!=REPAIR_SOURCE_SHA or d.fingerprint(NATIVE)['sha256']!=REPAIR_NATIVE_SHA:raise RuntimeError('exact reviewed native/source cut required')
    candidate=d.load(source)
    # Verified unchanged-core lineage only. R2 still needs its own exact source
    # review and finite runtime grant; the consumed R1 publication grants none.
    publication=TASK/'native-ingestion/Harvest3CornR1/NormalRepairSourceR1/publication.json';published=d.load(publication)
    if published.get('commit')!='c20170324aa0605796e49a4f1c8a71b2b8c094a3' or published.get('exact_reviewed_cut')is not True or not all(row.get('remote_bytes_verified')is True for row in published['files']):
        raise RuntimeError('verified exact reviewed source publication required first')
    for row in candidate['cfg']['repair_support'].values():d._check(row)
    value={'version':REPAIR_VERSION,'operation':REPAIR_OPERATION,'target':PATHS[0],'native_function':'repair_normals',
        'runtime_authorized':False,'native_source':d.pin(NATIVE),'source_candidate':d.pin(source),
        'host_source':d.pin(Path(__file__)),'test_source':d.pin(REPO/'tools/unreal/test_codex_skyfarm_corn_recovery.py'),
        'world_guard':d.pin(TASK/'build_gallery_dispatch_spur.py'),'source_scope':d.pin(a.scope),
        'reviewed_source_publication':d.pin(publication),'cfg':candidate['cfg'],
        'runtime_gate':'Distinct actual addressed finite repair-only grant with direct-user authorization reference, exact source/prepared/review pins and unique attempt. No grant exists at source preparation.',
        'maximum_native_callbacks':1,'maximum_targeted_normal_rebuilds':1,
        'maximum_imports':0,'maximum_saves':0,'maximum_new_actors':0,'maximum_map_saves':0,'maximum_camera_actions':0,'maximum_captures':0}
    d.write_new(a.folder/'prepared.json',value)
    print(json.dumps({'stage':'REPAIR_CALLER_SOURCE_ONLY','prepared':d.pin(a.folder/'prepared.json'),'native_calls':0,'compute_claims':0}))


def repair_caller_dry_run(a):
    # Default remains inert even if somebody supplies a grant file as an option.
    result={'stage':'REPAIR_CALLER_DRY_RUN','version':REPAIR_VERSION,'operation':REPAIR_OPERATION,
            'target':PATHS[0],'native_function':'repair_normals','native_calls':0,'external_calls':0,
            'compute_claims':0,'runtime_authorized':False,'effects':'No operation executed. A future approved run is one target rebuild/readback, zero saves/placement/camera.'}
    if getattr(a,'folder',None):result['source_packet_exists']=(a.folder/'prepared.json').exists()
    return result


def _repair_time(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset()!=timezone.utc.utcoffset(parsed):raise ValueError('explicit zero-offset UTC required')
    return parsed.timestamp()


def _repair_pending():
    for folder in REPAIR_ATTEMPTS.glob('corn-normal-repair-*'):
        terminal=folder/'terminal.json';release=folder/'release.json'
        if (folder/'uncertain.json').exists():raise RuntimeError('unreconciled prior repair attempt; no new attempt')
        if not terminal.exists():raise RuntimeError('prior repair attempt has no durable terminal')
        value=d.load(terminal)
        if value.get('known_terminal')is not True:raise RuntimeError('prior repair outcome remains pending')
        if (folder/'claim-intent.json').exists() and not release.exists() and value.get('reservation_acquired')is not False:raise RuntimeError('prior repair reservation requires explicit reconciliation')
        if release.exists() and d.load(release).get('old_lease_absent')is not True:raise RuntimeError('prior repair release unconfirmed')


def _repair_local_plan(a):
    if a.folder.resolve()!=REPAIR_SOURCE:raise ValueError('exact reviewed caller source path required')
    prepared=d.load(a.folder/'prepared.json')
    if (prepared.get('version')!=REPAIR_VERSION or prepared.get('operation')!=REPAIR_OPERATION
            or prepared.get('target')!=PATHS[0] or prepared.get('native_function')!='repair_normals'
            or prepared['native_source']['sha256']!=REPAIR_NATIVE_SHA or prepared['source_candidate']['sha256']!=REPAIR_SOURCE_SHA):
        raise ValueError('exact reviewed caller/native/target/function required')
    if Path(prepared['native_source']['path']).resolve()!=NATIVE.resolve() or Path(prepared['host_source']['path']).resolve()!=Path(__file__).resolve():raise ValueError('reviewed source file identity differs')
    rows=[prepared[k] for k in ('native_source','host_source','test_source','source_candidate','world_guard','source_scope','reviewed_source_publication')]
    cfg=prepared['cfg'];rows += [cfg[k] for k in ('source','manifest','packet','baseline','snap','world_helper','original_import')]
    rows += list(cfg['helpers'].values())+list(cfg['repair_support'].values())
    for row in rows:d._check(row)
    if not re.fullmatch(r'corn-normal-repair-\d{8}T\d{6}Z-[a-f0-9]{8}',a.repair_attempt or ''):raise ValueError('fresh closed repair attempt name required')
    attempt=REPAIR_ATTEMPTS/a.repair_attempt
    if attempt.exists():raise RuntimeError('retained attempt directory; no replay')
    _repair_pending()
    grant_pin=d.pin(a.prerequisite);review_pin=d.pin(a.review);review=d.load(a.review)
    prepared_pin=d.pin(a.folder/'prepared.json')
    if review.get('clear')is not True or review.get('prepared_sha256')!=prepared_pin['sha256']:raise ValueError('exact caller source review required')
    messages=d.load(a.prerequisite)['messages']
    grants=[m for m in messages if m.get('id',0)>33232 and m.get('from')=='pootscoot-coordination'
        and m.get('to')=='codex-play-guard' and m.get('type')=='grant'
        and m.get('body',{}).get('assignment_id')=='skyfarm-corn-authored-normal-repair-r1']
    if len(grants)!=1:raise ValueError('distinct actual addressed repair-only grant required')
    body=grants[0]['body']
    exact={'caller_version':REPAIR_VERSION,'operation':REPAIR_OPERATION,'target':PATHS[0],
        'native_function':'repair_normals','prepared_sha256':prepared_pin['sha256'],
        'native_source_sha256':REPAIR_NATIVE_SHA,'host_source_sha256':prepared['host_source']['sha256'],
        'source_review_sha256':review_pin['sha256'],'attempt_id':a.repair_attempt,'attempt_directory':str(attempt),
        'maximum_native_callbacks':1,'maximum_targeted_normal_rebuilds':1,
        'maximum_imports':0,'maximum_saves':0,'maximum_new_actors':0,'maximum_map_saves':0,'maximum_camera_actions':0,'maximum_captures':0}
    if any(body.get(k)!=v for k,v in exact.items()):raise ValueError('grant target/source/review/attempt/effect binding differs')
    if body.get('direct_user_authorization_received')is not True or not isinstance(body.get('direct_user_authorization_reference'),str) or not body['direct_user_authorization_reference'].strip():
        raise ValueError('direct user runtime authorization still pending; source publication is insufficient')
    if body.get('resource_prerequisite_confirmed')is not True or not isinstance(body.get('resource_prerequisite_reference'),str) or not body['resource_prerequisite_reference'].strip():
        raise ValueError('actual prior terminal/release or no-launch closure required; absent compute alone is insufficient')
    start=_repair_time(body['start_by_utc']);stop=_repair_time(body['stop_by_utc']);now=time.time()
    if now>=start or stop<=start or stop-now<330:raise ValueError('finite current UTC window with240sRPC+90s reserve required')
    return {'prepared':prepared,'prepared_pin':prepared_pin,'grant_pin':grant_pin,'review_pin':review_pin,
            'attempt':attempt,'start_by':start,'stop_by':stop,'operation':REPAIR_OPERATION,'source_rows':rows}


def _repair_code(plan,cfg):
    p=plan['prepared'];row=p['native_source']
    body='from pathlib import Path\nimport hashlib\npin='+repr(row)+'\nraw=Path(pin["path"]).read_bytes()\nif len(raw)!=pin["bytes"] or hashlib.sha256(raw).hexdigest()!=pin["sha256"]:raise RuntimeError("reviewed repair source changed")\nscope={"__name__":"_corn_repair_only","__file__":pin["path"]}\nexec(compile(raw,pin["path"],"exec"),scope)\nresult=scope["repair_normals"]('+repr(cfg)+')\n'
    tree=ast.parse(Path(p['world_guard']['path']).read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='native')
    value=next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
    return eval(compile(ast.Expression(value),'<existing-guarded-repair-only-route>','eval'),dict(MARKER=MARKER,body=body,dirty=False,owned=list(HELD)+[p.split('.')[0] for p in PATHS]))


def _repair_resources(folder,label):
    class MemoryStatus(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ('total_physical','available_physical','total_commit_limit','available_commit','total_virtual','available_virtual','reserved')]
    sample=MemoryStatus();sample.length=ctypes.sizeof(sample)
    ok=bool(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(sample)))
    d.write_new(folder/(label+'.json'),{'utc':_repair_utc(),'api_success':ok,'observed':{k:int(getattr(sample,k)) for k,t in sample._fields_},'physical_floor_bytes':1700000*1024,'commit_floor_bytes':2200000*1024})
    if not ok:raise RuntimeError('fresh numeric memory observation unavailable')
    return receiving.resources()  # Original floors remain unchanged.


def _repair_runtime_tools():
    def code_write(path,code):
        with path.open('x',encoding='utf-8') as stream:stream.write(code)
    return SimpleNamespace(write=d.write_new,code_write=code_write,now=time.time,locks=d.locks,lease=d._lease,
        protect=lambda p:d.protect(d.load(p['prepared']['cfg']['baseline']['path'])),resources=_repair_resources,
        process=lambda:json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',"Get-Process -Id 42564 -ErrorAction Stop | Select-Object Id,Path,@{n='start_utc';e={$_.StartTime.ToUniversalTime().ToString('o')}} | ConvertTo-Json -Compress"],text=True)),
        claim=lambda:d.post('/lock',{'me':d.OWNER,'name':'compute','ttl':600,'note':'Explicitly granted Corn repair-only:ONEtargetassetrebuild+proof;ZEROsave/import/placement/map/camera. No retry.'}),
        same=d.same_compute_lease,release=lambda:d.post('/unlock',{'me':d.OWNER,'name':'compute'}),
        call=lambda code:d.wire.call(d.wire.UNREAL,'execute_python',code=code,side='Unreal',unattended=False,timeout=240),
        unwrap=lambda reply:d.wire.obj(reply,side='Unreal',what='Corn explicit repair-only'))


def _repair_native_terminal(result):
    if (not isinstance(result,dict) or result.get('known_terminal')is not True or result.get('target')!=PATHS[0]
            or result.get('lod')!=0 or any(result.get(k)!=0 for k in ('imports','saves','new_actors','map_saves','camera_actions'))):
        raise RuntimeError('native qualification/outcome not confirmed by transport success')
    if result.get('stage')=='CORN_NORMAL_REPAIR_QUALIFIED_UNSAVED':
        if (result.get('setter_intents')!=1 or result.get('setter_returns')!=1 or result.get('rebuild_barrier_returned')is not True
                or not isinstance(result.get('build_after'),dict) or result.get('build_after')!=result.get('build_expected')
                or result['build_after'].get('native',{}).get('bRecomputeNormals')is not False
                or any(result.get('after_proof',{}).get(k)is not True for k in ('stored_authored_clear','raw_authored_clear','original_pbr_clear','preservation_clear'))):
            raise RuntimeError('complete target rebuild and strict proof required')
        return 'TARGET_REBUILD_QUALIFIED_UNSAVED'
    if result.get('stage')=='CORN_NORMAL_REPAIR_PARTIAL_HOLD':
        if result.get('setter_intents')==0 and result.get('setter_returns')==0 and result.get('rebuild_barrier_returned')is False:return 'KNOWN_HOLD_NO_REBUILD'
        if result.get('setter_intents')==1 and result.get('setter_returns')==1 and result.get('rebuild_barrier_returned')is True:return 'TARGET_REBUILD_COMPLETED_QUALIFICATION_HOLD'
    raise RuntimeError('inconsistent native terminal; hold without replay')


def _repair_release(folder,claim,io):
    if claim.get('holder')!='codex-play-guard' or not io.same(io.locks().get('compute',{}),claim):raise RuntimeError('exact own reservation changed; no unlock')
    io.write(folder/'release-intent.json',{'utc':_repair_utc(),'claim':claim})
    reply=io.release();after=io.locks()
    if reply.get('ok')is not True or reply.get('lock')is not None or io.same(after.get('compute',{}),claim):raise RuntimeError('normal own release/readback unconfirmed')
    value={'utc':_repair_utc(),'reply':reply,'locks_after':after,'old_lease_absent':True}
    try:io.write(folder/'release.json',value)
    except Exception as exc:exc.release_observation=value;raise
    return value


def _repair_execute(plan,io):
    folder=plan['attempt'];folder.mkdir(parents=True,exist_ok=False)
    state={'stage':'LOCAL_VALIDATED','known_terminal':False,'native_status':'NOT_DISPATCHED','dispatch_started':False,'claim_requested':False,'claim':None,'release':None}
    raw_observation=None
    try:
        io.write(folder/'preflight.json',{'utc':_repair_utc(),'version':REPAIR_VERSION,'operation':REPAIR_OPERATION,
            'prepared':plan['prepared_pin'],'grant':plan['grant_pin'],'review':plan['review_pin'],'target':PATHS[0],'native_function':'repair_normals','replay_permitted':False})
        io.protect(plan);locks=io.locks();io.write(folder/'custody-observed.json',{'utc':_repair_utc(),'locks':locks});lease=io.lease()
        if lease.get('holder')!='codex-play-guard' or locks.get('compute'):raise RuntimeError('sole own native custody/free compute required')
        memory=io.resources(folder,'memory-before-admission');process=io.process();io.write(folder/'editor-observed.json',{'utc':_repair_utc(),'editor':process,'memory':memory})
        if process.get('Id')!=42564 or process.get('Path')!=REPAIR_EDITOR or process.get('start_utc')!=REPAIR_EDITOR_START:raise RuntimeError('exact original editor context required')
        if memory.get('available_physical',0)<1700000*1024 or memory.get('available_commit',0)<2200000*1024:raise RuntimeError('original numeric memory floors not met')
        if io.now()>=plan['start_by']:raise RuntimeError('fresh finite start deadline passed')
        io.write(folder/'claim-intent.json',{'utc':_repair_utc(),'ttl_seconds':600});state['claim_requested']=True
        reply=io.claim()
        if reply.get('ok')is not True:state['claim_requested']=False;raise RuntimeError('exclusive reservation rejected; no dispatch')
        claim=reply['lock']
        if claim.get('holder')!='codex-play-guard' or claim.get('ttl')!=600:raise RuntimeError('exact own600second reservation not established')
        state['claim']=claim
        if not io.same(io.locks().get('compute',{}),claim):raise RuntimeError('claim identity unconfirmed')
        deadline=min(plan['stop_by'],claim['at']+claim['ttl'],lease['at']+lease['ttl'])
        io.write(folder/'claim.json',{'utc':_repair_utc(),'claim':claim,'deadline_epoch':deadline})
        memory=io.resources(folder,'memory-before-dispatch');io.lease();process=io.process()
        io.write(folder/'context-before-dispatch.json',{'utc':_repair_utc(),'memory':memory,'editor':process})
        if memory.get('available_physical',0)<1700000*1024 or memory.get('available_commit',0)<2200000*1024:raise RuntimeError('original numeric floors failed before dispatch')
        if process.get('Id')!=42564 or process.get('Path')!=REPAIR_EDITOR or process.get('start_utc')!=REPAIR_EDITOR_START:raise RuntimeError('fresh editor context changed before dispatch')
        if io.now()>=plan['start_by'] or deadline-io.now()<330:raise RuntimeError('240second RPC/90second reserve unavailable')
        if not io.same(io.locks().get('compute',{}),claim):raise RuntimeError('reservation changed before dispatch')
        for row in plan['source_rows']:d._check(row)
        cfg={**plan['prepared']['cfg'],'source_only':False,'repair_runtime_grant':plan['grant_pin'],'deadline_epoch':deadline,
             'normal_repair_journal':str(folder/'native.json'),'normal_repair_before_journal':str(folder/'before-native.json'),
             'normal_repair_after_journal':str(folder/'after-native.json'),'witness_directory':str(folder/'graph-witnesses')}
        (folder/'graph-witnesses').mkdir();code=_repair_code(plan,cfg)
        io.write(folder/'dispatch-intent.json',{'utc':_repair_utc(),'native_function':'repair_normals','target':PATHS[0],
            'native_source':plan['prepared']['native_source'],'code_sha256':hashlib.sha256(code.encode()).hexdigest(),'maximum_callbacks':1,'replay_permitted':False})
        io.code_write(folder/'repair-executed.py',code)
        state['dispatch_started']=True;state['native_status']='DISPATCH_OUTCOME_UNCONFIRMED'
        raw=io.call(code);raw_observation=raw;io.write(folder/'reply.json',raw);result=io.unwrap(raw);io.write(folder/'result.json',result)
        stage=_repair_native_terminal(result)
        state['native_status']=stage
        terminal={'utc':_repair_utc(),'stage':stage,'known_terminal':True,'native_result':d.pin(folder/'result.json'),
                  'target':PATHS[0],'saves':0,'placement':0,'camera':0}
        io.write(folder/'terminal.json',terminal);state.update(stage=stage,known_terminal=True)
        state['release']=_repair_release(folder,claim,io);return state
    except Exception as exc:
        state.update(error=str(exc),error_type=type(exc).__name__)
        if hasattr(exc,'release_observation'):state['release_observation']=exc.release_observation
        if not state['dispatch_started'] and (state['claim'] is not None or not state['claim_requested']):
            terminal={'utc':_repair_utc(),'stage':'NO_DISPATCH_REJECTED','known_terminal':True,'error':str(exc),'native_callbacks':0,'reservation_acquired':state['claim']is not None}
            try:
                io.write(folder/'terminal.json',terminal)
                if state['claim'] is not None:state['release']=_repair_release(folder,state['claim'],io)
                state.update(stage='NO_DISPATCH_REJECTED',known_terminal=True);return state
            except Exception as close_error:
                state['closure_error']=str(close_error)
                if hasattr(close_error,'release_observation'):state['release_observation']=close_error.release_observation
                if state['claim']is None and not state['claim_requested']:
                    state.update(stage='NO_DISPATCH_RECEIPT_FAILURE',known_terminal=True);return state
        state['stage']='UNCERTAIN_DISPATCH_OR_CLOSURE' if state['dispatch_started'] else 'UNCONFIRMED_PRELAUNCH_RESERVATION'
        try:io.write(folder/'uncertain.json',{'utc':_repair_utc(),**state,'raw_reply_observation':raw_observation,'replay_permitted':False,'forced_unlock_permitted':False})
        except Exception as receipt_error:state['receipt_error']=str(receipt_error)
        return state


def run_normal_repair(a,*,_io=None):
    if getattr(a,'execute_approved_repair',False)is not True:return repair_caller_dry_run(a)
    try:plan=_repair_local_plan(a)  # ALL grant/path/pin checks precede any external IO.
    except Exception as exc:return {'stage':'NO_DISPATCH_REJECTED','known_terminal':True,'native_callbacks':0,'external_calls':0,'error':str(exc),'runtime_authorized':False}
    return _repair_execute(plan,_io or _repair_runtime_tools())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',nargs='?',default='repair-dry-run',choices=['prepare','run','prepare-normal-repair','prepare-repair-caller','repair-dry-run','run-normal-repair'])
    parser.add_argument('--folder',type=Path);parser.add_argument('--scope',type=Path)
    parser.add_argument('--prerequisite',type=Path);parser.add_argument('--review',type=Path)
    parser.add_argument('--repair-attempt');parser.add_argument('--execute-approved-repair',action='store_true')
    args=parser.parse_args()
    if args.phase not in ('repair-dry-run','run-normal-repair') and args.folder is None:parser.error('--folder is required for that phase')
    if args.phase=='repair-dry-run':print(json.dumps(repair_caller_dry_run(args)))
    elif args.phase=='prepare-repair-caller':prepare_repair_caller(args)
    elif args.phase=='run-normal-repair':print(json.dumps(run_normal_repair(args)))
    elif args.phase=='prepare-normal-repair':prepare_normal_repair(args)
    elif args.phase=='prepare':prepare(args)
    else:run(args)
