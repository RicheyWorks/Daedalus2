# SPDX-License-Identifier: MIT
"""Count saved MCP tool descriptions; never connects to a server or executes an action."""
import argparse
import hashlib
import json
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


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(argv)
    capture,digest=read_capture(args.capture)
    result=catalog(capture);result['capture_sha256']=digest
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'exposed_actions':result['exposed_actions'],'executed_actions':0,'output':str(args.out)}))
    return 0


if __name__=='__main__':raise SystemExit(main())
