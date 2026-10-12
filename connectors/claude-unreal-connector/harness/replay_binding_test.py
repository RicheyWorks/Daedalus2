"""Retry/replay tests on a disposable bridge with independent execution witnesses."""
import argparse
import importlib.util
import json
import pathlib
import socket
import sys
import threading
import time



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bridge', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--connector-root', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    sys.path.insert(0, str(args.connector_root / 'tests'))
    sys.path.insert(0, str(args.connector_root))
    import fake_unreal
    sys.modules['unreal'] = fake_unreal
    spec = importlib.util.spec_from_file_location('fixture_bridge', args.bridge)
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    executions = {}
    def slow(params):
        key = params['key']
        executions[key] = executions.get(key, 0) + 1
        for _ in range(30):
            yield
        if params.get('fail'):
            raise ValueError('deliberate fixture failure')
        return {'key': key, 'runs': executions[key]}
    bridge.register('sol.slow', slow, 'Disposable yielding operation with execution witness')
    bridge.register('sol.inspect', lambda p: dict(executions), 'Independent counter witness', risk='READ')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    bridge.start(port, register_tick=False)
    stop = threading.Event()
    paused = threading.Event()
    def tick():
        fake_unreal.GAME_THREAD[0] = threading.get_ident()
        while not stop.is_set():
            if not paused.is_set():
                bridge.pump()
            stop.wait(.01)
    thread = threading.Thread(target=tick, daemon=True)
    thread.start()
    calls = 0
    def request(command, params=None, timeout=2):
        nonlocal calls
        calls += 1
        payload = {'id': calls, 'type': command,
                   'params': dict({'bridge_timeout': timeout}, **(params or {}))}
        with socket.create_connection(('127.0.0.1', port), timeout=timeout+5) as conn:
            conn.sendall((json.dumps(payload)+'\n').encode())
            data = b''
            while b'\n' not in data:
                chunk = conn.recv(65536)
                if not chunk:
                    raise ConnectionError('fixture closed without reply')
                data += chunk
        response = json.loads(data.split(b'\n', 1)[0])
        assert response['id'] == payload['id'], 'wire response id did not match request'
        return response
    def wait_jobs(jobs):
        last = []
        deadline = time.monotonic()+2
        while time.monotonic() < deadline:
            last = [request('job_result', {'job_id': j}) for j in jobs]
            if all(r.get('result', {}).get('state') == 'done' for r in last):
                return [r['result']['reply'] for r in last]
            time.sleep(.02)
        raise TimeoutError('fixture jobs failed to finish')
    rows = []
    def record(name, passed, start, before, witness, detail):
        rows.append({'case': name, 'classification': 'tested-pass' if passed else 'reproduced-fail',
                     'time_to_verified_result_s': time.perf_counter()-start,
                     'bridge_requests': calls-before, 'manual_interventions': 0,
                     'execution_witness': witness, 'detail': detail})
        print(json.dumps(rows[-1]))
    try:
        request('sol.inspect')  # Warm up resolver/transport outside timed trials.
        paused.set()
        time.sleep(.02)
        start, before = time.perf_counter(), calls
        expired = request('sol.slow', {'key': 'expired_queue'}, timeout=.04)
        paused.clear()
        witness = request('sol.inspect')['result']
        record('expired_queued_command_never_starts', expired['status'] == 'error'
               and witness.get('expired_queue', 0) == 0, start, before, witness,
               {'reply': expired, 'retry_count': 0})
        start, before = time.perf_counter(), calls
        first = request('sol.slow', {'key': 'retry', 'request_id': 'retry-key'}, timeout=.04)
        second = request('sol.slow', {'key': 'retry', 'request_id': 'retry-key'})
        witness = request('sol.inspect')['result']
        record('retry_while_generator_running', first['status'] == 'error' and second['status'] == 'ok'
               and witness.get('retry') == 1 and second.get('replayed') is True,
               start, before, witness, {'first': first, 'retry': second, 'retry_count': 1})
        start, before = time.perf_counter(), calls
        runs_before_replay = witness.get('retry')
        again = request('sol.slow', {'key': 'retry', 'request_id': 'retry-key'})
        witness = request('sol.inspect')['result']
        record('completed_replay', again.get('replayed') is True and witness.get('retry') == runs_before_replay,
               start, before, witness, again)
        for name, fail in [('async_same_key', False), ('async_failure_followers', True)]:
            start, before = time.perf_counter(), calls
            replies = [request('sol.slow', {'key': name, 'request_id': name, 'async': True, 'fail': fail})
                       for _ in range(2)]
            jobs = [r['result']['job_id'] for r in replies]
            finished = wait_jobs(jobs)
            witness = request('sol.inspect')['result']
            expected = 'error' if fail else 'ok'
            record(name, witness.get(name) == 1 and all(r['status'] == expected for r in finished)
                   and finished[1].get('replayed') is True
                   and [r['id'] for r in finished] == [r['id'] for r in replies],
                   start, before, witness,
                   {'jobs': jobs, 'replies': finished, 'retry_count': 1})
        start, before = time.perf_counter(), calls
        failures_before = witness['async_failure_followers']
        failed_retry = request('sol.slow', {'key': 'async_failure_followers',
                                          'request_id': 'async_failure_followers', 'fail': True})
        witness = request('sol.inspect')['result']
        record('completed_failure_allows_new_attempt', failed_retry['status'] == 'error'
               and witness['async_failure_followers'] == failures_before+1, start, before, witness,
               {'reply': failed_retry, 'retry_count': 1})
        start, before = time.perf_counter(), calls
        replies = [request('sol.slow', {'key': 'distinct', 'request_id': 'distinct-'+str(i), 'async': True})
                   for i in range(2)]
        finished = wait_jobs([r['result']['job_id'] for r in replies])
        witness = request('sol.inspect')['result']
        record('distinct_keys_execute_independently', witness.get('distinct') == 2
               and all(r['status'] == 'ok' for r in finished)
               and [r['id'] for r in finished] == [r['id'] for r in replies], start, before, witness,
               {'replies': finished, 'retry_count': 0})
    finally:
        stop.set()
        thread.join(2)
        bridge.stop()  # Disposable fixture only, never the editor's bridge.
    report = {'environment': 'stand-in disposable TCP bridge; no Unreal editor', 'bridge': args.bridge,
              'passed': sum(r['classification'] == 'tested-pass' for r in rows), 'total': len(rows), 'cases': rows}
    pathlib.Path(args.output).write_text(json.dumps(report, indent=2)+'\n')
    print(f'{report["passed"]}/{report["total"]}')
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
