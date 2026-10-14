# SPDX-License-Identifier: MIT
"""File-only Epic MCP configuration diagnosis. Never edits, starts, stops or contacts the editor."""
import argparse
import hashlib
import json
from pathlib import Path
import re

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
    return {'schema_version':1,'project':str(project),'project_sha256':digest,'plugins':plugins,
            'descriptors':descriptors,'errors':errors,'listener_override_rows':overrides,
            'listener_array_edits':array_edits,'config_sha256':hashlib.sha256(config_raw).hexdigest(),
            'loopback_override_consistent':loopback,'configuration_matches_request':configured,
            'server_ready':None,'editor_queried':False,'mutation':False,
            'scope':'Project/default config and declared dependencies only; merged config, loaded modules and MCP readiness unverified'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--engine',required=True,type=Path)
    args=parser.parse_args(argv)
    result=inspect(args.project,args.engine)
    print(json.dumps(result,indent=2))
    return 0 if result['configuration_matches_request'] else 2


if __name__=='__main__':raise SystemExit(main())
