# SPDX-License-Identifier: MIT
"""Closed32923 first greenhouse bay delivery; retained phases never replay.

File-only preparation precedes a bounded sole-operator native turn. Seven opaque
groups may be saved/placed; unsupported transmission glass stays unsaved. Raw
bridge envelopes, native journals and source pins distinguish partial outcomes.
"""
import argparse
import ast
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace

import codex_qualified_static_delivery as d
import codex_static_intake_delivery as original
from codex_tidepen_queue_manifest import glb

REPO=Path(__file__).resolve().parents[2]
NATIVE=REPO/'engines/unreal/DaedalusLink/Content/Python/daedalus_codex_skyfarm_greenhouse.py'
ROOT='/Game/Daedalus/Art/SkyFarm/GreenhouseBayR1'
LABEL='Codex SkyFarm GreenhouseBayR1 partial opaque intake32923'
MARKER='# Codex SkyFarm GreenhouseBayR1 closed32923 world phase'
SOURCE=Path('C:/Users/730ri/Documents/Codex/2026-10-13/task-3/sky-farm-greenhouse-delivery-r1')
SUPPORT='/Game/Daedalus/DaedalusWorld.DaedalusWorld:PersistentLevel.DaedalusLandDistrict_215'
_prior_asset_file=d._asset_file


def asset_file(path):
    """Own fixed receiving namespace; retain historical path policy elsewhere."""
    if path.startswith(ROOT+'/'):
        relative=path[len(ROOT)+1:]
        name=relative.split('.')[0]
        allowed={'SFG_R1_'+part for part in ('frame','glass','copper','soil','leaf','leaf_light','path',
            'frame_frame','glass_glass','frame_copper','bed_copper','bed_soil','crop_leaf','crop_leaf_light','path_path')}
        if name not in allowed or relative not in (name,name+'.'+name):raise ValueError('exact closed greenhouse asset path required')
        return Path('C:/Unreal/DaedalusRealm/Content/Daedalus/Art/SkyFarm/GreenhouseBayR1')/(name+'.uasset')
    return _prior_asset_file(path)


# This host's file-only baseline expansion includes only the closed new root;
# unchanged shared-source modules and every old package still use the old mapper.
d._asset_file=asset_file


def resources():
    return d._resources(SimpleNamespace(minimum_free_physical_mib=1700000/1024,
                                        minimum_free_commit_mib=2200000/1024))


def exclusive_copy(source,target):
    with Path(source).open('rb') as src,Path(target).open('xb') as out:
        shutil.copyfileobj(src,out,1024*1024);out.flush();os.fsync(out.fileno())
    if d.fingerprint(source)!=d.fingerprint(target):raise RuntimeError('exclusive backup differs')


def prepare(a):
    if a.folder.exists():raise RuntimeError('retained delivery; no replacement')
    base=d.load(a.baseline);d.protect(base)
    source=SOURCE/'Bld_SkyFarm_GreenhouseBay_R1.glb';manifest=SOURCE/'manifest.json'
    if d.fingerprint(source)!=dict(bytes=88052,sha256='1e208959d249b8b781027ad2bae69dbb70bb4472db01e9bf12da707d93ad7d0a'):
        raise RuntimeError('exact original GLB differs')
    if d.fingerprint(manifest)!=dict(bytes=5639,sha256='7082cd07018dfa21254023ab5e715645e11e099a455a13cd81d59e2ad4f62a96'):
        raise RuntimeError('exact original manifest differs')
    data=glb(source);nodes=[]
    for row in data['nodes']:
        if row['classification']!='render' or len(row['primitives'])!=1 or row['authored_transform_fields']:
            raise RuntimeError('closed original one-slot identity-root profile differs')
        p=row['primitives'][0]
        nodes.append(dict(name=row['name'],triangles=p['triangles_decoded_from_index_count'],
            local_bounds=p['position_bounds_decoded_local'],world_bounds=p['position_bounds_decoded_node_world'],
            transform=row['authored_transform_fields'],material=copy.deepcopy(data['materials'][p['material_index']])))
    if len(nodes)!=8 or sum(r['triangles'] for r in nodes)!=1452 or len(data['materials'])!=7:
        raise RuntimeError('exact8/7/1452 source required')
    a.folder.mkdir(parents=True)
    d.write_new(a.folder/'source-packet.json',{'nodes':nodes,'source':d.pin(source),'manifest':d.pin(manifest),
        'semantics':'raw glTF materials; omitted TRS identity; baked native XZY*100; shared actor origin',
        'sockets_metadata_only':{'Entry':[0,500,0],'Repeat':[0,-500,0]}})
    snap=a.folder/'snap.py';snap.write_text(original._snap_definition(),encoding='utf-8')
    native_dir=NATIVE.parent
    helpers={k:str(native_dir/v) for k,v in {
        'sunspool':'daedalus_codex_sunspool_subset.py','geometry':'daedalus_codex_copperfall_subset.py',
        'miri':'daedalus_codex_miri.py','catalogue':'daedalus_codex_catalogue.py',
        'queue':'daedalus_codex_qualified_static.py'}.items()}
    world_helper=REPO/'tools/unreal/codex_canal_water_placement_native.py'
    cfg=dict(destination=ROOT,glb=str(source),manifest=str(manifest),source_packet=str(a.folder/'source-packet.json'),
        source_packet_sha256=d.fingerprint(a.folder/'source-packet.json')['sha256'],
        journal=str(a.folder/'asset-native.json'),content_dir='C:/Unreal/DaedalusRealm/Content',
        baseline=str(a.baseline),world_before=str(a.folder/'world-before.json'),
        world_journal=str(a.folder/'world-native.json'),world_save_journal=str(a.folder/'map-save-native.json'),
        camera_journal=str(a.folder/'camera-native.json'),world_helper=str(world_helper),
        world_helper_sha256=d.fingerprint(world_helper)['sha256'],snap_source=str(snap),
        snap_source_sha256=d.fingerprint(snap)['sha256'],support_actor_path=SUPPORT,
        support_component_path=SUPPORT+'.Ground',support_instance=0,
        map_file=str(d.MAP_FILE),map_path='/Game/Daedalus/DaedalusWorld',anchor_cm=[-5000.,-19000.,5218.],**helpers)
    exclusive_copy(d.MAP_FILE,a.folder/'before-greenhouse.umap')
    value={'stage':'source_prepared_native_pending','utc':d._utc(),'cfg':cfg,'baseline':d.pin(a.baseline),
        'scope':d.pin(a.scope),'native_source':d.pin(NATIVE),'world_guard':d.pin(a.task/'build_gallery_dispatch_spur.py'),
        'helper_pins':[d.pin(p) for p in helpers.values()],
        'world_helper':d.pin(world_helper),'packet':d.pin(a.folder/'source-packet.json'),
        'snap_source':d.pin(snap),'original_glb':d.pin(source),'manifest':d.pin(manifest),
        'pre_map_backup':d.pin(a.folder/'before-greenhouse.umap'),
        'glass':'HOLD transmission mesh+MIC UNSAVED/UNPLACED; no fallback',
        'limits':'PARTIAL decorative bay. No gameplay/nav/walking/crop/grapple/collision acceptance.'}
    d.write_new(a.folder/'prepared.json',value)
    print(json.dumps({'stage':value['stage'],'native_mutations':0,'prepared':d.pin(a.folder/'prepared.json')}))


def prepared(a):
    value=d.load(a.folder/'prepared.json')
    for key in ('baseline','scope','native_source','world_guard','world_helper','packet','snap_source','original_glb','manifest','pre_map_backup'):
        d._check(value[key])
    for p in value['helper_pins']:d._check(p)
    return value


def claim(a):
    value=prepared(a);d.protect(d.load(value['baseline']['path']));lease=d._lease();mem=resources()
    if (a.folder/'claim.json').exists():raise RuntimeError('retained claim; reconcile instead of restart')
    if d.locks().get('compute'):raise RuntimeError('existing compute must actually terminate/release')
    reply=d.post('/lock',{'me':d.OWNER,'name':'compute','ttl':1200,
        'note':'Authorized32923 one existing greenhouse partial opaque import13/save +7actors one map save/capture/restore. No tests/Play/build/restart/old prop changes.'})
    if reply.get('ok') is not True or not d.same_compute_lease(d.locks().get('compute',{}),reply.get('lock',{})):
        raise RuntimeError('compute identity unconfirmed')
    cfg={**value['cfg'],'deadline_epoch':min(reply['lock']['at']+reply['lock']['ttl'],lease['at']+lease['ttl'])}
    d.write_new(a.folder/'claim.json',{'utc':d._utc(),'compute_claim':reply,'resources':mem,'cfg':cfg})
    print(json.dumps({'stage':'bounded_compute_claimed','claim':reply,'deadline_epoch':cfg['deadline_epoch']}))


def guards(a):
    value=prepared(a);claim=d.load(a.folder/'claim.json');d._lease();resources()
    if not d.same_compute_lease(d.locks().get('compute',{}),claim['compute_claim']['lock']):
        raise RuntimeError('exact bounded compute identity differs')
    if time.time()>claim['cfg']['deadline_epoch']-90:raise RuntimeError('absolute reserve reached')
    cfg=claim['cfg']
    if getattr(a,'remaining',False):
        recovery=d.load(a.folder/'remaining-prepared.json')
        for key in ('adapter','direct_receiver','graph_helper','original_asset_journal'):d._check(recovery[key])
        cfg={**cfg,**recovery['cfg']}
        value={**value,'remaining_adapter':recovery['adapter'],'remaining_cfg':cfg}
    return value,cfg


def module(value):
    code=('from pathlib import Path\nimport hashlib\nsource='+repr(value['native_source']['path'])+
        '\nraw=Path(source).read_bytes()\nif hashlib.sha256(raw).hexdigest()!='+repr(value['native_source']['sha256'])+
        ':raise RuntimeError("pinned greenhouse source changed")\nscope={"__name__":"_codex_greenhouse_delivery","__file__":source}\nexec(compile(raw,source,"exec"),scope)\n')
    if 'remaining_adapter' in value:
        adapter=value['remaining_adapter'];code+=('adapter='+repr(adapter)+'\nraw=Path(adapter["path"]).read_bytes()\n'
            'if hashlib.sha256(raw).hexdigest()!=adapter["sha256"]:raise RuntimeError("remaining-only adapter changed")\n'
            'receiver={"__name__":"_codex_greenhouse_remaining","__file__":adapter["path"]}\nexec(compile(raw,adapter["path"],"exec"),receiver)\n'
            'scope=receiver["install"](scope,'+repr(value['remaining_cfg'])+')\n')
    return code


def asset_journal(a):
    return a.folder/('asset-remaining-native.json' if getattr(a,'remaining',False) else 'asset-native.json')


def remaining_prepare(a):
    prepared(a);source=d.load(a.folder/'asset-native.json')
    if source.get('stage')!='halted_preserve_partial' or source.get('saves')!=[]:raise RuntimeError('known terminal zero-save import required')
    adapter=NATIVE.with_name('daedalus_codex_skyfarm_greenhouse_remaining.py')
    direct=NATIVE.with_name('daedalus_codex_skyfarm_direct_material.py')
    graph=NATIVE.with_name('daedalus_codex_canal_material.py')
    value={'utc':d._utc(),'stage':'REMAINING_ONLY_SOURCE_PREPARED','adapter':d.pin(adapter),
        'direct_receiver':d.pin(direct),'graph_helper':d.pin(graph),'original_asset_journal':d.pin(a.folder/'asset-native.json')}
    value['cfg']={'journal':str(a.folder/'asset-remaining-native.json'),'direct_receiver':value['direct_receiver'],
        'graph_helper':value['graph_helper'],'original_asset_journal':value['original_asset_journal'],
        'graph_witness_directory':str(a.folder/'direct-material-qualified-witnesses')}
    d.write_new(a.folder/'remaining-prepared.json',value)
    print(json.dumps({'stage':value['stage'],'pins':value,'native_mutations':0}))


def retained_call(a,name,command,code,**kw):
    # Any retained dispatch blocks a second call, even when response was lost.
    dispatch=a.folder/(name+'-dispatch.json');reply_path=a.folder/(name+'-reply.json')
    d.write_new(dispatch,{'utc':d._utc(),'stage':'dispatch_pending_no_replay','command':command,
        'code_sha256':hashlib.sha256(code.encode()).hexdigest()})
    (a.folder/(name+'-executed.py')).write_text(code,encoding='utf-8')
    reply=d.wire.call(d.wire.UNREAL,command,code=code,side='Unreal',**kw)
    d.write_new(reply_path,reply)
    result=d.wire.obj(reply,side='Unreal',what=name)
    d.write_new(a.folder/(name+'-result.json'),result)
    return result


def asset(a,operation):
    value,cfg=guards(a)
    if operation=='steps':
        if asset_journal(a).exists():raise RuntimeError('retained asset journal; no replay')
        d.protect(d.load(value['baseline']['path']))
        entry='remaining_steps' if getattr(a,'remaining',False) else 'steps'
        code=module(value)+'\ndef steps():\n return (yield from scope['+repr(entry)+']('+repr(cfg)+'))\n'
    else:
        code=module(value)+'\ndef steps():\n if False: yield\n return scope['+repr(operation)+']('+repr(cfg)+')\n'
    prefix='asset-remaining-' if getattr(a,'remaining',False) else 'asset-'
    result=retained_call(a,prefix+operation,'daedalus.steps',code,label=LABEL,budget_ms=1,timeout=180)
    expected={'preflight':'greenhouse_preflight_complete','steps':'PARTIAL_OPAQUE13_SAVED_GLASS2_HELD',
              'readback':'PARTIAL_OPAQUE13_SAVED_INDEPENDENT_READBACK_GLASS2_HELD'}[operation]
    if result.get('stage')!=expected:raise RuntimeError('native terminal stage differs; inspect retained raw reply/journal')
    print(json.dumps({'stage':result['stage'],'receipt':d.pin(a.folder/(prefix+operation+'-result.json'))}))


def world(a,operation):
    value,cfg=guards(a)
    if operation in ('world_place','world_save'):d.protect(d.load(value['baseline']['path']))
    if operation in ('world_place','world_save','world_readback'):accepted_outputs(a)
    native_tree=ast.parse(Path(value['world_guard']['path']).read_text())
    function=next(n for n in native_tree.body if isinstance(n,ast.FunctionDef) and n.name=='native')
    assignment=next(n for n in function.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
    held=[]
    if asset_journal(a).exists():held=d.load(asset_journal(a)).get('final',{}).get('held_paths',[])
    body=module(value)+'\nresult=scope['+repr(operation)+']('+repr(cfg)+')\n'
    namespace=dict(MARKER=MARKER,body=body,dirty=operation not in ('world_preflight','world_place'),
                   owned=[p.split('.')[0] for p in held])
    code=eval(compile(ast.Expression(assignment.value),'<existing-guard-code>','eval'),namespace)
    result=retained_call(a,operation,'execute_python',code,unattended=False,timeout=110)
    print(json.dumps({'stage':result.get('stage'),'receipt':d.pin(a.folder/(operation+'-result.json'))}))


def camera(a,mode):
    # world phase camera functions receive explicit mode through closed cfg.
    value,cfg=guards(a);cfg={**cfg,'camera_mode':mode}
    native_tree=ast.parse(Path(value['world_guard']['path']).read_text())
    fn=next(n for n in native_tree.body if isinstance(n,ast.FunctionDef) and n.name=='native')
    expression=next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
    held=d.load(asset_journal(a))['final']['held_paths']
    body=module(value)+'\nresult=scope["camera"]('+repr(cfg)+','+repr(mode)+')\n'
    code=eval(compile(ast.Expression(expression),'<existing-world-guard>','eval'),
              dict(MARKER=MARKER,body=body,dirty=True,owned=[p.split('.')[0] for p in held]))
    result=retained_call(a,'camera-'+mode,'execute_python',code,unattended=False,timeout=90)
    print(json.dumps(result))


def accepted_outputs(a):
    report=d.load(asset_journal(a))
    witness=d.load(a.folder/('asset-remaining-readback-result.json' if getattr(a,'remaining',False) else 'asset-readback-result.json'))
    if report.get('stage')!='PARTIAL_OPAQUE13_SAVED_GLASS2_HELD' or witness.get('stage')!='PARTIAL_OPAQUE13_SAVED_INDEPENDENT_READBACK_GLASS2_HELD':
        raise RuntimeError('saved opaque terminal and independent readback required')
    final=report['final'];rows=final['items'];accepted=set(final['accepted_paths']);held=set(final['held_paths'])
    saves=report['saves']
    if (len(accepted)!=13 or len(held)!=2 or accepted&held or len(saves)!=13
            or any(row.get('returned') is not True for row in saves)
            or {row['path'] for row in saves}!=accepted
            or set(report['imported_object_paths'])!=accepted|held
            or final['opaque_triangles']!=1404 or len(rows)!=8
            or witness['inspection']['accepted_paths']!=final['accepted_paths']
            or witness['inspection']['held_paths']!=final['held_paths']):
        raise RuntimeError('exact15 import/13 first TRUE saves/2 held partition differs')
    if any(d._asset_file(path).exists() for path in held):raise RuntimeError('held glass unexpectedly on disk')
    return {path:d.fingerprint(d._asset_file(path)) for path in sorted(accepted)}


def capture(a):
    guards(a)
    if (a.folder/'capture-dispatch.json').exists():raise RuntimeError('retained capture dispatch; no replay')
    d.write_new(a.folder/'capture-dispatch.json',{'utc':d._utc(),'stage':'capture_pending_no_replay'})
    reply=d.wire.call(d.wire.UNREAL,'viewport_screenshot',width=1280,height=720,timeout=70,side='Unreal')
    d.write_new(a.folder/'capture-reply.json',reply)
    result=reply.get('result',reply);data=base64.b64decode(result['image_png_base64'],validate=True)
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('actual PNG missing')
    with (a.folder/'native-greenhouse-partial.png').open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    d.write_new(a.folder/'capture-result.json',{'utc':d._utc(),'stage':'native_capture_saved','image':d.pin(a.folder/'native-greenhouse-partial.png'),
        'appearance_review':'pending personal native PNG inspection','glass':'not placed; partial opaque bay'})
    print(json.dumps(d.pin(a.folder/'native-greenhouse-partial.png')))


def release(a):
    claim=d.load(a.folder/'claim.json');current=d.locks().get('compute',{})
    if not d.same_compute_lease(current,claim['compute_claim']['lock']):raise RuntimeError('different lease; do not unlock')
    if not a.terminal:raise RuntimeError('explicit actual native terminal receipt required')
    terminal=d.load(a.terminal)
    if (not isinstance(terminal,dict)
            or terminal.get('stage')!='PARTIAL_GREENHOUSE_SEVEN_PLACED_ONE_MAP_SAVED_READBACK'
            or terminal.get('map_save_return') is not True
            or terminal.get('new_saved_packages')!=13 or len(terminal.get('new_actors',[]))!=7):
        raise RuntimeError('actual completed thirteen-save/seven-actor/TRUE-map terminal required; reconcile other outcomes separately')
    d.write_new(a.folder/'release-dispatch.json',{'utc':d._utc(),'terminal':d.pin(a.terminal)})
    reply=d.post('/unlock',{'me':d.OWNER,'name':'compute'});after=d.locks()
    if reply.get('ok') is not True or after.get('compute'):raise RuntimeError('explicit release not confirmed')
    d.write_new(a.folder/'compute-release.json',{'utc':d._utc(),'stage':'released_verified','reply':reply,'locks_after':after,'terminal':d.pin(a.terminal)})
    print(json.dumps(d.load(a.folder/'compute-release.json')))


def finalize(a):
    """File-only promotion of exact successful readbacks; never replays native."""
    value=prepared(a);base=d.load(value['baseline']['path']);outputs=accepted_outputs(a)
    observed=d.load(a.folder/'world_readback-result.json');saved=d.load(a.folder/'map-save-native.json')
    if (observed.get('stage')!='PARTIAL_GREENHOUSE_SEVEN_PLACED_ONE_MAP_SAVED_READBACK'
            or observed.get('tracked_actor_count')!=152 or observed.get('new_actor_count')!=7
            or len(observed['scene']['actors'])!=152 or saved.get('save_return') is not True
            or saved.get('stage')!='ONE_MAP_SAVE_TRUE'):
        raise RuntimeError('actual7placed/oneTRUEsave/152readback required')
    previous={r['path']:r for r in base['scene']['actors']};current={r['path']:r for r in observed['scene']['actors']}
    if any(current.get(path)!=row for path,row in previous.items()):raise RuntimeError('original145records changed')
    backup=a.folder/'saved-package-backups';backup.mkdir(exist_ok=True);backups=dict(base['package_backups'])
    for path,expected in outputs.items():
        target=backup/d._asset_file(path).name
        if not target.exists():exclusive_copy(d._asset_file(path),target)
        if d.fingerprint(target)!=expected:raise RuntimeError('new asset backup differs')
        backups[path]=str(target)
    target=a.folder/'saved-greenhouse.umap'
    if not target.exists():exclusive_copy(d.MAP_FILE,target)
    if d.fingerprint(target)!=d.fingerprint(d.MAP_FILE):raise RuntimeError('new saved map backup differs')
    extended=copy.deepcopy(base)
    extended.update(utc=d._utc(),stage='greenhouse_partial_opaque_saved_231packages_152actors',
        packages={**base['packages'],**outputs},package_backups=backups,package_count=231,
        map=d.pin(d.MAP_FILE),map_backup=str(target),scene=observed['scene'],actor_records=152,
        provenance={'previous_baseline':value['baseline'],'new_native_readback':d.pin(a.folder/'world_readback-result.json'),
                    'source_glb':value['original_glb'],'glass':'exact2unsaved/unplacedobjects excluded'},
        limits='Partial opaque decorative greenhouse; unsupported glass held unsaved/unplaced. No gameplay/collision/nav/crop/grapple acceptance.')
    d.protect(extended)
    destination=a.folder/'saved-production-baseline.json'
    if not destination.exists():d.write_new(destination,extended)
    else:
        retained=d.load(destination)
        if any(retained[k]!=extended[k] for k in ('packages','package_backups','map','scene','provenance')):
            raise RuntimeError('retained baseline differs')
    completion={'utc':d._utc(),'stage':observed['stage'],'source_glb':value['original_glb'],
        'native_namespace':ROOT,'saved_outputs':outputs,'new_saved_packages':13,'new_actors':observed['new_actors'],
        'map':d.pin(d.MAP_FILE),'map_save_return':True,'map_save_seconds':saved['save_seconds'],
        'native_asset_journal':d.pin(asset_journal(a)),'baseline':d.pin(destination),
        'capture':d.pin(a.folder/'native-greenhouse-partial.png'),
        'glass':'two held unsaved/unplaced objects; transmission receiving profile unsupported',
        'limits':observed['limits'],'tests_run':False}
    d.write_new(a.folder/'completion.json',completion)
    print(json.dumps({'stage':completion['stage'],'packages':231,'actors':152,'baseline':completion['baseline']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['prepare','remaining_prepare','claim','asset-preflight','asset-steps','asset-readback','world_preflight','world_place','world_save','world_readback','frame','restore','capture','finalize','release'])
    p.add_argument('--folder',type=Path,required=True);p.add_argument('--baseline',type=Path)
    p.add_argument('--scope',type=Path);p.add_argument('--task',type=Path,required=True);p.add_argument('--terminal',type=Path);p.add_argument('--remaining',action='store_true')
    a=p.parse_args();a.folder=a.folder.resolve();a.task=a.task.resolve()
    if a.baseline:a.baseline=a.baseline.resolve()
    if a.phase.startswith('asset-'):asset(a,a.phase.split('-',1)[1])
    elif a.phase.startswith('world_'):world(a,a.phase)
    elif a.phase in ('frame','restore'):camera(a,a.phase)
    else:globals()[a.phase](a)
