# SPDX-License-Identifier: MIT
"""Bounded static-asset batch execution over the existing pipeline, with durable resume evidence."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import uuid
from . import ship as pipeline
from . import wire,glb,teamlink
from .scene_observation import read_json

MAX_ASSETS=500
SAFE_NAME=re.compile(r'[A-Za-z][A-Za-z0-9_]{0,127}')
TERMINAL={'verified','rejected'}
RESUMABLE={'preparing','prepared','not-dispatched'}
REPLAY_UNSAFE={'outcome-unknown','reply-received','error-received','dispatch-pending'}


class BatchError(ValueError):
    pass


class ReconciliationRequired(BatchError):
    def __init__(self,name,record):
        super().__init__('reconcile prior dispatch before importing '+name)
        self.asset=name;self.record=copy.deepcopy(record)


class JournalBusy(BatchError):
    pass


def need(condition,message):
    if not condition:raise BatchError(message)


def check_sent(value):
    need(isinstance(value,dict) and isinstance(value.get('objects'),list) and value['objects'],'Blender export report must contain objects')
    names=set()
    for item in value['objects']:
        need(isinstance(item,dict),'export object must be an object')
        name=item.get('name');need(isinstance(name,str) and name and name not in names,'export object names must be unique');names.add(name)
        triangles=item.get('triangles');need(type(triangles) is int and triangles>=0,'triangle count must be a nonnegative integer')
        materials=item.get('materials');need(isinstance(materials,list) and all(isinstance(m,str) for m in materials),'material names missing')
        dims=item.get('dims');need(isinstance(dims,list) and len(dims)==3,'three export dimensions required')
        for n in dims:
            try:finite=math.isfinite(n)
            except (TypeError,OverflowError):finite=False
            need(type(n) in (int,float) and finite and n>=0,'dimensions must be finite and nonnegative')
    return copy.deepcopy(value)


def load_spec(path,source_root=None):
    raw=path.read_bytes();need(len(raw)<=8_000_000,'batch spec exceeds byte bound')
    value=read_json(path)
    need(isinstance(value,dict) and type(value.get('schema_version')) is int and value['schema_version']==1,'batch schema_version1 required')
    assets=value.get('assets');need(isinstance(assets,list) and 1<=len(assets)<=MAX_ASSETS,'batch requires1..500 explicit assets')
    root=(source_root or path.parent).resolve()
    names=set();destinations=set();records=[]
    for row in assets:
        need(isinstance(row,dict),'asset spec must be an object')
        name=row.get('name');need(isinstance(name,str) and SAFE_NAME.fullmatch(name),'safe asset name required')
        need(name not in names,'duplicate asset name');names.add(name)
        need(row.get('kind')=='static','this pipeline route accepts static assets only; use cast importer for rigs')
        digest=row.get('sha256');need(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest),'source SHA256 required')
        source=row.get('glb');need(isinstance(source,str) and source,'GLB source required')
        glb=(root/source).resolve();need(glb.is_relative_to(root),'GLB source escapes operator root')
        need(glb.suffix.lower()=='.glb','only GLB sources accepted')
        dest=row.get('dest','/Game/Daedalus/Assets')
        need(isinstance(dest,str) and re.fullmatch(r'/Game(?:/[A-Za-z0-9_]+)+',dest),'safe Unreal destination required')
        target=dest+'/'+name;need(target not in destinations,'duplicate import destination');destinations.add(target)
        records.append({'name':name,'path':str(glb),'sha256':digest,'blender':check_sent(row.get('blender')),'dest':dest})
    return {'schema_version':1,'spec_sha256':hashlib.sha256(raw).hexdigest(),'source_root':str(root),'assets':records}


def check_static(path):
    doc=glb.read_json(path)
    need(not doc.get('skins') and not doc.get('animations'),'rigged/animated GLB requires the dedicated cast importer')
    need(not any(primitive.get('targets') for mesh in doc.get('meshes',[]) for primitive in mesh.get('primitives',[])),
         'morph targets are outside the static pipeline route')


class LeaseGuard:
    """Observe an existing Unreal lease. Never acquire, steal or renew it implicitly."""
    def __init__(self,owner,port=teamlink.PORT,minimum_left=305):
        need(isinstance(owner,str) and owner,'explicit lease owner required')
        self.link=teamlink.Link(owner,port);self.owner=owner;self.minimum_left=minimum_left
    def __call__(self):
        locks=self.link._call('GET','/locks')
        need(isinstance(locks,dict),'broker lease observation unavailable')
        lease=locks.get('unreal')
        need(isinstance(lease,dict) and lease.get('holder')==self.owner,'Unreal lease is not held by this operator')
        left=lease.get('left_s')
        need(type(left) in (int,float) and math.isfinite(left) and left>=self.minimum_left,
             'Unreal lease must cover the full import observation window')
        return copy.deepcopy(lease)


class WriterLock:
    """One local process owns this journal. No PID-based stale lock guessing."""
    def __init__(self,path):self.path=path;self.stream=None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.stream=self.path.open('a+b')
        try:
            if os.name=='nt':
                import msvcrt
                self.stream.seek(0)
                if not self.stream.read(1):self.stream.write(b'0');self.stream.flush()
                self.stream.seek(0);msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:
            self.stream.close();self.stream=None
            raise JournalBusy('another process owns the batch journal') from error
        return self
    def __exit__(self,*unused):
        if self.stream is None:return
        try:
            if os.name=='nt':
                import msvcrt
                self.stream.seek(0);msvcrt.locking(self.stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_UN)
        finally:self.stream.close();self.stream=None


class BatchJournal:
    def __init__(self,path,spec):
        self.path=path
        if path.exists():
            self.value=read_json(path)
            need(isinstance(self.value,dict) and type(self.value.get('schema_version')) is int and self.value['schema_version']==1,'unsupported journal')
            need(self.value.get('spec_sha256')==spec['spec_sha256'] and self.value.get('source_root')==spec['source_root'],'spec/root changed; never resume under different input')
            need(isinstance(self.value.get('records'),dict),'journal records missing')
            allowed={a['name'] for a in spec['assets']}
            need(set(self.value['records'])<=allowed,'journal contains unknown asset identities')
            for name,record in self.value['records'].items():
                need(isinstance(record,dict) and record.get('state') in TERMINAL|RESUMABLE|REPLAY_UNSAFE,'unknown journal state; refuse replay')
                need(type(record.get('attempts')) is int and record['attempts']>=1,'invalid journal attempt count')
                if record['state'] in TERMINAL:
                    report=record.get('report')
                    need(isinstance(report,dict) and type(report.get('ok')) is bool and
                         report['ok']==(record['state']=='verified'),'terminal journal outcome is inconsistent')
        else:
            self.value={'schema_version':1,'run_id':uuid.uuid4().hex,'spec_sha256':spec['spec_sha256'],
                        'source_root':spec['source_root'],'created_at':time.time(),'records':{}}
    def save(self):
        self.value['updated_at']=time.time()
        pipeline.write_report(str(self.path),self.value)
    def get(self,name):return self.value['records'].get(name)
    def checkpoint(self,name,report):
        state=report.get('import_state','preparing')
        record=self.value['records'].setdefault(name,{'attempts':0})
        record.update(state=state,updated_at=time.time(),report=copy.deepcopy(report))
        self.save()
    def begin(self,name):
        prior=self.get(name)
        if prior and prior.get('state') not in RESUMABLE:raise ReconciliationRequired(name,prior)
        attempts=(prior or {}).get('attempts',0)+1
        self.value['records'][name]={'state':'preparing','attempts':attempts,'started_at':time.time()}
        self.save()
    def finish(self,name,report):
        record=self.value['records'][name]
        record.update(state='verified' if report['ok'] else 'rejected',updated_at=time.time(),report=copy.deepcopy(report))
        self.save()
    def failure(self,name,report,error):
        record=self.value['records'][name]
        # A pipeline callback has already persisted unknown before send. Preserve it.
        state=report.get('import_state',record.get('state','preparing'))
        record.update(state=state,error={'type':type(error).__name__,'message':str(error)},report=copy.deepcopy(report),updated_at=time.time())
        self.save()
    def summary(self):
        counts={state:0 for state in ('verified','rejected','preparing','prepared','not-dispatched','outcome-unknown','reply-received','error-received')}
        for record in self.value['records'].values():
            state=record.get('state','unknown');counts[state]=counts.get(state,0)+1
        return {'run_id':self.value['run_id'],'spec_sha256':self.value['spec_sha256'],'counts':counts,'journal':str(self.path)}

    def inspect(self,spec,check_retained=False):
        """Return bounded reconciliation evidence without publishing or making bridge calls."""
        rows=[]
        for asset in spec['assets']:
            record=self.get(asset['name']) or {}
            state=record.get('state','not-started')
            report=record.get('report') or {}
            need(isinstance(report,dict),'invalid retained report')
            transport=report.get('transport') or {}
            need(isinstance(transport,dict),'invalid retained transport evidence')
            binding=report.get('import_artifact')
            row={'name':asset['name'],'state':state,'attempts':record.get('attempts',0),
                 'action':'skip-recorded-terminal' if state in TERMINAL else
                          'reconcile-before-mutation' if state in REPLAY_UNSAFE else 'eligible-for-explicit-run',
                 'destination':asset['dest']+'/'+asset['name'],
                 'request_id':transport.get('request_id'),'command':transport.get('command'),
                 'transport_state':transport.get('state'),'import_path':report.get('import_path'),
                 'import_artifact':copy.deepcopy(binding),
                 'started_at':record.get('started_at'),'updated_at':record.get('updated_at')}
            if check_retained and row['import_path']:
                need(isinstance(row['import_path'],str),'retained snapshot path must be a string')
                try:
                    actual=pipeline.fingerprint(row['import_path'])
                    row['retained_file']={'available':True,'artifact':actual,
                                          'matches_recorded_identity':binding is not None and actual==binding}
                except OSError as error:
                    row['retained_file']={'available':False,'error_type':type(error).__name__}
            rows.append(row)
        result=self.summary()
        result.update(assets=rows,mutation=False,bridge_queried=False,
                      reconciliation_required=sum(row['state'] in REPLAY_UNSAFE for row in rows),
                      scope='Journal evidence only; terminal records and file hashes do not prove current editor state.')
        return result


class BatchExecutor:
    def __init__(self,spec,journal,addr=wire.UNREAL,timeout=300,authorize=None):
        self.spec=spec;self.journal=journal;self.addr=addr;self.timeout=timeout;self.authorize=authorize
    def plan(self):
        result=[]
        for asset in self.spec['assets']:
            actual=pipeline.fingerprint(asset['path'])
            need(actual['sha256']==asset['sha256'],'source hash changed for '+asset['name'])
            check_static(asset['path'])
            result.append({'name':asset['name'],'path':asset['path'],'sha256':actual['sha256'],
                           'bytes':actual['bytes'],'destination':asset['dest']+'/'+asset['name']})
        return result
    def run(self,limit=MAX_ASSETS):
        need(type(limit) is int and 1<=limit<=MAX_ASSETS,'run limit must be1..500')
        need(callable(self.authorize),'an explicit lease observer is required for execution')
        processed=0
        for asset in self.spec['assets']:
            prior=self.journal.get(asset['name'])
            if prior and prior.get('state') in TERMINAL:continue
            if processed>=limit:break
            lease=self.authorize()
            self.journal.begin(asset['name'])
            report={'name':asset['name'],'phase':'preflight'}
            try:
                actual=pipeline.fingerprint(asset['path'])
                need(actual['sha256']==asset['sha256'],'source hash changed before import')
                check_static(asset['path'])
                report=pipeline.prebuilt(asset['name'],asset['path'],asset['blender'])
                need(report['artifact']['sha256']==asset['sha256'],'source changed while preparing import')
                report['lease_observation']=lease
                report['phase']='import'
                self.journal.checkpoint(asset['name'],report)
                def dispatch_guard():
                    report['dispatch_lease_observation']=self.authorize()
                    self.journal.checkpoint(asset['name'],report)
                pipeline.land(report,asset['dest'],True,self.addr,self.timeout,
                              checkpoint=lambda r,name=asset['name']:self.journal.checkpoint(name,r),
                              before_dispatch=dispatch_guard)
                report['phase']='verified'
                self.journal.finish(asset['name'],report)
                processed+=1
            except Exception as error:
                self.journal.failure(asset['name'],report,error)
                # Stop the batch on ambiguous/failed dispatch. Never move to another
                # editor mutation while the prior accepted work may still be running.
                raise
        result=self.journal.summary();result['processed_this_run']=processed
        result['remaining']=sum(not self.journal.get(a['name']) or self.journal.get(a['name']).get('state') not in TERMINAL for a in self.spec['assets'])
        return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--spec',type=Path,required=True)
    ap.add_argument('--source-root',type=Path)
    ap.add_argument('--journal',type=Path)
    ap.add_argument('--me',help='existing Unreal lease holder, required for execution')
    ap.add_argument('--hub-port',type=int,default=teamlink.PORT)
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument('--run',action='store_true',help='explicitly execute imports; default is file-only planning')
    mode.add_argument('--status',action='store_true',help='read existing journal reconciliation evidence; no editor or writes')
    ap.add_argument('--check-retained',action='store_true',help='with --status, hash retained snapshots without changing them')
    ap.add_argument('--limit',type=int,default=MAX_ASSETS)
    ap.add_argument('--unreal-port',type=int,default=wire.UNREAL[1])
    ap.add_argument('--timeout',type=float,default=300)
    a=ap.parse_args(argv)
    spec=load_spec(a.spec,a.source_root)
    need(not a.check_retained or a.status,'--check-retained requires --status')
    if a.status:
        need(a.journal is not None and a.journal.is_file(),'--status requires an existing --journal')
        journal=BatchJournal(a.journal,spec)
        result=journal.inspect(spec,a.check_retained)
        print(json.dumps(result,indent=2))
        return 2 if result['reconciliation_required'] else 0
    if not a.run:
        # No journal is created and no bridge is queried in planning mode.
        executor=BatchExecutor(spec,None)
        print(json.dumps({'plan':executor.plan(),'mutation':False},indent=2));return 0
    need(a.journal is not None,'--journal required for execution')
    need(math.isfinite(a.timeout) and 0<a.timeout<=1800 and 1<=a.unreal_port<=65535 and 1<=a.hub_port<=65535,'invalid timeout or bridge port')
    guard=LeaseGuard(a.me,a.hub_port,a.timeout+5)
    with WriterLock(Path(str(a.journal)+'.lock')):
        journal=BatchJournal(a.journal,spec);executor=BatchExecutor(spec,journal,(wire.UNREAL[0],a.unreal_port),a.timeout,guard)
        try:result=executor.run(a.limit)
        except Exception as error:
            print(json.dumps(dict(journal.summary(),stopped=True,error={'type':type(error).__name__,'message':str(error)},
                                  retry='No automatic replay. Inspect retained request/snapshot and reconcile editor outcome.'),indent=2))
            return 2
    print(json.dumps(result,indent=2));return 0 if not result['remaining'] and not result['counts']['rejected'] else 1

if __name__=='__main__':raise SystemExit(main())
