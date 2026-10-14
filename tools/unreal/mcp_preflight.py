# SPDX-License-Identifier: MIT
"""File-only Epic MCP configuration diagnosis. Never edits, starts, stops or contacts the editor."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

DESCRIPTORS={
    'ModelContextProtocol':'Experimental/ModelContextProtocol/ModelContextProtocol.uplugin',
    'ToolsetRegistry':'Experimental/ToolsetRegistry/ToolsetRegistry.uplugin',
    'AllToolsets':'Experimental/Toolsets/AllToolsets/AllToolsets.uplugin'}


def document(path):
    with path.open('rb') as stream:raw=stream.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise ValueError('Configuration exceeds8MiB')
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('Duplicate configuration field: '+key)
            value[key]=item
        return value
    def nonfinite(value):raise ValueError('Nonfinite configuration value: '+value)
    value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_constant=nonfinite)
    if not isinstance(value,dict):raise ValueError('Configuration must be an object')
    return value,hashlib.sha256(raw).hexdigest()


def plugin_references(value):
    if not isinstance(value,list):raise ValueError('Plugin references must be an array')
    names=set()
    for row in value:
        if not isinstance(row,dict) or not isinstance(row.get('Name'),str) or not row['Name'] or row['Name'] in names or type(row.get('Enabled')) is not bool:
            raise ValueError('Invalid or duplicate plugin reference')
        names.add(row['Name'])
    return value


def listener_fields(line):
    match=re.fullmatch(r'\+?ListenerOverrides\s*=\s*\(([^)]*)\)\s*(?:;.*)?',line)
    if not match:return None
    fields={}
    for item in match[1].split(','):
        pair=item.split('=',1)
        if len(pair)!=2:return None
        key,value=(part.strip() for part in pair)
        if key in fields:return None
        fields[key]=value.strip('"')
    return fields


def probe_initialization(timeout=5):
    # Reuse the owner's client. No tools/list, tools/call or startup console command.
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from unreal_mcp.client import Mcp,URL
    try:
        client=Mcp(timeout=timeout)
        server=client.server
        valid=(isinstance(server,dict) and isinstance(server.get('protocolVersion'),str) and
               bool(server['protocolVersion']) and isinstance(server.get('capabilities'),dict) and
               isinstance(server.get('serverInfo'),dict) and isinstance(server['serverInfo'].get('name'),str) and
               isinstance(client.sid,str) and bool(client.sid))
        if not valid:raise ValueError('Initialization response/session evidence incomplete')
        return {'initialization_observed':True,'url':URL,'protocol_version':server['protocolVersion'],
                'server_name':server['serverInfo']['name'],'session_id_observed':True,
                'server_metadata_complete':bool(server['serverInfo']['name'] and server['serverInfo'].get('version')),
                'native_tools_called':False,'server_ready':True}
    except Exception as error:
        return {'initialization_observed':False,'url':URL,'server_ready':None,
                'error':{'type':type(error).__name__,'message':str(error)[-1000:]},'native_tools_called':False}


def inspect(project,engine):
    project=project.resolve();engine=engine.resolve()
    data,digest=document(project)
    declarations={}
    for row in plugin_references(data.get('Plugins',[])):
        name=row.get('Name')
        if not isinstance(name,str) or name in declarations or type(row.get('Enabled')) is not bool:
            raise ValueError('Invalid or duplicate project plugin declaration')
        declarations[name]=row['Enabled']
    descriptors={};errors=[]
    for name,relative in DESCRIPTORS.items():
        path=engine/'Engine'/'Plugins'/relative
        try:
            descriptor,sha=document(path)
            descriptors[name]={'path':str(path),'sha256':sha,
                               'declared_dependencies':plugin_references(descriptor.get('Plugins',[]))}
        except (OSError,ValueError) as error:
            errors.append({'plugin':name,'error':str(error)})
    required=descriptors.get('ModelContextProtocol',{}).get('declared_dependencies',[])
    registry_required=any(row.get('Name')=='ToolsetRegistry' and row.get('Enabled') is True for row in required)
    plugins={name:{'explicit_enabled':declarations.get(name),
                   'descriptor_available':name in descriptors} for name in DESCRIPTORS}
    plugins['ToolsetRegistry']['enabled_via_declared_dependency']=registry_required and declarations.get('ModelContextProtocol') is True and declarations.get('ToolsetRegistry') is not False
    config=project.parent/'Config'/'DefaultEngine.ini'
    with config.open('rb') as stream:config_raw=stream.read(8*1024*1024+1)
    if len(config_raw)>8*1024*1024:raise ValueError('INI configuration exceeds8MiB')
    text=config_raw.decode('utf-8-sig');section='';overrides=[];array_edits=[]
    for raw in text.splitlines():
        line=raw.strip()
        if line.startswith((';','#')):continue
        if line.startswith('['):section=line
        elif section=='[HTTPServer.Listeners]' and re.match(r'^[!.-]ListenerOverrides\s*=',line):array_edits.append(line)
        elif section=='[HTTPServer.Listeners]' and re.match(r'^\+?ListenerOverrides\s*=',line):
            if re.search(r'\bPort\s*=\s*8000\b',line):overrides.append(line)
    fields=listener_fields(overrides[0]) if len(overrides)==1 else None
    loopback=(not array_edits and fields is not None and fields.get('Port')=='8000' and
              fields.get('BindAddress')=='127.0.0.1' and fields.get('ReuseAddressAndPort','').lower()=='false')
    configured=(not errors and all(plugins[name]['explicit_enabled'] is True for name in ('ModelContextProtocol','AllToolsets')) and
                (plugins['ToolsetRegistry']['explicit_enabled'] is True or plugins['ToolsetRegistry']['enabled_via_declared_dependency']) and loopback)
    findings=[]
    for name in ('ModelContextProtocol','AllToolsets'):
        if plugins[name]['explicit_enabled'] is not True:
            findings.append({'code':'PLUGIN_NOT_EXPLICITLY_ENABLED','plugin':name,'observed':plugins[name]['explicit_enabled']})
    if plugins['ToolsetRegistry']['explicit_enabled'] is not True and not plugins['ToolsetRegistry']['enabled_via_declared_dependency']:
        findings.append({'code':'TOOLSET_REGISTRY_ENABLE_NOT_ESTABLISHED','plugin':'ToolsetRegistry'})
    if not loopback:
        findings.append({'code':'LOOPBACK_OVERRIDE_NOT_ESTABLISHED','port':8000,
                         'matching_rows':len(overrides),'array_edits':len(array_edits)})
    return {'schema_version':1,'available':not errors,'project':str(project),'project_sha256':digest,'plugins':plugins,
            'status':'configuration-unavailable' if errors else 'configuration-matches' if configured else 'configuration-mismatch','findings':findings,
            'descriptors':descriptors,'errors':errors,'listener_override_rows':overrides,
            'listener_array_edits':array_edits,'config_sha256':hashlib.sha256(config_raw).hexdigest(),
            'loopback_override_consistent':loopback,'configuration_matches_request':configured if not errors else None,
            'server_ready':None,'editor_queried':False,'mutation':False,
            'scope':'Project/default config and declared dependencies only; merged config, loaded modules and MCP readiness unverified'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--engine',required=True,type=Path)
    parser.add_argument('--probe',action='store_true',help='opt-in loopback MCP initialize through the existing client; no native tools')
    args=parser.parse_args(argv)
    try:
        result=inspect(args.project,args.engine)
    except (OSError,ValueError,RecursionError) as error:
        result={'schema_version':1,'available':False,'status':'configuration-unavailable',
                'configuration_matches_request':None,'project':str(args.project),'engine':str(args.engine),
                'errors':[{'code':'CONFIGURATION_UNAVAILABLE' if isinstance(error,OSError) else 'CONFIGURATION_INVALID',
                           'type':type(error).__name__,'message':str(error)[-2000:]}],
                'server_ready':None,'editor_queried':False,'mutation':False,
                'scope':'Unavailable file evidence; no inference about the running editor or MCP server'}
    if args.probe:
        result['probe']=probe_initialization()
        result['server_ready']=result['probe']['server_ready']
    print(json.dumps(result,indent=2))
    return 0 if result['configuration_matches_request'] and (not args.probe or result['server_ready'] is True) else 2


if __name__=='__main__':raise SystemExit(main())
