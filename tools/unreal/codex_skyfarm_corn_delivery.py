# SPDX-License-Identifier: MIT
"""Corn existing-alias recovery; prepare is file-only, run needs a NEW grant.

Reuse the existing transport, dispatch retention, opaque GLB pipeline, graph/
geometry inspectors and preservation helpers. No automatic replay or cleanup.
"""
import argparse
import ast
import base64
import copy
from datetime import datetime,timezone
import hashlib
import json
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


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['prepare','run','prepare-normal-repair'])
    parser.add_argument('--folder',type=Path,required=True);parser.add_argument('--scope',type=Path)
    parser.add_argument('--prerequisite',type=Path);parser.add_argument('--review',type=Path)
    args=parser.parse_args()
    if args.phase=='prepare-normal-repair':prepare_normal_repair(args)
    elif args.phase=='prepare':prepare(args)
    else:run(args)
