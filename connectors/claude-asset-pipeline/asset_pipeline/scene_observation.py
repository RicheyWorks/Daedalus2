# SPDX-License-Identifier: MIT
"""Read-only host consumer for Claude Unreal scene schema1. No implicit mutation/retry."""
import argparse
import copy
import json
import math
from pathlib import Path
from . import wire

CONTEXT_KEYS={'session_id','world_path','world_kind','world_epoch'}
VECTOR_FIELDS={'location','rotation','scale'}
TOP_FAILURES={'STALE_CONTEXT','WORLD_UNAVAILABLE','OBSERVATION_UNAVAILABLE'}
MAX_ACTORS=128


class SceneSchemaError(ValueError):
    pass


class SceneContextChanged(ValueError):
    def __init__(self,expected,observed):
        super().__init__('scene context changed; discard earlier observations')
        self.expected=copy.deepcopy(expected);self.observed=copy.deepcopy(observed)


def require(condition,message):
    if not condition:raise SceneSchemaError(message)


def string(value,name,nullable=False,empty=False):
    if nullable and value is None:return
    require(isinstance(value,str) and (empty or bool(value)),name+' must be a string')


def integer(value,name,minimum=0,nullable=False):
    if nullable and value is None:return
    require(type(value) is int and value>=minimum,name+' must be an integer >= '+str(minimum))


def boolean(value,name):
    require(type(value) is bool,name+' must be an explicit boolean')


def finite_number(value):
    if type(value) not in (int,float):return False
    try:return math.isfinite(value)
    except OverflowError:return False


def vector(value,name):
    require(isinstance(value,list) and len(value)==3,name+' must contain three coordinates')
    require(all(finite_number(n) for n in value),name+' coordinates must be finite')


def json_values(value,depth=0,budget=None):
    """Reject opaque/nonfinite diagnostics without rounding or rewriting valid values."""
    if budget is None:budget=[3000000]
    budget[0]-=1
    require(depth<=32 and budget[0]>=0,'observation exceeds nesting/value bounds')
    if isinstance(value,dict):
        require(all(isinstance(key,str) for key in value),'JSON object keys must be strings')
        for item in value.values():json_values(item,depth+1,budget)
    elif isinstance(value,list):
        for item in value:json_values(item,depth+1,budget)
    else:
        require(value is None or type(value) in (str,bool,int,float),'opaque observation value')
        if type(value) in (int,float):require(finite_number(value),'nonfinite observation value')


def context(value,nullable=False):
    if nullable and value is None:return
    require(isinstance(value,dict) and set(value)==CONTEXT_KEYS,'context must preserve all four identity fields')
    for key in CONTEXT_KEYS:string(value[key],'context.'+key)
    require(value['world_kind'] in ('editor','pie'),'unknown world kind')


def errors(values,name):
    require(isinstance(values,list) and len(values)<=128,name+' must be a bounded error list')
    for error in values:
        require(isinstance(error,dict),name+' entries must be objects')
        require('path' in error,name+'.path missing')
        string(error.get('path'),name+'.path',nullable=True)
        string(error.get('code'),name+'.code')
        string(error.get('message'),name+'.message')


def actor(value):
    require(isinstance(value,dict),'actor observation must be an object')
    for field in ('path','class_path','name','class'):string(value.get(field),'actor.'+field)
    for field in ('label','folder'):string(value.get(field),'actor.'+field,empty=True)
    require('parent_path' in value,'actor.parent_path missing')
    string(value.get('parent_path'),'actor.parent_path',nullable=True)
    boolean(value.get('selected'),'actor.selected')
    for field in VECTOR_FIELDS:vector(value.get(field),'actor.'+field)
    bounds=value.get('bounds');require(isinstance(bounds,dict),'actor.bounds missing')
    vector(bounds.get('origin'),'bounds.origin');vector(bounds.get('extent'),'bounds.extent')
    require(all(n>=0 for n in bounds['extent']),'negative bounds extent')
    components=value.get('components')
    require(isinstance(components,list) and len(components)<=128,'components must be bounded')
    paths=[]
    for component in components:
        require(isinstance(component,dict),'component must be an object')
        for field in ('path','name','class'):string(component.get(field),'component.'+field)
        paths.append(component['path'])
        if 'mesh' in component:string(component['mesh'],'component.mesh',nullable=True)
        if 'materials' in component:
            require(isinstance(component['materials'],list) and len(component['materials'])<=128,'material slots must be bounded')
            for material in component['materials']:string(material,'material slot',nullable=True)
    require(len(paths)==len(set(paths)),'duplicate component paths')
    return value


def snapshot(value,requested=None):
    json_values(value)
    require(isinstance(value,dict),'snapshot result must be an object')
    require('context' in value,'snapshot context missing')
    require(type(value.get('schema_version')) is int and value['schema_version']==1,'unsupported scene schema')
    boolean(value.get('available'),'available');context(value.get('context'),nullable=not value['available'])
    scope=value.get('scope');require(isinstance(scope,dict),'scope missing')
    require({'loaded_only','atomic','folder','offset','limit','total_loaded','total_matching','matched_known','returned','complete','next_offset','error_count','errors_truncated'}<=set(scope),'scope fields missing')
    require(scope.get('loaded_only') is True and scope.get('atomic') is False,'schema1 requires loaded-only non-atomic coverage')
    string(scope.get('folder'),'scope.folder',nullable=True,empty=True)
    for field in ('offset','matched_known','returned','error_count'):integer(scope.get(field),'scope.'+field)
    integer(scope.get('limit'),'scope.limit',1);require(scope['limit']<=128,'page limit exceeds128')
    for field in ('total_loaded','total_matching','next_offset'):integer(scope.get(field),'scope.'+field,nullable=True)
    boolean(scope.get('complete'),'scope.complete');boolean(scope.get('errors_truncated'),'scope.errors_truncated')
    rows=value.get('actors');require(isinstance(rows,list) and len(rows)<=scope['limit'],'actors exceed page limit')
    paths=[]
    for row in rows:actor(row);paths.append(row['path'])
    require(paths==sorted(paths) and len(paths)==len(set(paths)),'actor paths must be sorted and unique')
    errors(value.get('errors'),'errors')
    require(scope['returned']==len(rows),'returned count disagrees with observed actors')
    require(scope['error_count']>=len(value['errors']),'error count smaller than diagnostics')
    require(scope['errors_truncated']==(scope['error_count']>len(value['errors'])),'error truncation flag inconsistent')
    if requested is not None:
        for field,default in (('folder',None),('offset',0),('limit',32)):
            require(scope.get(field)==requested.get(field,default),'snapshot response differs from requested '+field)
    if not value['available']:
        require(value.get('code') in TOP_FAILURES and not rows and not scope['complete'],'unavailable snapshot cannot prove scene contents')
    else:
        require(scope['total_loaded'] is not None,'available snapshot lacks enumeration count')
        require(scope['matched_known']<=scope['total_loaded'],'matching paths exceed loaded count')
        if scope['total_matching'] is not None:
            require(scope['total_matching']==scope['matched_known'],'matching counts inconsistent')
        known=scope['matched_known'];end=scope['offset']+min(scope['limit'],max(0,known-scope['offset']))
        require(scope['next_offset']==(end if end<known else None),'pagination cursor inconsistent')
        require(len(rows)<=max(0,min(scope['limit'],known-scope['offset'])),'page has impossible row count')
        complete=(scope['offset']==0 and len(rows)==known and scope['error_count']==0 and scope['total_matching'] is not None)
        require(scope['complete']==complete,'complete flag is not supported by coverage evidence')
    return copy.deepcopy(value)


def verify_request(value):
    json_values(value)
    require(isinstance(value,dict) and type(value.get('schema_version')) is int and value['schema_version']==1,'schema_version1 required')
    context(value.get('context'))
    rows=value.get('actors');require(isinstance(rows,list) and 1<=len(rows)<=128,'verification requires1..128 actor predicates')
    paths=[]
    for row in rows:
        require(isinstance(row,dict) and set(row)=={'path','expected'},'actor predicate requires exact path and expected')
        string(row['path'],'requested path');paths.append(row['path'])
        expected=row['expected']
        require(isinstance(expected,dict) and expected and set(expected)<=VECTOR_FIELDS|{'parent_path','selected','components'},'nonempty supported predicates required')
        for field in VECTOR_FIELDS & set(expected):vector(expected[field],'expected.'+field)
        if 'parent_path' in expected:string(expected['parent_path'],'expected.parent_path',nullable=True)
        if 'selected' in expected:boolean(expected['selected'],'expected.selected')
        if 'components' in expected:
            components=expected['components'];require(isinstance(components,list) and len(components)<=128,'expected components must be bounded')
            component_paths=[]
            for component in components:
                require(isinstance(component,dict) and 'path' in component and set(component)<={'path','mesh','materials'} and len(component)>1,'component predicate requires path and fields')
                string(component['path'],'expected component path');component_paths.append(component['path'])
                if 'mesh' in component:string(component['mesh'],'expected.mesh',nullable=True)
                if 'materials' in component:
                    require(isinstance(component['materials'],list) and len(component['materials'])<=128,'expected materials must be bounded')
                    for material in component['materials']:string(material,'expected material',nullable=True)
            require(len(component_paths)==len(set(component_paths)),'duplicate expected component paths')
    require(len(paths)==len(set(paths)),'duplicate requested actor paths')
    tolerance=value.get('tolerance',{})
    require(isinstance(tolerance,dict) and set(tolerance)<=VECTOR_FIELDS,'unsupported tolerance fields')
    for field,n in tolerance.items():require(finite_number(n) and n>=0,'tolerance must be finite and nonnegative')
    return copy.deepcopy(value)


def predicate_failures(expected,observed,tolerance):
    """Independent readback consistency for the schema1 supported predicates."""
    failed={}
    for field in VECTOR_FIELDS & set(expected):
        differences=[abs(a-b) for a,b in zip(observed[field],expected[field])]
        if field=='rotation':differences=[abs((a-b+180)%360-180) for a,b in zip(observed[field],expected[field])]
        if any(not math.isfinite(n) or n>tolerance.get(field,0) for n in differences):
            failed[field]=(expected[field],observed[field])
    for field in ('parent_path','selected'):
        if field in expected and expected[field]!=observed[field]:failed[field]=(expected[field],observed[field])
    if 'components' in expected:
        actual={item['path']:item for item in observed['components']}
        if not expected['components'] and observed['components']:
            failed['components']=([],observed['components'])
        for component in expected['components']:
            found=actual.get(component['path'])
            for field in ('mesh','materials'):
                if field in component and (found is None or field not in found or component[field]!=found[field]):
                    failed['components.'+component['path']+'.'+field]=(component[field],found.get(field) if found is not None else None)
    return failed


def verification(value,requested):
    request=verify_request(requested)
    json_values(value)
    require(isinstance(value,dict) and 'context' in value,'verification context missing')
    require(isinstance(value,dict) and type(value.get('schema_version')) is int and value['schema_version']==1,'unsupported verification schema')
    boolean(value.get('passed'),'passed');context(value.get('context'),nullable=True)
    checks=value.get('checks');require(isinstance(checks,list) and len(checks)<=128,'checks must be bounded')
    if value.get('code') in TOP_FAILURES:
        require(value['passed'] is False and not checks,'top-level failure cannot contain successful checks')
        return copy.deepcopy(value)
    require(value.get('context')==request['context'],'verification context differs without explicit stale response')
    wanted={row['path']:row['expected'] for row in request['actors']};seen=set()
    for check in checks:
        require(isinstance(check,dict),'check must be an object')
        path=check.get('path');require(path in wanted and path not in seen,'unexpected or duplicate check identity');seen.add(path)
        status=check.get('status');require(status in ('match','mismatch','unavailable'),'unsupported check status')
        mismatches=check.get('mismatches');require(isinstance(mismatches,list),'mismatch diagnostics missing')
        for mismatch in mismatches:
            require(isinstance(mismatch,dict) and {'predicate','expected','observed'}<=set(mismatch),'mismatch must preserve expected and observed values')
            string(mismatch['predicate'],'mismatch predicate')
            if 'code' in mismatch:string(mismatch['code'],'mismatch code')
        if status=='unavailable':
            require(check.get('observed') is None and not mismatches,'unavailable check cannot imply an observed mismatch')
            string(check.get('code'),'unavailable code')
        else:
            observed=actor(check.get('observed'));require(observed['path']==path,'observed identity differs from check')
            require((status=='mismatch')==bool(mismatches),'status contradicts mismatch diagnostics')
            failures=predicate_failures(wanted[path],observed,request.get('tolerance',{}))
            require((status=='mismatch')==bool(failures),'reported status contradicts observed predicates')
            reported={item['predicate']:(item['expected'],item['observed']) for item in mismatches}
            require(len(reported)==len(mismatches) and reported==failures,'mismatch diagnostics contradict requested/observed values')
    require(seen==set(wanted),'verification omitted requested actors')
    require(value['passed']==all(check['status']=='match' for check in checks),'passed flag contradicts explicit checks')
    if 'observation_errors' in value:errors(value['observation_errors'],'observation_errors')
    if 'error_count' in value:
        integer(value['error_count'],'error_count')
        require(value['error_count']>=len(value.get('observation_errors',[])),'observation error count inconsistent')
    if 'errors_truncated' in value:boolean(value['errors_truncated'],'errors_truncated')
    return copy.deepcopy(value)


class SceneClient:
    def __init__(self,addr=wire.UNREAL,timeout=30):
        self.addr=addr;self.timeout=timeout

    def snapshot(self,folder=None,offset=0,limit=32):
        string(folder,'folder',nullable=True,empty=True);integer(offset,'offset');integer(limit,'limit',1)
        require(limit<=128,'limit exceeds128')
        request={'folder':folder,'offset':offset,'limit':limit}
        return snapshot(wire.call(self.addr,'scene_snapshot',timeout=self.timeout,side='Unreal',**request),request)

    def verify(self,request):
        request=verify_request(request)
        return verification(wire.call(self.addr,'scene_verify',timeout=self.timeout,side='Unreal',**request),request)

    def pages(self,folder=None,limit=32,max_pages=32):
        integer(max_pages,'max_pages',1);require(max_pages<=128,'max_pages exceeds128')
        pages=[];seen=set();identity=None;offset=0
        for _ in range(max_pages):
            page=self.snapshot(folder,offset,limit);pages.append(page)
            if not page['available']:break
            if identity is None:identity=page['context']
            elif identity!=page['context']:raise SceneContextChanged(identity,page['context'])
            paths={row['path'] for row in page['actors']}
            require(not seen & paths,'page overlap indicates catalogue drift; do not claim complete coverage')
            seen.update(paths)
            next_offset=page['scope']['next_offset']
            if next_offset is None:break
            require(next_offset>offset,'pagination did not advance');offset=next_offset
        return {'schema_version':1,'context':identity,'pages':pages,'actors_observed':len(seen),
                'available':all(page['available'] for page in pages),
                'complete':len(pages)==1 and pages[0]['scope']['complete'],
                'loaded_only':True,'atomic':False,'stopped_at_page_limit':bool(pages and pages[-1]['scope']['next_offset'] is not None)}


def read_json(path):
    require(path.stat().st_size<=wire.MAX_REPLY_BYTES,'offline observation exceeds byte bound')
    def unique(pairs):
        value={}
        for key,item in pairs:
            require(key not in value,'duplicate JSON field '+key)
            value[key]=item
        return value
    return json.loads(path.read_text(encoding='utf-8-sig'),parse_constant=wire.reject_nonfinite,object_pairs_hook=unique)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('kind',choices=('snapshot','verify'))
    ap.add_argument('--input',type=Path,required=True,help='offline result or bridge envelope JSON')
    ap.add_argument('--request',type=Path,help='original verify request')
    ap.add_argument('--out',type=Path)
    args=ap.parse_args(argv)
    value=read_json(args.input)
    if isinstance(value,dict) and 'status' in value:
        require(value['status']=='ok','transport error envelope is not a scene result');value=value.get('result')
    if args.kind=='verify':
        require(args.request is not None,'--request required for verification')
        request=read_json(args.request)
        result=verification(value,request);code=0 if result['passed'] else 1
    else:
        result=snapshot(value);code=0 if result['available'] else 2
    rendered=json.dumps(result,indent=2,allow_nan=False)
    if args.out:args.out.write_text(rendered,encoding='utf-8')
    print(rendered);return code

if __name__=='__main__':raise SystemExit(main())
