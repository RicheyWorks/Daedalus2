"""Observe real Unreal redirect payload handling; never record the fresh probe credential."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import threading
import time


def scenario(engine, project, output, mode, expected):
    output.mkdir()
    token=secrets.token_hex(24)
    observations=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            landed=mode=='direct' or self.path=='/landed' or self.path.startswith('/API/')
            observations.append({'landed':landed,'port':self.server.server_port,
                'authorization_present':bool(self.headers.get('Authorization')),
                'credential_match':self.headers.get('Authorization')=='Bearer '+token})
            if landed:
                body=json.dumps(dict(x=0,y=0,z=0,revision=0,present=False,data='',palette=['AIR'])).encode()
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            else:
                destination=target.server_port if mode=='cross-origin-port' else origin.server_port
                path=self.path.replace('/api/','/API/',1) if mode=='same-origin-case' else '/landed'
                self.send_response(302);self.send_header('Location',f'http://127.0.0.1:{destination}{path}')
                self.send_header('Content-Length','0');self.end_headers()
    origin=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    target=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threads=[]
    for server in [origin,target]:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();threads.append(thread)
    env=os.environ.copy();env.update(DAEDALUS_REDIRECT_ORIGIN=f'http://127.0.0.1:{origin.server_port}',DAEDALUS_REDIRECT_TOKEN=token)
    log=output/'native.log';start=time.monotonic()
    child=None
    try:
        with (output/'stdout.log').open('wb') as stdout:
            child=subprocess.Popen([str(engine),str(project),'/Engine/Maps/Entry?game=/Script/DaedalusLink.OceanRedirectGameMode',
                '-game','-NullRHI','-unattended','-nop4','-nosplash',f'-abslog={log}'],env=env,stdout=stdout,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            child.wait(timeout=45)
        text=log.read_text(encoding='utf-8-sig',errors='replace')
        if child.returncode!=0:raise RuntimeError('Native probe process failed')
        marker='OCEAN_REDIRECT_PAYLOAD_'+expected.upper()
        if marker not in text:raise RuntimeError('Unexpected redirect behavior; inspect private native log')
        if token in text or token in (output/'stdout.log').read_text(encoding='utf-8',errors='replace'):
            raise RuntimeError('Probe credential appeared in native log')
        entered=[row for row in observations if not row['landed']]
        landed=[row for row in observations if row['landed']]
        if len(entered)!=(0 if mode=='direct' else 1) or len(landed)!=1 \
                or not (landed[0]['credential_match'] if mode=='direct' else entered[0]['credential_match']):
            raise RuntimeError('Redirect endpoint sequence not observed')
        return {'mode':mode,
            'elapsed_seconds':round(time.monotonic()-start,3),'observed':expected,
            'redirect_target_contacted':mode!='direct','authorization_at_target':landed[0]['authorization_present'],
            'probe_credential_at_target':landed[0]['credential_match'],'token_absent_from_logs':True,
            'native_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
    finally:
        if child and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=10)
        origin.shutdown();target.shutdown();origin.server_close();target.server_close()
        for thread in threads:thread.join(timeout=2)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['engine','project','output']:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--expect',required=True,choices=['accepted','refused'])
    a=p.parse_args()
    plugin=a.project.parent/'Plugins/DaedalusLink'
    manifest=json.loads((a.project.parent/'source-manifest.json').read_text(encoding='utf-8'))
    prefix='engines/unreal/DaedalusLink/'
    for name,digest in manifest['files'].items():
        source=plugin/name.removeprefix(prefix)
        if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Production source differs from recorded build input: '+name)
    fixture_files=['Public/OceanRedirectProbe.h','Private/OceanRedirectProbe.cpp']
    expected={name.removeprefix(prefix+'Source/DaedalusLink/') for name in manifest['files']
              if name.startswith(prefix+'Source/DaedalusLink/')}
    actual={str(path.relative_to(plugin/'Source/DaedalusLink')).replace('\\','/')
            for path in (plugin/'Source/DaedalusLink').rglob('*') if path.is_file()}
    if actual != expected | set(fixture_files):
        raise RuntimeError('Undeclared or missing probe source additions')
    a.output.mkdir()
    modes=['direct','same-origin-path','cross-origin-port','same-origin-case']
    rows=[scenario(a.engine,a.project.resolve(),a.output/mode,mode,'accepted' if mode=='direct' else a.expect) for mode in modes]
    proof={'scope':'Actual UE loopback redirects; no TLS or pre-forward prevention claim','cases':rows,
        'baseline_defect_demonstration':a.expect=='accepted','owned_children_stopped':True,
        'production_source_head':manifest['source_head'],
        'declared_fixture_additions':fixture_files,
        'fixture_source_sha256':{name:hashlib.sha256((plugin/'Source/DaedalusLink'/name).read_bytes()).hexdigest()
                                 for name in fixture_files},
        'client_source_sha256':hashlib.sha256((plugin/'Source/DaedalusLink/Private/DaedalusOceanHostClient.cpp').read_bytes()).hexdigest(),
        'module_sha256':hashlib.sha256((plugin/'Binaries/Win64/UnrealEditor-DaedalusLink.dll').read_bytes()).hexdigest()}
    (a.output/'proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(proof,indent=2))
