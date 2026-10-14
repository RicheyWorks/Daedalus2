# SPDX-License-Identifier: MIT
"""Read-only night/cast receipt summary. Never queries or controls an editor or replays work."""
import argparse
import json
import os
import re
from pathlib import Path

MAX_BYTES=8*1024*1024
CAST_STATES={'prepared','outcome-unknown','reply-received','partial-terminal',
             'reconciliation-required','rejected','imports-completed','completed'}


def read(path):
    if path.stat().st_size>MAX_BYTES:raise ValueError('receipt exceeds8MiB')
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('duplicate JSON field')
            value[key]=item
        return value
    def nonfinite(value):raise ValueError('nonfinite JSON value')
    with path.open('rb') as stream:raw=stream.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('receipt exceeds8MiB')
    value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_constant=nonfinite)
    if not isinstance(value,dict):raise ValueError('receipt must be an object')
    return value


def cast_summary(path,value=None):
    value=read(path) if value is None else value
    if type(value.get('schema_version')) is not int or value['schema_version']!=1 or value.get('state') not in CAST_STATES:
        raise ValueError('unsupported cast receipt')
    planned,assets=value.get('planned'),value.get('assets')
    if not isinstance(planned,list) or not isinstance(assets,list) or not 1<=len(planned)<=500 or len(assets)>len(planned):
        raise ValueError('invalid import coverage')
    if any(not isinstance(row,dict) or not isinstance(row.get('id'),str) or
           not isinstance(row.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',row['sha256']) for row in planned):
        raise ValueError('planned identity/hash missing')
    ids=[row['id'] for row in planned]
    if len(set(ids))!=len(ids):raise ValueError('duplicate planned identities')
    counts={'imported':0,'skipped':0,'failed':0}
    for row,expected in zip(assets,planned):
        if not isinstance(row,dict) or row.get('id')!=expected['id'] or row.get('sha256')!=expected['sha256'] or row.get('status') not in counts:
            raise ValueError('terminal row identity differs')
        counts[row['status']]+=1
    if value['state'] in ('completed','imports-completed','rejected') and len(assets)!=len(planned):
        raise ValueError('terminal receipt lacks complete identity coverage')
    if 'counts' in value and (not isinstance(value['counts'],dict) or value['counts']!=counts or
            any(type(n) is not int for n in value['counts'].values())):
        raise ValueError('recorded counts contradict observed rows')
    if value['state'] in ('completed','imports-completed') and counts['failed']:
        raise ValueError('completed receipt contains failed assets')
    return {'receipt':str(path),'recorded_state':value['state'],'planned':len(planned),
            'terminal_rows':len(assets),'counts':counts,'last_command':value.get('command'),
            'evidence_kind':value.get('evidence_kind'),'reconciliation_required':value['state'] not in ('completed','imports-completed','rejected'),
            'native_quiescence':'not-established-by-receipt'}


def summarize(path,jobs_root):
    value=read(path)
    references=value.get('import_receipts',[])
    if not isinstance(references,list) or len(references)>8:raise ValueError('invalid import receipt list')
    root=jobs_root.resolve();imports=[]
    for reference in references:
        try:
            if not isinstance(reference,str):raise ValueError('receipt reference must be a path')
            target=Path(reference).resolve()
            if not target.is_relative_to(root):raise ValueError('referenced receipt escapes jobs root')
            imports.append(cast_summary(target))
        except (OSError,ValueError,TypeError,KeyError) as error:
            imports.append({'receipt':reference,'unavailable_or_invalid':True,'error':str(error)[:300],
                            'reconciliation_required':True})
    outcome=value.get('outcome')
    status=outcome.get('status') if isinstance(outcome,dict) else None
    reported_status=status
    validation_errors=[]
    if status not in ('running','passed','failed','unverified'):status='unverified'
    if status=='passed':
        counts=outcome.get('counts')
        valid=(outcome.get('passed') is True and type(outcome.get('exit_code')) is int and outcome['exit_code']==0 and
               type(outcome.get('scenario_returncode')) is int and outcome['scenario_returncode']==0 and
               type(outcome.get('editor_errors')) is int and outcome['editor_errors']==0 and
               isinstance(counts,dict) and type(counts.get('total')) is int and counts['total']>0 and
               type(counts.get('passed')) is int and counts['passed']==counts['total'])
        if not valid:
            status='unverified'
            validation_errors.append('passed outcome lacks consistent scenario/log evidence')
    return {'receipt':str(path),'run_id':value.get('checkpoint_run_id',value.get('run_id')),
            'recorded_status':status,'phase':value.get('stopped_phase',value.get('phase')),
            'reported_status':reported_status,'validation_errors':validation_errors,
            'sha':value.get('sha'),'build_job':value.get('build_job'),'build_pid':value.get('build_pid'),
            'reported_total':value.get('total'),'imports':imports,
            'elapsed_seconds':value.get('elapsed_seconds'),'stage_intervals':value.get('stage_intervals',[]),
            'reconciliation_required':status!='passed' or any(row['reconciliation_required'] for row in imports),
            'scope':'Saved receipt evidence only; no current engine state or replay authorization',
            'mutation':False,'editor_queried':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--jobs-root',type=Path,default=Path(os.environ.get('LOCALAPPDATA','.'))/'Daedalus'/'jobs')
    args=parser.parse_args(argv)
    result=summarize(args.receipt,args.jobs_root)
    print(json.dumps(result,indent=2))
    return 2 if result['reconciliation_required'] else 1 if result['recorded_status']=='failed' else 0


if __name__=='__main__':raise SystemExit(main())
