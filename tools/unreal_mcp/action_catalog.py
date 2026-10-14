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
            row={'toolset':toolset,'name':name,'call_name':name.split('.')[-1],
                 'description':prose,'input_schema':schema,'required_parameters':required,
                 'annotations':annotations,'read_only_hint':annotations.get('readOnlyHint'),
                 'execution_state':'not-executed','execution_evidence':None}
            rows.append(row)
            if len(rows)>50000:raise ValueError('Catalog exceeds50000 exposed actions')
    return {'schema_version':1,'exposed_actions':len(rows),'toolsets':len(sets),'per_toolset':counts,
            'actions':rows,'executed_actions':0,'mutation':False,'server_queried':False,
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
        state=attempt.get('state')
        if state not in ('returned','failed','outcome-unknown'):raise ValueError('Unsupported attempt state')
        seconds=attempt.get('elapsed_seconds')
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<0:
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


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--attempts',type=Path,help='optional saved attempt wrapper bound to this capture SHA')
    parser.add_argument('--evidence-root',type=Path,help='required with --attempts; referenced files must remain inside it')
    args=parser.parse_args(argv)
    capture,digest=read_capture(args.capture)
    result=catalog(capture);result['capture_sha256']=digest
    if args.attempts:
        if args.evidence_root is None:parser.error('--attempts requires --evidence-root')
        attempts,attempt_digest=read_capture(args.attempts)
        attach_attempts(result,attempts,args.evidence_root)
        result['attempts_sha256']=attempt_digest
    publish_new(args.out,result)
    print(json.dumps({'exposed_actions':result['exposed_actions'],'executed_actions':0,'output':str(args.out)}))
    return 0


if __name__=='__main__':raise SystemExit(main())
