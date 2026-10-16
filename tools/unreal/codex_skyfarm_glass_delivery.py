# SPDX-License-Identifier: MIT
"""Glass source qualification and the bounded32998 read-only witness route.

Prepare/check are file-only. Witness requires the pinned grant, its original
start-by time, an exclusive compute claim and the existing native guards.
It never authorizes saves or placement, including after qualification.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import ast
from datetime import datetime
import time
from types import SimpleNamespace

from codex_tidepen_queue_manifest import glb

REPO=Path(__file__).resolve().parents[2]
POLICY=REPO/'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_skyfarm_glass.py'
spec=importlib.util.spec_from_file_location('_skyfarm_glass_source_policy',POLICY)
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
GLB_SHA='1e208959d249b8b781027ad2bae69dbb70bb4472db01e9bf12da707d93ad7d0a'
MANIFEST_SHA='7082cd07018dfa21254023ab5e715645e11e099a455a13cd81d59e2ad4f62a96'
BASE_SHA='7d7a33679e79b909b7f382a42144bbceccff475281e3cdbd2248e0b829e4614e'
EVIDENCE_SHA='ff24aa5a9f030b7ab0d4f372c706f402c2a82a9fc8dd2d57f3e9542655a164d8'


def pin(path):
    p=Path(path).resolve();raw=p.read_bytes()
    return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def prepare(args):
    source=pin(args.glb);manifest=pin(args.manifest);baseline=pin(args.baseline)
    if (source['sha256']!=GLB_SHA or source['bytes']!=88052
            or manifest['sha256']!=MANIFEST_SHA or manifest['bytes']!=5639
            or baseline['sha256']!=BASE_SHA):raise ValueError('exact original payload/accepted baseline pins required')
    decoded=glb(Path(args.glb));nodes=[r for r in decoded['nodes'] if r['name']=='SFG_R1_glass_glass']
    if len(nodes)!=1 or nodes[0]['authored_transform_fields'] or len(nodes[0]['primitives'])!=1:
        raise ValueError('exact identity shared-origin glass role required')
    node=nodes[0];primitive=node['primitives'][0]
    if (primitive['triangles_decoded_from_index_count']!=48 or primitive['position_count_decoded']!=96
            or set(primitive['attributes'])!={'POSITION','NORMAL'} or primitive['material_index']!=1
            or decoded['images'] or decoded['textures']):raise ValueError('exact48tri/96vertices/factor-only role required')
    contract=policy.source_contract(decoded['materials'][primitive['material_index']])
    for edge in ('min','max'):
        actual=[primitive['position_bounds_decoded_node_world'][edge][axis]*100 for axis in (0,2,1)]
        if not policy._numbers(actual,contract['native_bounds_cm'][edge],1e-6):raise ValueError('source absolute XZY100 bounds differ')
    evidence_pin=pin(args.evidence);evidence=load(args.evidence)
    if (evidence_pin['bytes']!=10224 or evidence_pin['sha256']!=EVIDENCE_SHA
            or len(evidence.get('installed_file_pins',[]))!=10
            or evidence.get('stage')!='SOURCE_MAPPING_AVAILABLE_NATIVE_HELD'
            or evidence.get('native_calls')!=0 or evidence.get('compute_claims')!=0):
        raise ValueError('source-only installed API evidence required')
    for expected in evidence['installed_file_pins']:
        actual=pin(expected['path'])
        if any(actual[k]!=expected[k] for k in ('bytes','sha256')):raise ValueError('installed source/API body package changed')
    b=load(args.baseline)
    if len(b['packages'])!=231 or len(b['scene']['actors'])!=152 or len(b['candidate_source'])!=184:
        raise ValueError('exact accepted saved baseline counts required')
    for path in (policy.MATERIAL,policy.MESH):
        package=path.split('.')[0]
        if (Path('C:/Unreal/DaedalusRealm/Content')/(package.removeprefix('/Game/')+'.uasset')).exists():
            raise ValueError('held glass unexpectedly saved; source stage does not adopt changed state')
    result={'stage':'SOURCE_TRANSMISSION_MAPPING_QUALIFIED_NATIVE_PENDING','assignment':'32971',
        'source':source,'manifest':manifest,'baseline':baseline,'policy':pin(POLICY),
        'source_evidence':evidence_pin,'installed_file_pins':evidence['installed_file_pins'],
        'contract':contract,'decoded_glass':node,'native_ready':False,'runtime_authorized':False,
        'native_calls':0,'native_graph_observed':False,'tests_are_native_proof':False,
        'next_execution_scope':['After corn actual terminal+explicit release/readback, obtain separate bounded READONLY native scope.',
            'Existing owned bridge/queue/resources/231package152actor184source/map guards; exact2helddirty allowlist.',
            'Read ONLY existing glass48tri/material graph, five independent factors and actual MF_Transmission_Body defaults/output names.',
            'Public MEL traversal plus separate30root and ThinTranslucent custom-output CDO/T3D witnesses; no protected reflection.',
            'Compare complete observations through check_observation; unsupported graph/API or scalar/tuple shape holds glass.',
            'Only a later explicit mutation scope may first-save2/place1/save-map-once/capture/restore; never reimport/replace/SaveAll.'],
        'visual_contract':['Matched native front/back/oblique views show tinted transmitted scene and independent alpha coverage.',
            'Confirm no opaque substitute, alpha-only fallback, custom-output absence or whole-aisle collision.',
            'Retain real images and original scene/camera witnesses; graph proof alone is not visual acceptance.']}
    write(args.output,result);print(json.dumps({'stage':result['stage'],'output':pin(args.output),'native_calls':0}))


def witness(args):
    """One32998 guarded readonly dispatch; unknown outcomes keep custody."""
    import codex_skyfarm_greenhouse_delivery as receiving
    import codex_static_intake_delivery as original
    d=receiving.d
    folder=args.folder.resolve()
    if folder.exists():raise RuntimeError('GlassGraphR1 must be absent before initial attempt; no replay')
    if args.compatibility_of:
        previous=args.compatibility_of.resolve()
        if folder!=previous/'CompatibilityR2':raise ValueError('only the one declared CompatibilityR2 child may follow initial witness')
        old=load(previous/'native-terminal.json');released=load(previous/'compute-release.json')
        if (old.get('stage')!='KNOWN_TERMINAL_READONLY_SHAPE_REFUSAL'
                or old.get('error')!='actual unique function default missing: EmissiveFactor'
                or old.get('before')!=old.get('after') or old.get('native_mutations')!=0
                or released.get('reply',{}).get('ok') is not True or released.get('reply',{}).get('lock') is not None):
            raise ValueError('exact known terminal, preserved and explicitly released initial schema refusal required')
    qualification=load(args.qualification)
    if qualification.get('stage')!='SOURCE_TRANSMISSION_MAPPING_QUALIFIED_NATIVE_PENDING':raise ValueError('reviewed32971 qualification required')
    for key in ('source','manifest','baseline','policy','source_evidence'):d._check(qualification[key])
    if qualification['policy']['sha256']!='76a6937750ea8592abf150fb8acc62394d5906ea306802856d5c889090dcf2a9':raise ValueError('frozen pure qualifier required')
    for row in qualification['installed_file_pins']:d._check(row)
    messages=json.loads(args.grant.read_text(encoding='utf-8-sig'))['messages']
    grants=[m for m in messages if m.get('id')==32998 and m.get('from')=='pootscoot-coordination']
    releases=[m for m in messages if m.get('id')==33000 and m.get('from')=='pootscoot-coordination']
    if len(grants)!=1 or len(releases)!=1:raise ValueError('exact32998 grant and33000 release prerequisite required')
    start_by=datetime.fromisoformat(grants[0]['body']['start_by_utc'].replace('Z','+00:00')).timestamp()
    if time.time()>start_by:raise RuntimeError('grant start-by passed; no launch')
    baseline=load(qualification['baseline']['path']);d.protect(baseline);lease=d._lease();resources=receiving.resources()
    if d.locks().get('compute'):raise RuntimeError('competing compute; no launch')
    marker='# Codex SkyFarm GlassGraphR1 readonly32998'
    task=REPO.parent;world_guard=task/'build_gallery_dispatch_spur.py'
    prior=load(task/'native-ingestion/SkyFarmGreenhouseBayR1/DeliveryR1/prepared.json')
    d._check(prior['world_guard'])
    if str(world_guard.resolve())!=str(Path(prior['world_guard']['path']).resolve()):raise ValueError('original guarded route differs')
    folder.mkdir(parents=True);snap=folder/'snap.py'
    with snap.open('x',encoding='utf-8') as stream:stream.write(original._snap_definition())
    graph=POLICY.with_name('daedalus_codex_canal_material.py')
    collector=POLICY.with_name('daedalus_codex_skyfarm_glass_witness.py')
    function_body=next(row for row in qualification['installed_file_pins'] if row['path'].endswith('MF_Transmission_Body.uasset'))
    cfg={'folder':str(folder),'marker':marker,'policy':qualification['policy'],'graph_helper':pin(graph),
        'world_helper':pin(REPO/'tools/unreal/codex_canal_water_placement_native.py'),'snap_source':pin(snap),
        'baseline':qualification['baseline'],'function_body':function_body}
    if cfg['graph_helper']['sha256']!='75c6d1eecef4d2c42d47db0b3a52033024f8bc7ac67efa58aeff83ad00f62000':raise RuntimeError('frozen graph helper differs')
    source_pins=[pin(collector),pin(Path(__file__)),prior['world_guard'],cfg['graph_helper'],cfg['world_helper'],cfg['snap_source'],*qualification['installed_file_pins'],*[qualification[k] for k in ('source','manifest','baseline','policy')]]
    write(folder/'prepared.json',{'utc':d._utc(),'grant':pin(args.grant),'qualification':pin(args.qualification),
        'source_pins':source_pins,'resources':resources,'cfg':cfg,'native_calls':0})
    claim=d.post('/lock',{'me':d.OWNER,'name':'compute','ttl':300,'note':'32998 one READONLY held greenhouse glass graph witness; evidencefiles only, no saves/placement/setters/selection/camera/render/build/import. Release for queuedHearthjaw after actual terminal.'})
    if claim.get('ok') is not True or not d.same_compute_lease(d.locks().get('compute',{}),claim.get('lock',{})):raise RuntimeError('exact300s claim unconfirmed')
    cfg['deadline_epoch']=min(claim['lock']['at']+claim['lock']['ttl'],lease['at']+lease['ttl'])
    write(folder/'claim.json',{'utc':d._utc(),'compute_claim':claim,'cfg':cfg})
    if time.time()>start_by or time.time()>cfg['deadline_epoch']-90:raise RuntimeError('start/deadline changed before dispatch; preserve reservation for explicit closure')
    d._lease();receiving.resources()
    if not d.same_compute_lease(d.locks().get('compute',{}),claim['lock']):raise RuntimeError('claim identity changed')
    for row in source_pins:d._check(row)
    raw=source_pins[0]
    body=('from pathlib import Path\nimport hashlib\npin='+repr(raw)+'\nraw=Path(pin["path"]).read_bytes()\n'
        'if hashlib.sha256(raw).hexdigest()!=pin["sha256"]:raise RuntimeError("collector changed")\n'
        'collector={"__name__":"_codex_glass_readonly","__file__":pin["path"]}\nexec(compile(raw,pin["path"],"exec"),collector)\n'
        'result=collector["collect"]('+repr(cfg)+')\n')
    tree=ast.parse(world_guard.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='native')
    expression=next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
    code=eval(compile(ast.Expression(expression),'<existing-guarded-route>','eval'),dict(MARKER=marker,body=body,dirty=False,
        owned=[p.split('.')[0] for p in (policy.MATERIAL,policy.MESH)]))
    a=SimpleNamespace(folder=folder)
    result=receiving.retained_call(a,'collector','execute_python',code,unattended=False,timeout=160)
    if (result.get('stage') not in ('QUALIFIED_READONLY_ADMISSION_PENDING','HOLD_ACTUAL_GRAPH_CONTRACT_DIFFERS','KNOWN_TERMINAL_READONLY_SHAPE_REFUSAL')
            or result.get('native_mutations')!=0 or result.get('before')!=result.get('after')):
        raise RuntimeError('unknown/nonpreserved result; retain custody, no replay')
    for row in source_pins:d._check(row)
    d.protect(baseline)
    write(folder/'terminal.json',{'utc':d._utc(),'stage':result['stage'],'native':pin(folder/'native-terminal.json'),
        'raw_reply':pin(folder/'collector-reply.json'),'source_pins':source_pins,'baseline':qualification['baseline'],
        'known_terminal':True,'native_mutations':0,'compute_claim':claim})
    if not d.same_compute_lease(d.locks().get('compute',{}),claim['lock']):raise RuntimeError('different lease; no release')
    unlock=d.post('/unlock',{'me':d.OWNER,'name':'compute'});after=d.locks()
    if unlock.get('ok') is not True or after.get('compute'):raise RuntimeError('explicit release not confirmed')
    write(folder/'compute-release.json',{'utc':d._utc(),'reply':unlock,'locks_after':after,'terminal':pin(folder/'terminal.json')})
    print(json.dumps({'stage':result['stage'],'error':result.get('error'),'contract_error':result.get('contract_error'),
        'native_elapsed_seconds':result.get('elapsed_seconds'),'receipt':pin(folder/'terminal.json'),'release':load(folder/'compute-release.json')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','check','witness']);parser.add_argument('--output',type=Path)
    for name in ('glb','manifest','baseline','evidence','observation'):parser.add_argument('--'+name,type=Path)
    for name in ('folder','qualification','grant'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--compatibility-of',type=Path)
    args=parser.parse_args()
    if args.phase=='witness':witness(args)
    elif args.phase=='prepare':prepare(args)
    else:
        observed=load(args.observation)
        for witness in observed.get('graph',{}).get('proofs',{}).values():
            if not isinstance(witness,dict):raise ValueError('actual retained witness files required')
            # Existing root exporters use "file"; package/custom pins use
            # "path". Preserve both raw proof forms, rejecting disagreement.
            paths=[witness[key] for key in ('path','file') if key in witness]
            if not paths or any(not isinstance(p,str) or p!=paths[0] for p in paths):
                raise ValueError('one unambiguous retained witness file required')
            actual=pin(paths[0])
            if any(actual[k]!=witness[k] for k in ('bytes','sha256')):raise ValueError('retained native witness changed')
        result=policy.check_observation(observed);write(args.output,result);print(json.dumps(result))
