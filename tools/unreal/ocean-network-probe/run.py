"""Two-process localhost transport probe. Fixture must already be built in a scratch host."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

def run(engine, project, output, dive, non_owner=False, keyboard=False, gamepad=False, dock=False, roundtrip=False, exit_key=False, hull_profile=False):
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
    if keyboard: common.append('-ProbeKeyboard')
    if gamepad: common.append('-ProbeGamepad')
    if dock: common.append('-ProbeDock')
    if roundtrip: common.append('-ProbeRoundTrip')
    if exit_key: common.append('-ProbeExitKey')
    if hull_profile: common.append('-ProbeHullProfile')
    if dock: common.append('-ExecCmds=daedalus.Server http://127.0.0.1:9')
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
            marker='OCEAN_REMOTE_ROUNDTRIP_PASS' if roundtrip else 'OCEAN_REMOTE_BOARD_PASS' if dock else 'OCEAN_NETWORK_PASS'
            if marker in log:
                assert client is not None
                client_text=client_log.read_text(errors='replace')
                assert 'Welcomed by server' in client_text,'Missing actual connection evidence'
                if dock:
                    assert 'OCEAN_REMOTE_DOCK_REQUEST' in client_text and 'OCEAN_REMOTE_BOARD_CLIENT_POSSESSION' in client_text
                    if roundtrip: assert 'OCEAN_REMOTE_EXIT_REQUEST' in client_text and 'OCEAN_REMOTE_EXIT_CLIENT_POSSESSION' in client_text
                    if exit_key: assert 'OCEAN_EXIT_KEY_PRESSED' in client_text and 'OCEAN_EXIT_KEY_RELEASED' in client_text
                else:
                    assert 'OCEAN_REPLICATED_IDENTITY' in client_text,'Missing replicated configuration evidence'
                if keyboard:
                    assert 'OCEAN_KEY_INPUT_PRESSED' in client_text and 'OCEAN_KEY_INPUT_RELEASED' in client_text
                if gamepad:
                    assert 'OCEAN_ANALOG_INPUT_STARTED' in client_text and 'OCEAN_ANALOG_INPUT_NEUTRAL' in client_text
                if non_owner:
                    attack_text=attacker_log.read_text(errors='replace')
                    assert 'Welcomed by server' in attack_text
                    assert 'OCEAN_FOREIGN_RPC_ATTEMPT' in attack_text and 'owned=0' in attack_text
                    assert 'No owning connection' in attack_text,'Missing engine refusal evidence'
                return {'mode':mode,'elapsed_seconds':round(time.monotonic()-started,3),
                    'server_pid':server.pid,'client_pid':client.pid,'port':port,
                    **({'foreign_client_pid':attacker.pid} if non_owner else {}),
                    'result':next(line for line in log.splitlines() if marker in line),
                    'replicated_identity':next((line for line in client_text.splitlines() if 'OCEAN_REPLICATED_IDENTITY' in line),None),
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
    parser.add_argument('--non-owner',action='store_true')
    parser.add_argument('--hull-profile',action='store_true')
    inputs=parser.add_mutually_exclusive_group()
    inputs.add_argument('--keyboard',action='store_true');inputs.add_argument('--gamepad',action='store_true')
    inputs.add_argument('--dock',action='store_true')
    parser.add_argument('--roundtrip',action='store_true');parser.add_argument('--exit-key',action='store_true')
    args=parser.parse_args()
    if args.exit_key: args.roundtrip=True
    if args.roundtrip: args.dock=True
    if args.dock and args.non_owner: parser.error('Dock probe currently supports one owner client')
    if args.hull_profile and args.dock: parser.error('Hull-profile probe uses direct vessel possession')
    results=[run(args.engine,args.project,args.output,dive,args.non_owner,args.keyboard,args.gamepad,args.dock,args.roundtrip,args.exit_key,args.hull_profile) for dive in [False,True]]
    for row in results:
        row['server_log_sha256']=hashlib.sha256((args.output/(row['mode']+'-server.log')).read_bytes()).hexdigest()
        row['client_log_sha256']=hashlib.sha256((args.output/(row['mode']+'-client.log')).read_bytes()).hexdigest()
        row['keyboard_dispatch_verified']=args.keyboard
        row['gamepad_axis_dispatch_verified']=args.gamepad
        row['remote_dock_boarding_verified']=args.dock
        row['remote_dock_roundtrip_verified']=args.roundtrip
        row['exit_key_dispatch_verified']=args.exit_key
        if args.hull_profile:
            text=(args.output/(row['mode']+'-client.log')).read_text(errors='replace')
            assert 'OCEAN_HULL_REPLICATED' in text and 'client_resize_refused=1' in text
            assert 'OCEAN_CLIENT_HULL_MUTATION' not in text
            row['hull_profile_replication_verified']=True
        if args.non_owner:
            row['non_owner_refused']=True
            row['foreign_client_log_sha256']=hashlib.sha256((args.output/(row['mode']+'-foreign-client.log')).read_bytes()).hexdigest()
    source=args.project.parent/'Plugins/DaedalusLink/Source/DaedalusLink'
    inputs=['Public/DaedalusOceanTravelComponent.h','Private/DaedalusOceanTravelComponent.cpp',
            'Public/OceanNetworkProbe.h','Private/OceanNetworkProbe.cpp']
    if args.dock:
        inputs+=['Public/DaedalusOceanDock.h','Private/DaedalusOceanDock.cpp',
                 'Public/DaedalusOceanInteractor.h','Private/DaedalusOceanInteractor.cpp',
                 'Public/DaedalusHero.h','Private/DaedalusHero.cpp']
    hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in inputs}
    proof={'passed':results,'owned_children_stopped':True,'compiled_input_sha256':hashes}
    manifest_path=args.project.parent/'source-manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        plugin=args.project.parent/'Plugins/DaedalusLink'
        for name,digest in manifest['files'].items():
            relative=name.removeprefix('engines/unreal/DaedalusLink/')
            assert hashlib.sha256((plugin/relative).read_bytes()).hexdigest()==digest,'Production source overlay'
        proof.update(full_plugin_source_head=manifest['source_head'],production_input_count=len(manifest['files']),
                     declared_test_additions=['Public/OceanNetworkProbe.h','Private/OceanNetworkProbe.cpp'])
    (args.output/'proof.json').write_text(json.dumps(proof,indent=2))
    print(json.dumps(results,indent=2))
