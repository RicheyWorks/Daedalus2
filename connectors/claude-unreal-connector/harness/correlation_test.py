"""Offline bridge callers + installed Epic client + local fake peer. Never contacts Unreal."""
import argparse
import concurrent.futures
import contextlib
import importlib.util
import io
import json
import pathlib
import socket
import sys
import tempfile
import threading
import time
import types


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exercise(bridge_path, connector, epic_path, mode):
    sys.path.insert(0, str(connector / 'tests'))
    import fake_unreal
    sys.modules['unreal'] = fake_unreal
    fake_unreal.LOGDIR = tempfile.gettempdir()
    fake_unreal.REMOTE_WITNESS = []
    bridge = load('correlation_bridge', bridge_path)
    epic = load('installed_epic_client', epic_path)
    client_sock, peer_sock = socket.socketpair()
    for sock in (client_sock, peer_sock):
        sock.settimeout(3)
    a_sent, b_sent = threading.Event(), threading.Event()
    a_received, b_received = threading.Event(), threading.Event()
    witness, peer_errors, initializations = [], [], []
    b_executed = threading.Event()
    local = threading.local()

    class Channel:
        def sendall(self, data):
            command = json.loads(data)['data']['command']
            local.owner = 'OWNER_A' if 'OWNER_A' in command else 'OWNER_B'
            client_sock.sendall(data)
            (a_sent if local.owner == 'OWNER_A' else b_sent).set()
        def recv(self, size):
            # Adversarial but legal schedule: B receives A's result first when two
            # callers concurrently use the same uncorrelated Epic socket.
            if mode == 'concurrent_swap' and local.owner == 'OWNER_A' and b_sent.wait(.15):
                if not b_received.wait(2):
                    raise TimeoutError('fixture B receiver did not finish')
            data = client_sock.recv(size)
            (a_received if local.owner == 'OWNER_A' else b_received).set()
            return data
        def close(self):
            client_sock.close()

    connection = epic._RemoteExecutionCommandConnection.__new__(epic._RemoteExecutionCommandConnection)
    connection._node_id = 'fixture-client'
    connection._remote_node_id = 'fixture-editor'
    connection._command_channel_socket = Channel()
    connection._command_listen_socket = None
    rx = epic.RemoteExecution()
    rx._command_connection = connection
    rx._broadcast_connection = types.SimpleNamespace(broadcast_close_connection=lambda node: None, close=lambda: None)
    bridge._remote.update(rx=rx, node='fixture-editor', error=None)
    if mode in ('remote_unavailable', 'fallback_deadline', 'discovery_deadline'):
        def unavailable(want, request_deadline=None):
            if mode == 'discovery_deadline':
                time.sleep(.05)
            elif mode == 'fallback_deadline':
                time.sleep(.005)  # Finish before budget but after the first generator yield.
            return None
        bridge._remote_node = unavailable
        bridge._remote['error'] = 'fixture Remote Execution off before dispatch'
    elif mode == 'initialization_race':
        bridge._remote.update(rx=None, node=None)
        def initialize(want, request_deadline=None):
            if bridge._remote['rx'] is None:
                time.sleep(.04)  # Simulate discovery/open while a second caller arrives.
                initializations.append(threading.get_ident())
                bridge._remote.update(rx=rx, node='fixture-editor')
            return bridge._remote['rx'], bridge._remote['node']
        bridge._remote_node = initialize

    def peer():
        decoder, pending = json.JSONDecoder(), ''
        try:
            while True:
                part = peer_sock.recv(65536)
                if not part:
                    return
                pending += part.decode()
                while pending:
                    try:
                        message, used = decoder.raw_decode(pending)
                    except json.JSONDecodeError:
                        break
                    pending = pending[used:].lstrip()
                    command = message['data']['command']
                    owner = 'OWNER_A' if 'OWNER_A' in command else 'OWNER_B'
                    witness.append({'owner': owner, 'unattended': message['data']['unattended']})
                    buffer, error = io.StringIO(), None
                    with contextlib.redirect_stdout(buffer):
                        try:
                            exec(compile(command, '<fixture-remote>', 'exec'), {'unreal': fake_unreal})
                        except Exception as exc:
                            error = f'{type(exc).__name__}: {exc}'
                    output = [{'type': 'Info', 'output': line} for line in buffer.getvalue().splitlines()]
                    response_type = 'command_result'
                    if mode == 'foreign_marker':
                        output = [{'type': 'Info', 'output': bridge.RESULT_MARK+json.dumps({'caller': 'FOREIGN'})}]
                    elif mode == 'extra_foreign_marker':
                        output.append({'type': 'Info', 'output': bridge.RESULT_MARK+json.dumps({'caller': 'FOREIGN'})})
                    elif mode == 'missing_marker':
                        output = [entry for entry in output if not entry['output'].startswith(bridge.RESULT_MARK)]
                    elif mode == 'duplicate_marker':
                        output += [entry for entry in output if entry['output'].startswith(bridge.RESULT_MARK)]
                    elif mode == 'transport_error_after_execution':
                        response_type = 'unexpected_response'
                    if owner == 'OWNER_B':
                        b_executed.set()
                    if mode == 'concurrent_swap' and owner == 'OWNER_B' and not a_received.is_set():
                        if not b_received.wait(2):
                            raise TimeoutError('fixture A result was not consumed by B')
                    reply = {'success': error is None, 'command': command, 'result': error or 'None', 'output': output}
                    if mode == 'foreign_echo':
                        reply['command'] = 'a different caller command'
                    elif mode == 'missing_echo':
                        reply.pop('command')
                    peer_sock.sendall(epic._RemoteExecutionMessage(response_type, 'fixture-editor',
                                                                 'fixture-client', reply).to_json_bytes())
        except (OSError, TimeoutError) as exc:
            if not ending.is_set():
                peer_errors.append(repr(exc))
    ending, tick_stop = threading.Event(), threading.Event()
    peer_thread = threading.Thread(target=peer, daemon=True)
    peer_thread.start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    bridge.start(port, register_tick=False)
    def tick():
        fake_unreal.GAME_THREAD[0] = threading.get_ident()
        while not tick_stop.is_set():
            bridge.pump()
            tick_stop.wait(.06 if mode in ('fallback_deadline', 'discovery_deadline') else .005)
    tick_thread = threading.Thread(target=tick, daemon=True)
    tick_thread.start()
    calls = 0
    def caller(owner):
        nonlocal calls
        calls += 1
        code = f"unreal.REMOTE_WITNESS.append('{owner}')\nprint('stdout-{owner}')\nresult = {{'caller': '{owner}'}}"
        if mode == 'contention_deadline' and owner == 'OWNER_A':
            code = 'import time\ntime.sleep(.25)\n'+code
        if mode == 'user_exception':
            code += "\nraise ValueError('fixture user failure')"
        timeout = .04 if mode == 'contention_deadline' and owner == 'OWNER_B' else 2
        if mode in ('fallback_deadline', 'discovery_deadline'):
            timeout = .03
        payload = {'id': owner, 'type': 'execute_python', 'params': {'code': code, 'timeout': timeout, 'bridge_timeout': 3}}
        with socket.create_connection(('127.0.0.1', port), timeout=4) as sock:
            sock.sendall((json.dumps(payload)+'\n').encode())
            data = b''
            while b'\n' not in data:
                chunk = sock.recv(65536)
                if not chunk:
                    raise ConnectionError('fixture bridge closed without reply')
                data += chunk
        reply = json.loads(data.split(b'\n', 1)[0])
        assert reply['id'] == owner
        return reply
    start = time.perf_counter()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(caller, 'OWNER_A')
            if mode in ('concurrent_swap', 'initialization_race', 'contention_deadline'):
                if mode != 'initialization_race' and not a_sent.wait(2):
                    raise TimeoutError('fixture first remote dispatch did not start')
                second = pool.submit(caller, 'OWNER_B')
                replies = {'OWNER_A': first.result(4), 'OWNER_B': second.result(4)}
                if mode == 'contention_deadline' and b_sent.is_set():
                    b_executed.wait(1)
            else:
                replies = {'OWNER_A': first.result(4)}
        executions = list(fake_unreal.REMOTE_WITNESS)
        success_modes = {'normal', 'concurrent_swap', 'initialization_race', 'contention_deadline',
                         'extra_foreign_marker', 'remote_unavailable'}
        passed = not peer_errors
        for owner, reply in replies.items():
            expires_waiting = mode == 'contention_deadline' and owner == 'OWNER_B'
            expires_waiting = expires_waiting or mode in ('fallback_deadline', 'discovery_deadline')
            expected_success = mode in success_modes and not expires_waiting
            passed = passed and executions.count(owner) == (0 if expires_waiting else 1)
            if expected_success:
                passed = passed and reply.get('status') == 'ok'
                result = reply.get('result') or {}
                passed = passed and result.get('result') == {'caller': owner}
                passed = passed and 'stdout-'+owner in result.get('stdout', '')
                if mode == 'remote_unavailable':
                    passed = passed and not result.get('unattended') and len(witness) == 0
                else:
                    passed = passed and result.get('unattended') is True
            else:
                passed = passed and reply.get('status') == 'error'
        if mode == 'initialization_race':
            passed = passed and len(initializations) == 1
        return {'case': mode, 'classification': 'tested-pass' if passed else 'reproduced-fail',
                'time_to_verified_result_s': time.perf_counter()-start, 'bridge_requests': calls,
                'retries': 0, 'manual_interventions': 0, 'executed_owners': executions,
                'remote_dispatch_witness': witness, 'replies': replies, 'fixture_errors': peer_errors,
                'initialization_count': len(initializations)}
    finally:
        ending.set()
        tick_stop.set()
        tick_thread.join(2)
        bridge.stop()  # Only this disposable bridge, not the user's editor.
        client_sock.close()
        peer_sock.close()
        peer_thread.join(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bridge', type=pathlib.Path, required=True)
    parser.add_argument('--connector-root', type=pathlib.Path, required=True)
    parser.add_argument('--epic-client', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    rows = [exercise(args.bridge, args.connector_root, args.epic_client, mode) for mode in
            ('normal', 'concurrent_swap', 'initialization_race', 'contention_deadline',
             'foreign_echo', 'missing_echo', 'foreign_marker', 'extra_foreign_marker', 'missing_marker',
             'duplicate_marker', 'transport_error_after_execution', 'remote_unavailable', 'user_exception',
             'fallback_deadline', 'discovery_deadline')]
    report = {'environment': 'installed Epic client with disposable local fake peer and fake Unreal; no editor',
              'bridge': str(args.bridge), 'epic_client': str(args.epic_client),
              'passed': sum(r['classification'] == 'tested-pass' for r in rows), 'total': len(rows), 'cases': rows}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    for row in rows:
        print(json.dumps({k: v for k, v in row.items() if k != 'replies'}))
    print(f'{report["passed"]}/{report["total"]}')
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
