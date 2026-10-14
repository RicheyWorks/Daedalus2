# SPDX-License-Identifier: MIT
"""Count saved MCP tool descriptions; never connects to a server or executes an action."""
import argparse
import hashlib
import json
import math
import os
import uuid
from pathlib import Path


def read_capture(path):
    with path.open('rb') as stream:raw=stream.read(16*1024*1024+1)
    if len(raw)>16*1024*1024:raise ValueError('Capture exceeds16MiB')
    def unique(pairs):
        out={}
        for key,value in pairs:
            if key in out:raise ValueError('Duplicate JSON field: '+key)
            out[key]=value
        return out
    def invalid(value):raise ValueError('Nonfinite JSON '+value)
    return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_constant=invalid),hashlib.sha256(raw).hexdigest()


def text(value,label):
    if not isinstance(value,str) or not value or len(value)>512:raise ValueError('Invalid '+label)
    return value


def finite_seconds(value):
    try:return type(value) in (int,float) and math.isfinite(value) and value>=0
    except (TypeError,OverflowError):return False


def timing_metrics(values):
    if any(not finite_seconds(value) for value in values):raise ValueError('Invalid timing observation')
    if not values:return {'attempts':0,'recorded_sum_seconds':0,'mean_seconds':None,'p50_seconds':None,'p95_seconds':None}
    ordered=sorted(float(value) for value in values)
    try:total=math.fsum(ordered)
    except OverflowError as error:raise ValueError('Timing sum exceeds finite range') from error
    if not math.isfinite(total):raise ValueError('Timing sum is nonfinite')
    return {'attempts':len(ordered),'recorded_sum_seconds':total,'mean_seconds':total/len(ordered),
            'p50_seconds':ordered[max(0,math.ceil(len(ordered)*0.5)-1)],
            'p95_seconds':ordered[max(0,math.ceil(len(ordered)*0.95)-1)],
            'min_seconds':ordered[0],'max_seconds':ordered[-1]}


def benchmark_summary(result):
    states=('returned','failed','outcome-unknown')
    grouped={state:[] for state in states};toolsets={}
    for row in result['actions']:
        for attempt in row.get('recorded_attempts',[]):
            state=attempt['state'];seconds=attempt['elapsed_seconds']
            grouped[state].append(seconds)
            toolsets.setdefault(row['toolset'],{key:[] for key in states})[state].append(seconds)
    return {'by_state':{state:timing_metrics(values) for state,values in grouped.items()},
            'per_toolset':{name:{state:timing_metrics(values) for state,values in groups.items()}
                           for name,groups in sorted(toolsets.items())},
            'percentile_method':'nearest rank',
            'scope':'Recorded attempt durations; sums are not run wall time and returned calls are not verified effects'}


def coverage_summary(rows):
    def counts(group):
        states=[{attempt['state'] for attempt in row.get('recorded_attempts',[])} for row in group]
        attempted=sum(bool(state) for state in states)
        return {'exposed_actions':len(group),'actions_without_attempts':len(group)-attempted,
                'actions_with_recorded_attempts':attempted,
                'actions_with_returned_attempts':sum('returned' in state for state in states),
                'actions_with_failed_attempts':sum('failed' in state for state in states),
                'actions_with_unknown_attempts':sum('outcome-unknown' in state for state in states),
                'recorded_attempt_coverage_percent':100*attempted/len(group) if group else None,
                'effects_verified':0,'all_effects_verified':False}
    sets={}
    for row in rows:sets.setdefault(row['toolset'],[]).append(row)
    return {'total':counts(rows),'per_toolset':{name:counts(group) for name,group in sorted(sets.items())},
            'count_semantics':'Outcome categories overlap across attempts; recorded coverage is not effect verification'}


def catalog(capture):
    if not isinstance(capture,dict) or type(capture.get('schema_version')) is not int or capture['schema_version']!=1:
        raise ValueError('Expected saved-description wrapper schema1')
    sets=capture.get('toolsets')
    if not isinstance(sets,dict) or not 1<=len(sets)<=512:raise ValueError('Expected1..512 saved toolset descriptions')
    rows=[];counts={};seen=set()
    for toolset,description in sorted(sets.items()):
        text(toolset,'toolset')
        tools=description.get('tools') if isinstance(description,dict) else None
        if not isinstance(tools,list) or len(tools)>10000:raise ValueError('Tool description tools array missing/oversized')
        counts[toolset]=len(tools)
        for tool in tools:
            if not isinstance(tool,dict):raise ValueError('Tool description must be an object')
            name=text(tool.get('name'),'tool name')
            identity=(toolset,name)
            if identity in seen:raise ValueError('Duplicate exposed action identity')
            seen.add(identity)
            schema=tool.get('inputSchema')
            if schema is not None and not isinstance(schema,dict):raise ValueError('Input schema must be an object')
            annotations=tool.get('annotations',{})
            if not isinstance(annotations,dict):raise ValueError('Annotations must be an object')
            for hint in ('readOnlyHint','destructiveHint','idempotentHint','openWorldHint'):
                if hint in annotations and type(annotations[hint]) is not bool:raise ValueError('Annotation hint must be boolean')
            prose=tool.get('description','')
            if not isinstance(prose,str):raise ValueError('Tool description text must be a string')
            required=schema.get('required',[]) if schema else []
            if not isinstance(required,list) or any(not isinstance(field,str) for field in required):raise ValueError('Required parameter list invalid')
            action_id=hashlib.sha256(json.dumps([toolset,name],ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()
            schema_hash=hashlib.sha256(json.dumps(schema,sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest() if schema is not None else None
            row={'toolset':toolset,'name':name,'call_name':text(name.split('.')[-1],'short call name'),
                 'action_id':action_id,'input_schema_sha256':schema_hash,
                 'description':prose,'input_schema':schema,'required_parameters':required,
                 'annotations':annotations,'read_only_hint':annotations.get('readOnlyHint'),
                 'execution_state':'not-executed','execution_evidence':None}
            rows.append(row)
            if len(rows)>50000:raise ValueError('Catalog exceeds50000 exposed actions')
    short_names={}
    for row in rows:short_names.setdefault((row['toolset'],row['call_name']),[]).append(row)
    collisions=[]
    for (toolset,short),group in sorted(short_names.items()):
        ambiguous=len(group)>1
        for row in group:row['client_short_name_ambiguous']=ambiguous
        if ambiguous:collisions.append({'toolset':toolset,'call_name':short,'names':[row['name'] for row in group]})
    return {'schema_version':1,'exposed_actions':len(rows),'toolsets':len(sets),'per_toolset':counts,
            'client_short_name_collisions':collisions,
            'actions':rows,'executed_actions':0,'mutation':False,'server_queried':False,
            'coverage':coverage_summary(rows),
            'scope':'Unique toolset/name pairs in saved descriptions; not every engine function, execution proof or risk approval'}


def attach_attempts(result,attempts,evidence_root):
    if not isinstance(attempts,dict) or type(attempts.get('schema_version')) is not int or attempts['schema_version']!=1:
        raise ValueError('Expected attempt wrapper schema1')
    if attempts.get('capture_sha256')!=result['capture_sha256']:
        raise ValueError('Attempts belong to another tool capture')
    records=attempts.get('attempts')
    if not isinstance(records,list) or len(records)>50000:raise ValueError('Attempt list missing/oversized')
    root=evidence_root.resolve();index={(row['toolset'],row['name']):row for row in result['actions']};ids=set()
    for attempt in records:
        if not isinstance(attempt,dict):raise ValueError('Attempt must be an object')
        aid=text(attempt.get('attempt_id'),'attempt ID')
        if aid in ids:raise ValueError('Duplicate attempt ID')
        ids.add(aid)
        identity=(text(attempt.get('toolset'),'toolset'),text(attempt.get('name'),'name'))
        if identity not in index:raise ValueError('Attempt references undiscovered action')
        if 'action_id' in attempt and attempt['action_id']!=index[identity]['action_id']:
            raise ValueError('Attempt stable action ID differs')
        state=attempt.get('state')
        if state not in ('returned','failed','outcome-unknown'):raise ValueError('Unsupported attempt state')
        seconds=attempt.get('elapsed_seconds')
        if not finite_seconds(seconds):
            raise ValueError('Attempt timing must be finite/nonnegative')
        evidence=attempt.get('evidence',[])
        if not isinstance(evidence,list) or len(evidence)>32:raise ValueError('Evidence list invalid')
        verified=[]
        for item in evidence:
            if not isinstance(item,dict):raise ValueError('Evidence must be an object')
            path=(root/text(item.get('path'),'evidence path')).resolve()
            if not path.is_relative_to(root):raise ValueError('Evidence path escapes root')
            with path.open('rb') as stream:
                digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if item.get('sha256')!=digest:raise ValueError('Evidence bytes differ from recorded hash')
            verified.append({'path':str(path),'sha256':digest})
        row=index[identity]
        row.setdefault('recorded_attempts',[]).append({'attempt_id':aid,'state':state,'elapsed_seconds':seconds,
                                                     'evidence':verified,'effect_verified':False})
        row['execution_state']='recorded-'+state
    result['recorded_attempts']=len(records)
    result['actions_with_recorded_attempts']=sum(bool(row.get('recorded_attempts')) for row in result['actions'])
    for row in result['actions']:
        row['unresolved_attempts']=sum(attempt['state']=='outcome-unknown' for attempt in row.get('recorded_attempts',[]))
        row['reconciliation_required']=bool(row['unresolved_attempts'])
    result['unresolved_attempts']=sum(row['unresolved_attempts'] for row in result['actions'])
    result['effects_verified']=0
    result['attempt_scope']='Recorded attempt/timing claims and hash-bound files; artifact presence does not prove an in-world effect'
    result['benchmark_summary']=benchmark_summary(result)
    result['coverage']=coverage_summary(result['actions'])
    return result


def publish_new(path,result):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('x',encoding='utf-8',newline='\n') as stream:
            json.dump(result,stream,indent=2,allow_nan=False)
            stream.write('\n');stream.flush();os.fsync(stream.fileno())
        # Hard-link publication is no-clobber and exposes only complete bytes.
        # Unsupported filesystems fail rather than replacing a prior artifact.
        os.link(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def compare_catalogs(before,after):
    old={row['action_id']:row for row in before['actions']}
    new={row['action_id']:row for row in after['actions']}
    def identity(row):return {key:row[key] for key in ('action_id','toolset','name')}
    added=[identity(new[key]) for key in sorted(new.keys()-old.keys())]
    removed=[identity(old[key]) for key in sorted(old.keys()-new.keys())]
    changed=[]
    fields=('input_schema_sha256','annotations','description','client_short_name_ambiguous')
    for key in sorted(old.keys() & new.keys()):
        differences={field:{'before':old[key][field],'after':new[key][field]}
                     for field in fields if old[key][field]!=new[key][field]}
        if differences:changed.append(dict(identity(new[key]),changes=differences))
    return {'added':added,'removed':removed,'changed':changed,
            'unchanged_actions':len(old.keys() & new.keys())-len(changed),
            'metadata_matches':not added and not removed and not changed,
            'scope':'Differences between saved exposed metadata; no runtime availability or behavior assertion'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--attempts',type=Path,help='optional saved attempt wrapper bound to this capture SHA')
    parser.add_argument('--evidence-root',type=Path,help='required with --attempts; referenced files must remain inside it')
    parser.add_argument('--baseline-capture',type=Path,help='optional prior saved descriptions for exposed metadata comparison')
    args=parser.parse_args(argv)
    capture,digest=read_capture(args.capture)
    result=catalog(capture);result['capture_sha256']=digest
    if args.baseline_capture:
        prior,prior_digest=read_capture(args.baseline_capture)
        result['baseline_capture_sha256']=prior_digest
        result['catalog_comparison']=compare_catalogs(catalog(prior),result)
    if args.attempts:
        if args.evidence_root is None:parser.error('--attempts requires --evidence-root')
        attempts,attempt_digest=read_capture(args.attempts)
        attach_attempts(result,attempts,args.evidence_root)
        result['attempts_sha256']=attempt_digest
    publish_new(args.out,result)
    print(json.dumps({'exposed_actions':result['exposed_actions'],'executed_actions':0,'output':str(args.out)}))
    return 0


if __name__=='__main__':raise SystemExit(main())
