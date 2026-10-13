"""Two-process localhost transport probe. Fixture must already be built in a scratch host."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

def run(engine, project, output, dive, non_owner=False):
    mode='submarine' if dive else 'boat'
    output.mkdir(parents=True,exist_ok=True)
    server_log=output/(mode+'-server.log');client_log=output/(mode+'-client.log')
    for path in [server_log,client_log]:
        if path.exists(): raise RuntimeError('Use a fresh output directory; refusing stale logs')
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    common=['-NullRHI','-unattended','-nop4','-nosplash','-nosound','-NoSteam']
    if dive: common.append('-ProbeDive')
    if non_owner: common.append('-ProbeNonOwner')
    flags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0
    children=[];started=time.monotonic()
    try:
        server=subprocess.Popen([str(engine),str(project),'/Engine/Maps/Entry?game=/Script/DaedalusLink.OceanProbeGameMode',
            '-server','-game','-MULTIHOME=127.0.0.1',f'-port={port}',f'-abslog={server_log}',*common],
            stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT,creationflags=flags)
        children.append(server)
        deadline=started+75
        client=None
        while time.monotonic()<deadline:
            log=server_log.read_text(errors='replace') if server_log.exists() else ''
            if client is None and 'IpNetDriver listening on port' in log:
                client=subprocess.Popen([str(engine),str(project),f'127.0.0.1:{port}','-game',
                    f'-abslog={client_log}',*common],stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT,creationflags=flags)
                children.append(client)
                if non_owner:
                    attacker_log=output/(mode+'-foreign-client.log')
                    if attacker_log.exists(): raise RuntimeError('Stale foreign client log')
                    attacker=subprocess.Popen([str(engine),str(project),f'127.0.0.1:{port}','-game',
                        '-ProbeAttack',f'-abslog={attacker_log}',*common],stdout=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT,creationflags=flags)
                    children.append(attacker)
            if 'OCEAN_NETWORK_PASS' in log:
                assert client is not None
                client_text=client_log.read_text(errors='replace')
                assert 'Welcomed by server' in client_text,'Missing actual connection evidence'
                if non_owner:
                    attack_text=attacker_log.read_text(errors='replace')
                    assert 'Welcomed by server' in attack_text
                    assert 'OCEAN_FOREIGN_RPC_ATTEMPT' in attack_text and 'owned=0' in attack_text
                    assert 'No owning connection' in attack_text,'Missing engine refusal evidence'
                return {'mode':mode,'elapsed_seconds':round(time.monotonic()-started,3),
                    'server_pid':server.pid,'client_pid':client.pid,'port':port,
                    **({'foreign_client_pid':attacker.pid} if non_owner else {}),
                    'result':next(line for line in log.splitlines() if 'OCEAN_NETWORK_PASS' in line),
                    'transport':'localhost Unreal IpNetDriver; actual remote owner RPC',
                    'rendered_gameplay_proven':False}
            if server.poll() is not None: raise RuntimeError(f'Server terminated without pass: {server_log}')
            time.sleep(.25)
        raise TimeoutError(f'No transport pass; inspect {server_log} and {client_log}')
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=10)
                except subprocess.TimeoutExpired: child.kill();child.wait(timeout=10)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('engine',type=Path)
    parser.add_argument('project',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--non-owner',action='store_true');args=parser.parse_args()
    results=[run(args.engine,args.project,args.output,dive,args.non_owner) for dive in [False,True]]
    for row in results:
        row['server_log_sha256']=hashlib.sha256((args.output/(row['mode']+'-server.log')).read_bytes()).hexdigest()
        row['client_log_sha256']=hashlib.sha256((args.output/(row['mode']+'-client.log')).read_bytes()).hexdigest()
        if args.non_owner:
            row['non_owner_refused']=True
            row['foreign_client_log_sha256']=hashlib.sha256((args.output/(row['mode']+'-foreign-client.log')).read_bytes()).hexdigest()
    source=args.project.parent/'Plugins/DaedalusLink/Source/DaedalusLink'
    inputs=['Public/DaedalusOceanTravelComponent.h','Private/DaedalusOceanTravelComponent.cpp',
            'Public/OceanNetworkProbe.h','Private/OceanNetworkProbe.cpp']
    hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in inputs}
    (args.output/'proof.json').write_text(json.dumps({'passed':results,'owned_children_stopped':True,
        'compiled_input_sha256':hashes},indent=2))
    print(json.dumps(results,indent=2))
