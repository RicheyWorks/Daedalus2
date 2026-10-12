"""Same-bridge recovery and real initialization helper with wholly fake transports."""
import argparse
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import time
import threading
import types


def load(path):
    spec = importlib.util.spec_from_file_location('recovery_bridge', path)
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    return bridge


def exercise(path, mode):
    import fake_unreal
    sys.modules['unreal'] = fake_unreal
    bridge = load(path)
    witnesses, dispatches, stops = [], [], []
    fake_unreal.LOGDIR = str(path.parent)
    fake_unreal.GAME_THREAD[0] = threading.get_ident()
    fake_unreal.RECOVERY_WITNESS = witnesses

    class Transport:
        def run_command(self, command, **kwargs):
            dispatches.append(command)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(command, {'unreal': fake_unreal})
            lines = output.getvalue().splitlines()
            if len(dispatches) == 1:
                if mode == 'lost_reply':
                    raise ConnectionError('fixture lost reply after execution')
                if mode == 'malformed_marker':
                    lines = [line.rsplit(':', 1)[0]+':{' if line.startswith(bridge.RESULT_MARK) else line for line in lines]
                if mode == 'missing_marker':
                    lines = [line for line in lines if not line.startswith(bridge.RESULT_MARK)]
            return {'command': 'foreign' if mode == 'invalid_echo' and len(dispatches) == 1 else command,
                    'success': True, 'result': 'None', 'output': [{'output': line} for line in lines]}
        def stop(self):
            stops.append('stop')

    def node(want, request_deadline=None):
        if bridge._remote['rx'] is None:
            bridge._remote.update(rx=Transport(), node='fixture')
        return bridge._remote['rx'], 'fixture'

    bridge._remote_node = node
    replies = []
    for owner in ('FIRST', 'NEXT'):
        gen = bridge.cmd_execute_python({'code': "unreal.RECOVERY_WITNESS.append(%r)\nresult = %r" % (owner, owner), 'timeout': 2})
        try:
            while True:
                next(gen)
                time.sleep(.001)
        except StopIteration as done:
            replies.append({'status': 'ok', 'result': done.value})
        except Exception as error:
            replies.append({'status': 'error', 'error': str(error)})
    passed = (witnesses == ['FIRST', 'NEXT'] and len(dispatches) == 2 and
              replies[0]['status'] == 'error' and replies[1]['status'] == 'ok' and
              replies[1]['result']['result'] == 'NEXT')
    return {'case': mode+'_then_valid_same_bridge', 'passed': passed, 'execution_witness': witnesses,
            'dispatch_count': len(dispatches), 'stops': len(stops), 'replies': replies}


def initialization(path, mode):
    bridge = load(path)
    witness = []
    class Transport:
        remote_nodes = [{'project_root': 'fixture', 'node_id': 'fixture'}]
        def start(self):
            witness.append('start')
            if mode == 'start_failure':
                raise RuntimeError('fixture start failure')
        def open_command_connection(self, node):
            witness.append('open')
            raise RuntimeError('fixture open failure')
        def stop(self):
            witness.append('stop')
    prior = sys.modules.get('remote_execution')
    sys.modules['remote_execution'] = types.SimpleNamespace(RemoteExecution=Transport)
    error = None
    try:
        bridge._remote_node('fixture')
    except Exception as exc:
        error = str(exc)
    finally:
        if prior is None:
            sys.modules.pop('remote_execution', None)
        else:
            sys.modules['remote_execution'] = prior
    return {'case': mode, 'passed': bool(error) and witness.count('stop') == 1 and bridge._remote['rx'] is None,
            'lifecycle_witness': witness, 'error': error, 'real_network_calls': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bridge', type=pathlib.Path, required=True)
    parser.add_argument('--connector-root', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.connector_root/'tests'))
    import fake_unreal
    sys.modules['unreal'] = fake_unreal
    rows = [exercise(args.bridge, mode) for mode in ('invalid_echo', 'lost_reply', 'malformed_marker', 'missing_marker')]
    rows += [initialization(args.bridge, mode) for mode in ('start_failure', 'open_failure')]
    report = {'environment': 'fake transports, no editor or Epic sockets', 'passed': sum(row['passed'] for row in rows), 'total': len(rows), 'cases': rows}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
