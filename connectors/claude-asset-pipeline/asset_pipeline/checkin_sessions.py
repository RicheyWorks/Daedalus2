"""Explicit offline init/advance/show over completed retained check-in inputs.

Generations contain all assignment states and committed advice together. CURRENT
is replaced only after the exclusive generation file is flushed and fsynced.
An interrupted generation or writer marker requires reconciliation, never an
automatic retry, promotion, stale-lock removal or external action. show reports
stored advice as committed data; it never produces a new recommendation.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from . import retained_checkins as retained
from . import team_checkins as reducer

SCHEMA = 'daedalus.checkin-session.v1'
MAX_BYTES = 64 * 1024 * 1024
MAX_STATES = 64
MAX_MESSAGES = 50000


class SessionError(ValueError):
    pass


def _need(ok, message):
    if not ok:
        raise SessionError(message)


def _clock(value):
    _need(isinstance(value, str), 'explicit UTC clock required')
    match = re.fullmatch(r'([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})'
                         r'(?:\.([0-9]{1,9}))?(?:Z|\+00:00)', value)
    _need(match is not None, 'canonical UTC clock with at most nine fraction digits required')
    return reducer.utc(match[1] + '+00:00'), int((match[2] or '0').ljust(9, '0'))


def _compatible_clock(value):
    """Equivalent call-boundary spelling for frozen Python3.10 validators."""
    _clock(value)
    match = re.fullmatch(r'(.{19})\.([0-9]+)(Z|\+00:00)', value)
    if match and len(match[2]) in (1, 2, 4, 5):
        return match[1] + '.' + match[2].ljust(6, '0') + match[3]
    return value


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _hex(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _label(value):
    _need(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value),
          'invalid prepared label')
    _need(value.upper() not in {'CON', 'PRN', 'AUX', 'NUL'} and
          not re.fullmatch(r'(COM|LPT)[1-9]', value.upper()), 'reserved prepared label')
    return value


def _inputs(directory):
    """Freeze every selected file before any session mutation."""
    root = Path(directory)
    _need(stat.S_ISDIR(root.lstat().st_mode), 'prepared input must be a directory, not a link')
    pins, total = {}, 0
    def read(name):
        nonlocal total
        raw, pin = retained._copy(root / name, MAX_BYTES)
        total += len(raw)
        _need(total <= MAX_BYTES, 'prepared input byte limit exceeded')
        pins[name] = pin
        return retained._json(raw, name)
    manifest = read('manifest.json')
    _need(isinstance(manifest, dict) and manifest.get('schema') == 'daedalus.retained-checkins-inputs.v1',
          'completed retained-input manifest required')
    _need(set(manifest) == {'schema', 'source_sha256', 'selection_sha256', 'source_bytes', 'records',
          'observed_at_utc', 'event_clock_policy', 'assignments', 'unqualified_records',
          'automatic_send', 'automatic_assignment'}, 'incomplete/unsupported retained manifest')
    _need(manifest.get('automatic_send') is False and manifest.get('automatic_assignment') is False,
          'prepared inputs must keep automatic actions disabled')
    _need(_hex(manifest.get('source_sha256')) and _hex(manifest.get('selection_sha256')), 'invalid source pins')
    _need(type(manifest['source_bytes']) is int and 0 < manifest['source_bytes'] <= retained.MAX_SOURCE_BYTES,
          'invalid retained source byte count')
    _need(isinstance(manifest['event_clock_policy'], str) and isinstance(manifest['unqualified_records'], list),
          'invalid retained diagnostics/clock policy')
    _clock(manifest.get('observed_at_utc'))
    rows = manifest.get('assignments')
    _need(isinstance(rows, list) and 1 <= len(rows) <= MAX_STATES, 'prepared assignment count exceeded')
    _need(type(manifest.get('records')) is int and 1 <= manifest['records'] <= retained.MAX_RECORDS,
          'invalid prepared record count')
    selected, labels, messages, common_snapshot, broker = [], set(), None, None, {}
    for row in rows:
        _need(isinstance(row, dict) and set(row) == {'label', 'message_id', 'start_deadline_utc',
              'checkpoint_seconds', 'assignment', 'snapshot', 'assignment_sha256'},
              'invalid prepared assignment entry')
        label = _label(row.get('label'))
        _need(label.casefold() not in labels, 'duplicate prepared label')
        labels.add(label.casefold())
        _need(row.get('assignment') == 'assignment.json' and row.get('snapshot') == 'snapshot.json',
              'unsupported prepared filenames')
        _need(stat.S_ISDIR((root / label).lstat().st_mode), 'prepared label must be a directory, not a link')
        assignment = read(label + '/assignment.json')
        snapshot = read(label + '/snapshot.json')
        _need(isinstance(assignment, dict), 'assignment envelope required')
        retained._envelope(assignment, 1)
        _need(assignment.get('type') in {'ping', 'task.assign'} and isinstance(assignment['body'], dict),
              'unsupported/unstructured assignment envelope')
        key = reducer.digest(assignment)
        _need(key == row.get('assignment_sha256') and assignment['id'] == reducer.positive(row.get('message_id')),
              'prepared assignment identity mismatch')
        initial = reducer.create(assignment, _compatible_clock(row['start_deadline_utc']), row['checkpoint_seconds'])
        initial['deadline_utc'] = row['start_deadline_utc']
        _need(isinstance(snapshot, dict) and set(snapshot) == {'observed_at_utc', 'messages'}, 'invalid snapshot')
        _need(snapshot['observed_at_utc'] == manifest['observed_at_utc'], 'snapshot observation differs from manifest')
        records = snapshot['messages']
        _need(isinstance(records, list) and len(records) == manifest['records'], 'snapshot record count mismatch')
        snapshot_pin = reducer.digest(snapshot)
        _need(common_snapshot is None or common_snapshot == snapshot_pin, 'selected snapshots disagree')
        common_snapshot, messages = snapshot_pin, records
        found = False
        for line, message in enumerate(records, 1):
            retained._envelope(message, line)
            mid, digest = str(message['id']), reducer.digest(message)
            _need(mid not in broker or broker[mid] == digest, 'conflicting broker ID in prepared inputs: ' + mid)
            broker[mid] = digest
            if message['id'] == assignment['id']:
                _need(digest == key, 'assignment differs from snapshot envelope')
                found = True
        _need(found, 'selected assignment absent from snapshot')
        selected.append({'label': label, 'key': key, 'initial': initial,
                         'initial_deadline_utc': row['start_deadline_utc'],
                         'checkpoint_seconds': row['checkpoint_seconds']})
    frozen = {'manifest_sha256': pins['manifest.json'][1], 'source_sha256': manifest['source_sha256'],
              'selection_sha256': manifest['selection_sha256'],
              'files': {name: pin[1] for name, pin in sorted(pins.items())}}
    result = {'root': root, 'pins': pins, 'selected': selected, 'messages': messages, 'broker': broker,
              'observed_at_utc': manifest['observed_at_utc'], 'frozen': frozen}
    _verify_inputs(result)
    return result


def _verify_inputs(inputs):
    for name, pin in inputs['pins'].items():
        retained._unchanged(inputs['root'] / name, pin, MAX_BYTES)


def _generation_name(number):
    _need(type(number) is int and 1 <= number <= 99999999, 'generation must be 1..99999999')
    return '%08d.json' % number


def _uncertain(root, number, writer=False):
    result = []
    for path in (root / 'generations').iterdir():
        match = re.fullmatch(r'([0-9]{8})\.json', path.name)
        if match is None or not 1 <= int(match[1]) <= number:
            result.append('generations/' + path.name)
    result.extend(path.name for path in root.glob('.checkins-*'))
    if writer and (root / '.writer.lock').exists():
        result.append('.writer.lock')
    return sorted(result)


def _head(root):
    _need(stat.S_ISDIR(root.lstat().st_mode) and stat.S_ISDIR((root / 'generations').lstat().st_mode),
          'session directories must be regular directories')
    pointer_raw, pointer_pin = retained._copy(root / 'CURRENT.json', 4096)
    pointer = retained._json(pointer_raw, 'CURRENT.json')
    _need(isinstance(pointer, dict) and set(pointer) == {'generation', 'sha256'}, 'invalid current pointer')
    name = _generation_name(pointer['generation'])
    _need(_hex(pointer['sha256']), 'invalid generation pin')
    raw, _ = retained._copy(root / 'generations' / name, MAX_BYTES)
    _need(_sha(raw) == pointer['sha256'], 'committed generation hash mismatch')
    generation = retained._json(raw, name)
    _need(isinstance(generation, dict) and generation.get('schema') == SCHEMA and
          generation.get('generation') == pointer['generation'], 'invalid committed generation')
    _need(generation.get('automatic_send') is False and generation.get('automatic_assignment') is False,
          'committed automatic actions must remain disabled')
    _need(isinstance(generation.get('states'), dict) and len(generation['states']) <= MAX_STATES and
          isinstance(generation.get('messages'), dict) and len(generation['messages']) <= MAX_MESSAGES,
          'invalid committed state bounds')
    for key, entry in generation['states'].items():
        _need(_hex(key) and isinstance(entry, dict) and isinstance(entry.get('state'), dict) and
              entry['state'].get('assignment_sha256') == key and
              entry['state'].get('schema') == 'daedalus.team-checkins.v1', 'invalid assignment state binding')
        for flag in ('started', 'terminal', 'acceptance_missing', 'reminder_issued'):
            _need(type(entry['state'].get(flag)) is bool, 'invalid persisted state flag: ' + flag)
    retained._unchanged(root / 'CURRENT.json', pointer_pin, 4096)
    return generation, pointer['sha256']


@contextmanager
def _writer(root):
    lock = root / '.writer.lock'
    try:
        stream = lock.open('xb')
    except FileExistsError as error:
        raise SessionError('writer marker exists; busy or interrupted session requires reconciliation') from error
    owned = os.fstat(stream.fileno())
    try:
        stream.write(b'checkin-session-writer\n')
        stream.flush()
        os.fsync(stream.fileno())
        yield
    finally:
        stream.close()
        try:
            current = lock.lstat()
        except FileNotFoundError as error:
            raise SessionError('writer marker disappeared; session publication requires reconciliation') from error
        _need((current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino),
              'writer marker identity changed; foreign marker not removed')
        lock.unlink()


def _next(inputs, evaluation, previous=None, previous_sha=None):
    _need(_clock(evaluation) >= _clock(inputs['observed_at_utc']), 'evaluation precedes retained observation')
    if previous:
        _need(_clock(evaluation) >= _clock(previous['evaluation_utc']), 'evaluation time reversed')
        _need(_clock(inputs['observed_at_utc']) >= _clock(previous['observed_at_utc']), 'observation time reversed')
    states = json.loads(json.dumps(previous['states'])) if previous else {}
    broker = dict(previous['messages']) if previous else {}
    for mid, pin in inputs['broker'].items():
        _need(mid not in broker or broker[mid] == pin, 'conflicting persisted broker ID: ' + mid)
        broker[mid] = pin
    _need(len(broker) <= MAX_MESSAGES, 'session broker-ID count exceeded')
    logical = {}
    for key, entry in states.items():
        state = entry['state']
        identity = reducer.digest([state['coordinator'], state['worker'], state['assignment_id']])
        _need(identity not in logical or logical[identity] == key, 'ambiguous persisted logical assignment')
        logical[identity] = key
    selected, processed, advice = [], set(), []
    for row in inputs['selected']:
        key, initial = row['key'], row['initial']
        identity = reducer.digest([initial['coordinator'], initial['worker'], initial['assignment_id']])
        _need(identity not in logical or logical[identity] == key, 'logical assignment rebinding refused')
        logical[identity] = key
        if key not in states:
            states[key] = {'initial_deadline_utc': row['initial_deadline_utc'],
                           'checkpoint_seconds': row['checkpoint_seconds'], 'state': initial}
        entry = states[key]
        _need(entry['initial_deadline_utc'] == row['initial_deadline_utc'] and
              entry['checkpoint_seconds'] == row['checkpoint_seconds'], 'assignment deadline/interval rebinding refused')
        selected.append({'label': row['label'], 'key': key})
        if key in processed:
            continue
        processed.add(key)
        state = reducer.reduce(entry['state'], inputs['messages'], _compatible_clock(inputs['observed_at_utc']))
        recommendation = None
        if _clock(evaluation) >= _clock(state['deadline_utc']):
            raw_deadline = state['deadline_utc']
            state['deadline_utc'] = _compatible_clock(raw_deadline)
            state, recommendation = reducer.checkpoint(state, _compatible_clock(evaluation))
            state['deadline_utc'] = raw_deadline
        entry['state'] = state
        if recommendation is not None:
            advice.append({'assignment_sha256': key, 'recommendation': recommendation})
    _need(len(states) <= MAX_STATES, 'session assignment count exceeded')
    return {'schema': SCHEMA, 'generation': previous['generation'] + 1 if previous else 1,
            'prior': {'generation': previous['generation'], 'sha256': previous_sha} if previous else None,
            'prepared': inputs['frozen'], 'observed_at_utc': inputs['observed_at_utc'], 'evaluation_utc': evaluation,
            'states': states, 'messages': broker, 'selected': selected, 'omitted': sorted(set(states) - processed),
            'committed_advice': advice, 'automatic_send': False, 'automatic_assignment': False,
            'durability': 'file fsync + atomic CURRENT; directory fsync on POSIX, filesystem metadata guarantees on Windows'}


def _sync_directory(path):
    if os.name != 'nt':
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _publish(root, generation, inputs):
    raw = retained._encode(generation, MAX_BYTES)
    _verify_inputs(inputs)
    name = _generation_name(generation['generation'])
    path = root / 'generations' / name
    try:
        with path.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _sync_directory(root / 'generations')
        _verify_inputs(inputs)
        reducer.save(root / 'CURRENT.json', {'generation': generation['generation'], 'sha256': _sha(raw)})
        _sync_directory(root)
    except (OSError, ValueError) as error:
        raise SessionError('publication uncertain; generation retained at %s; show/reconcile before retry: %s'
                           % (path, error)) from error
    return _report(generation, _sha(raw), [], True)


def _report(generation, digest, uncertain, produced=False):
    return dict(generation, generation_sha256=digest, uncertain_artifacts=uncertain,
                new_advice=generation['committed_advice'] if produced else [])


def initialize(prepared, evaluation_utc, session):
    inputs = _inputs(prepared)
    generation = _next(inputs, evaluation_utc)
    retained._encode(generation, MAX_BYTES)
    root = Path(session)
    _need(root.parent.is_dir(), 'session parent must already exist')
    _verify_inputs(inputs)
    root.mkdir()  # Existing sessions/inputs/state are never overwritten.
    (root / 'generations').mkdir()
    _sync_directory(root.parent)
    with _writer(root):
        return _publish(root, generation, inputs)


def advance(prepared, evaluation_utc, session, expected_generation):
    _generation_name(expected_generation)
    inputs, root = _inputs(prepared), Path(session)
    _need(stat.S_ISDIR(root.lstat().st_mode), 'session must be a regular directory')
    with _writer(root):
        previous, digest = _head(root)
        _need(previous['generation'] == expected_generation, 'stale expected generation')
        _need(not _uncertain(root, expected_generation), 'incomplete/unreferenced generation; reconcile before advancing')
        generation = _next(inputs, evaluation_utc, previous, digest)
        return _publish(root, generation, inputs)


def show(prepared, evaluation_utc, session, expected_generation):
    _generation_name(expected_generation)
    inputs, root = _inputs(prepared), Path(session)
    _need(_clock(evaluation_utc) >= _clock(inputs['observed_at_utc']), 'evaluation precedes retained observation')
    if not (root / 'CURRENT.json').exists():
        _need(stat.S_ISDIR(root.lstat().st_mode) and stat.S_ISDIR((root / 'generations').lstat().st_mode),
              'partial session directories must be regular directories')
        _verify_inputs(inputs)
        return {'schema': SCHEMA, 'generation': None, 'generation_sha256': None,
                'expected_generation': expected_generation, 'states': {}, 'committed_advice': [], 'new_advice': [],
                'uncertain_artifacts': _uncertain(root, 0, True) + ['CURRENT.json missing'],
                'outcome': 'uncommitted_session_requires_reconciliation',
                'requested_evaluation_utc': evaluation_utc, 'automatic_send': False, 'automatic_assignment': False}
    generation, digest = _head(root)
    _need(generation['generation'] == expected_generation, 'stale expected generation')
    _need(inputs['frozen'] == generation['prepared'], 'show requires the committed prepared input set')
    _need(_clock(evaluation_utc) >= _clock(generation['evaluation_utc']), 'evaluation time reversed')
    _verify_inputs(inputs)
    # Requested evaluation is display metadata, never a refreshed observation/checkpoint.
    return dict(_report(generation, digest, _uncertain(root, expected_generation, True)),
                requested_evaluation_utc=evaluation_utc)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['init', 'advance', 'show'])
    parser.add_argument('--prepared', required=True)
    parser.add_argument('--evaluation-utc', required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--expected-generation', type=int)
    args = parser.parse_args(argv)
    try:
        if args.operation == 'init':
            _need(args.expected_generation is None, 'init requires a new session, not an expected generation')
            result = initialize(args.prepared, args.evaluation_utc, args.session)
        else:
            _need(args.expected_generation is not None, 'advance/show require an explicit expected generation')
            operation = advance if args.operation == 'advance' else show
            result = operation(args.prepared, args.evaluation_utc, args.session, args.expected_generation)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        print(json.dumps({'error': str(error), 'automatic_send': False,
                          'automatic_assignment': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
