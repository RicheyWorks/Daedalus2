# SPDX-License-Identifier: MIT
"""File-only32971 glass source qualification; deliberately no native dispatcher."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

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


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','check']);parser.add_argument('--output',type=Path,required=True)
    for name in ('glb','manifest','baseline','evidence','observation'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.phase=='prepare':prepare(args)
    else:
        observed=load(args.observation)
        for witness in observed.get('graph',{}).get('proofs',{}).values():
            if not isinstance(witness,dict) or 'path' not in witness:raise ValueError('actual retained witness files required')
            actual=pin(witness['path'])
            if any(actual[k]!=witness[k] for k in ('bytes','sha256')):raise ValueError('retained native witness changed')
        result=policy.check_observation(observed);write(args.output,result);print(json.dumps(result))
