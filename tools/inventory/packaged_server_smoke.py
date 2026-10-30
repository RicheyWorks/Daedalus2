"""Verify packaged catalog bytes and real loopback production HTTP. No deployment."""
import argparse
import base64
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import urllib.error
import urllib.request
import zipfile

def request(url,token=None):
    headers={'Authorization':'Bearer '+token} if token else {}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=3) as response:
            return response.status,response.read()
    except urllib.error.HTTPError as error:
        return error.code,error.read()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java',required=True);parser.add_argument('--jar',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();jar=args.jar.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2]
    fixtures=sorted((repo/'engines/unreal/DaedalusLink/Content/Inventory').glob('*.dic'))
    expected={'world-zero','gallery-city','parcels','bricks','labyrinth','ocean'}
    if {path.stem for path in fixtures}!=expected:raise RuntimeError('Canonical realm catalog set differs')
    hashes={}
    with zipfile.ZipFile(jar) as boot:
        cores=[name for name in boot.namelist() if name.startswith('BOOT-INF/lib/daedalus-core-') and name.endswith('.jar')]
        if len(cores)!=1:raise RuntimeError('Missing/ambiguous packaged core')
        with zipfile.ZipFile(io.BytesIO(boot.read(cores[0]))) as core:
            for path in fixtures:
                actual=core.read('inventory/'+path.name)
                if actual!=path.read_bytes():raise RuntimeError('Packaged catalog drift: '+path.name)
                hashes[path.name]=hashlib.sha256(actual).hexdigest()
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    key=secrets.token_bytes(32);environment=os.environ.copy()
    environment.update(SPRING_PROFILES_ACTIVE='prod',DAEDALUS_SECURITY_JWT_SECRET=base64.b64encode(key).decode(),
        DAEDALUS_SECURITY_ADMIN_PASSWORD_BCRYPT='$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu')
    base=f'http://127.0.0.1:{port}'
    with (output/'server.log').open('wb') as log:
        process=subprocess.Popen([args.java,'-jar',str(jar),'--server.address=127.0.0.1',f'--server.port={port}',
            '--daedalus.redis.enabled=false','--daedalus.plugins.scan-on-startup=false',
            '--daedalus.security.jwt.issuer=catalog-smoke',
            '--daedalus.world.file='+str(output/'world-zero.daew')],cwd=output,env=environment,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+60
            while True:
                if process.poll() is not None:raise RuntimeError('Packaged server exited; inspect local server.log')
                try:
                    if request(base+'/actuator/health')[0]==200:break
                except (OSError,urllib.error.URLError):pass
                if time.monotonic()>deadline:raise RuntimeError('Packaged server startup timeout')
                time.sleep(.25)
            def encoded(value):return base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).decode().rstrip('=')
            now=int(time.time());unsigned=encoded({'alg':'HS256','typ':'JWT'})+'.'+encoded(
                {'iss':'catalog-smoke','sub':'packaged-smoke-user','iat':now,'exp':now+120})
            token=unsigned+'.'+base64.urlsafe_b64encode(hmac.new(key,unsigned.encode(),hashlib.sha256).digest()).decode().rstrip('=')
            results=[]
            for fixture in fixtures:
                url=base+'/api/v1/inventory/'+fixture.stem+'/catalog'
                if request(url)[0] not in (401,403):raise RuntimeError('Anonymous catalog unexpectedly allowed')
                status,body=request(url,token)
                if status!=200:raise RuntimeError('Authenticated catalog refused: '+fixture.name)
                catalog=json.loads(body)
                if catalog['realm']!=fixture.stem.upper() or not catalog['items']:raise RuntimeError('Wrong realm/empty catalog')
                if any('count' in item or 'quantity' in item for item in catalog['items']):raise RuntimeError('Player quantities exposed')
                results.append({'realm':fixture.stem,'status':status,'item_definitions':len(catalog['items'])})
            status,body=request(base+'/api/v1/inventory/missing/catalog',token)
            if status!=404 or json.loads(body).get('status')!=404:raise RuntimeError('Unknown realm problem detail invalid')
            evidence={'jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),'catalog_hashes':hashes,'http':results,
                'anonymous_refused':True,'unknown_realm_404':True,'scope':'Local packaged production profile; no public deployment or gameplay proof'}
            (output/'proof.json').write_text(json.dumps(evidence,indent=2))
            print(f'PACKAGED_SERVER_PASS {len(fixtures)} byte-identical catalogs, auth HTTP, unknown404')
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)

if __name__=='__main__':main()
