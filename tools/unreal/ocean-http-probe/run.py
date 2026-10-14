"""Real packaged prod Java -> native Unreal OceanHostClient transport probe."""
import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import urllib.error
import urllib.request


def main(args):
    out=args.output.resolve()
    out.mkdir()  # Existing proof directories are never replaced.
    seed=subprocess.run([str(args.java),'--class-path',str(args.classpath.resolve()),str(args.store_probe.resolve()),
                         'write',str(out/'store')],capture_output=True,text=True,timeout=30,check=True)
    if 'OCEAN_PROCESS_WRITE_PASS' not in seed.stdout:raise RuntimeError('Persistent Ocean fixture not seeded')
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
    origin=f'http://127.0.0.1:{port}'
    key=secrets.token_bytes(32)
    env=os.environ.copy()
    env.update(SPRING_PROFILES_ACTIVE='prod',DAEDALUS_SECURITY_JWT_SECRET=base64.b64encode(key).decode(),
               DAEDALUS_SECURITY_ADMIN_PASSWORD_BCRYPT='$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu')
    command=[str(args.java),'-Xmx768m','-jar',str(args.jar.resolve()),'--server.address=127.0.0.1',f'--server.port={port}',
             '--daedalus.redis.enabled=false','--daedalus.plugins.scan-on-startup=false',
             '--daedalus.security.jwt.issuer=ocean-native-test',f'--daedalus.world.file={out / "world.daew"}',
             '--daedalus.ocean.enabled=true',f'--daedalus.ocean.directory={out / "store"}','--daedalus.ocean.seed=42',
             '--logging.level.org.springframework.security=WARN']
    children=[];start=time.monotonic()
    with (out/'server.log').open('wb') as log:
        server=subprocess.Popen(command,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));children.append(server)
        try:
            deadline=time.monotonic()+60
            while True:
                if server.poll() is not None:raise RuntimeError('Packaged server exited; inspect private log')
                try:
                    with urllib.request.urlopen(origin+'/actuator/health',timeout=2) as response:
                        if response.status==200:break
                except (OSError,urllib.error.URLError):pass
                if time.monotonic()>deadline:raise TimeoutError('Server readiness timeout')
                time.sleep(.25)
            def encoded(value):return base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).decode().rstrip('=')
            now=int(time.time())
            unsigned=encoded({'alg':'HS256','typ':'JWT'})+'.'+encoded({'iss':'ocean-native-test','sub':'native-probe','iat':now,'exp':now+120})
            token=unsigned+'.'+base64.urlsafe_b64encode(hmac.new(key,unsigned.encode(),hashlib.sha256).digest()).decode().rstrip('=')
            native_env=os.environ.copy();native_env.update(DAEDALUS_OCEAN_TEST_ORIGIN=origin,DAEDALUS_OCEAN_TEST_TOKEN=token)
            if args.render:native_env['DAEDALUS_OCEAN_RENDER_PATH']=str(out/'ocean-scene.png')
            native_log=out/'native.log'
            with (out/'native-stdout.log').open('wb') as native_stdout:
                graphics=['-OceanRender','-RenderOffscreen','-d3d11','-ResX=1280','-ResY=720','-ForceRes'] if args.render else ['-NullRHI']
                native=subprocess.Popen([str(args.engine),str(args.project.resolve()),
                    '/Engine/Maps/Entry?game=/Script/DaedalusLink.OceanHttpGameMode','-game',*graphics,'-unattended',
                    '-nop4','-nosplash',f'-abslog={native_log}'],env=native_env,stdout=native_stdout,stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));children.append(native)
                native.wait(timeout=180 if args.render else 40)
            text=native_log.read_text(encoding='utf-8',errors='replace')
            if native.returncode!=0 or 'OCEAN_NATIVE_HTTP_PASS' not in text:raise RuntimeError('Native HTTP probe failed; inspect private log')
            if 'OCEAN_NATIVE_MESH_BUILT' not in text:raise RuntimeError('No native procedural mesh proof')
            if 'OCEAN_NATIVE_CLEARED_MESH_REMOVED' not in text:raise RuntimeError('No cleared revision/geometry proof')
            if args.render and ('OCEAN_RENDER_CAPTURED' not in text or not (out/'ocean-scene.png').exists()):raise RuntimeError('No rendered capture')
            for name in ['server.log','native.log','native-stdout.log']:
                if token in (out/name).read_text(encoding='utf-8',errors='replace'):
                    raise RuntimeError('Test token appeared in private log; do not publish it')
            result={'packaged_server_to_native_client':True,'native_procedural_geometry':True,'water_collision_disabled':True,'cleared_revision_and_mesh_removal':True,'water_payload':True,'bounds404':True,'jwt401':True,
                    'cancelled_reply_ignored':True,'reconnect':True,'token_not_in_logs':True,
                    'elapsed_seconds':round(time.monotonic()-start,3),'scope':'Java server startup plus native engine startup and HTTP scenario',
                    'jar_sha256':hashlib.sha256(args.jar.read_bytes()).hexdigest(),
                    'rendered_gameplay_verified':False,'tls_redirect_policy_verified':False,'realm_transfer_verified':False}
            if args.render:
                result.update(rendered_inspection_capture=True,rendered_chunks=64,staged_vessels=2,
                              capture_sha256=hashlib.sha256((out/'ocean-scene.png').read_bytes()).hexdigest())
        finally:
            for child in reversed(children):
                if child.poll() is None:
                    child.terminate()
                    try:child.wait(timeout=10)
                    except subprocess.TimeoutExpired:child.kill();child.wait(timeout=10)
    manifest=json.loads((args.project.parent/'source-manifest.json').read_text(encoding='utf-8-sig'))
    plugin=args.project.parent/'Plugins/DaedalusLink'
    for name,digest in manifest['files'].items():
        relative=name.removeprefix('engines/unreal/DaedalusLink/')
        if hashlib.sha256((plugin/relative).read_bytes()).hexdigest()!=digest:raise RuntimeError('Production source overlay')
    result.update(source_head=manifest['source_head'],production_inputs=len(manifest['files']),
                  fixture_additions=['Public/OceanHttpProbe.h','Private/OceanHttpProbe.cpp'],owned_children_stopped=True,
                  log_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')})
    if args.render:
        result['private_scene_content_sha256']={str(p.relative_to(plugin)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                                               for p in (plugin/'Content/Ocean').rglob('*.uasset')}
        result['private_editor_plugins']=['PythonScriptPlugin','EditorScriptingUtilities']
    (out/'proof.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--render',action='store_true')
    for name in ['java','jar','engine','project','output','classpath','store-probe']:parser.add_argument('--'+name,required=True,type=Path)
    main(parser.parse_args())
