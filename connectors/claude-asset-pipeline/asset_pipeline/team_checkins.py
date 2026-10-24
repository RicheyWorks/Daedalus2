"""Reduce retained TeamLink messages; never poll, send, wake, or assign work."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
import re
from pathlib import Path
import tempfile


def utc(value):
    if not isinstance(value, str) or not value.endswith(('Z', '+00:00')):
        raise ValueError('explicit UTC timestamp required')
    # PowerShell DateTimeOffset emits seven fractional digits; Python 3.10's
    # parser accepts microseconds. Truncate sub-microsecond precision only.
    normalized = re.sub(r'(\.\d{6})\d+(?=\+00:00$)', r'\1', value.replace('Z', '+00:00'))
    return datetime.fromisoformat(normalized)


def positive(value):
    if type(value) is not int or value <= 0:
        raise ValueError('positive broker message ID required')
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def create(assignment, start_deadline, checkpoint_seconds=900):
    """Assignment is an actual retained coordinator -> worker hub message."""
    mid = positive(assignment['id'])
    body = assignment['body']
    coordinator, worker = assignment['from'], assignment['to']
    if coordinator != 'pootscoot-coordination' or not isinstance(worker, str) or worker in ('*', coordinator, ''):
        raise ValueError('explicit coordinator-to-worker assignment required')
    for field in ('assignment_id', 'request_id'):
        if not isinstance(body.get(field), str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}', body[field]):
            raise ValueError('structured assignment and request identities required')
    utc(start_deadline)
    if type(checkpoint_seconds) is not int or not 1 <= checkpoint_seconds <= 86400:
        raise ValueError('checkpoint interval must be 1..86400 seconds')
    return dict(schema='daedalus.team-checkins.v1', assignment_id=body['assignment_id'],
                request_id=body['request_id'], assignment_message_id=mid,
                assignment_sha256=digest(assignment), coordinator=coordinator, worker=worker,
                stage='delivered', transport_ack=False, started=False, terminal=False,
                acceptance_missing=True,
                superseded_by=None, deadline_utc=start_deadline, checkpoint_seconds=checkpoint_seconds,
                cursor=0, seen={}, correlated_ids=[mid], last_semantic_id=None,
                unqualified_count=0, reminder_issued=False)


KINDS = {'task.start': 'start', 'task.progress': 'progress', 'task.blocked': 'blocked',
         'task.completed': 'completed', 'task.failed': 'failed', 'task.cancelled': 'cancelled'}
STATUSES = {'START': 'start', 'PROGRESS': 'progress', 'BLOCKED': 'blocked',
            'COMPLETED': 'completed', 'FAILED': 'failed', 'CANCELLED': 'cancelled'}


def reduce(state, messages, observed_at):
    """Single-writer reducer; route identities are trusted broker labels, not authentication."""
    now = utc(observed_at)
    state = json.loads(json.dumps(state))
    if state.get('schema') != 'daedalus.team-checkins.v1' or not isinstance(messages, list):
        raise ValueError('unsupported state/messages')
    state['acceptance_missing'] = not state['started']
    for message in sorted(messages, key=lambda m: positive(m['id'])):
        mid, pin = positive(message['id']), digest(message)
        prior = state['seen'].get(str(mid))
        if prior:
            if prior != pin:
                raise ValueError('conflicting replay for broker message ID')
            continue
        state['seen'][str(mid)] = pin
        state['cursor'] = max(state['cursor'], mid)
        body = message.get('body')
        if not isinstance(body, dict):
            continue
        frm, to = message.get('from'), message.get('to')
        if (frm == state['coordinator'] and to == state['worker']
                and mid > state['assignment_message_id'] and body.get('assignment_id')
                and message.get('type') in ('ping', 'task.assign') and body.get('request_id')
                and body['assignment_id'] != state['assignment_id']):
            state['superseded_by'] = max(state['superseded_by'] or 0, mid)
            continue
        if frm != state['worker'] or to != state['coordinator'] or mid <= state['assignment_message_id']:
            continue
        if message.get('type') == 'ack' and body.get('id') == state['assignment_message_id']:
            state['transport_ack'] = True
            continue
        # A conflicting explicit identity must never be rescued by reply_to.
        if body.get('assignment_id') not in (None, state['assignment_id']):
            continue
        correlated = (body.get('assignment_id') == state['assignment_id']
                      or message.get('reply_to') in state['correlated_ids'])
        if body.get('request_id') not in (None, state['request_id']):
            correlated = False
        kind = KINDS.get(message.get('type'))
        if message.get('type') == 'checkin':
            kind = STATUSES.get(body.get('status'))
        if not correlated or not kind:
            state['unqualified_count'] += 1
            continue
        state['correlated_ids'].append(mid)
        # Replayed historical messages cannot roll back a newer semantic state.
        if mid <= (state['last_semantic_id'] or 0) or state['terminal']:
            continue
        if kind == 'start':
            state['started'] = True
            state['acceptance_missing'] = False
        elif not state['started'] and kind == 'progress':
            state['unqualified_count'] += 1
            continue
        state['last_semantic_id'] = mid
        state['stage'] = kind
        state['terminal'] = kind in ('completed', 'failed', 'cancelled')
        # A blocker/result is evidence even if START was missed. Do not invent
        # acceptance or postpone the original missing-START checkpoint.
        if state['started']:
            state['deadline_utc'] = (now + timedelta(seconds=state['checkpoint_seconds'])).isoformat()
    return state


def checkpoint(state, now):
    """Persist the returned state to consume the one advice; no external action."""
    instant = utc(now)
    state = json.loads(json.dumps(state))
    advice = None
    missing = not state['started']
    state['acceptance_missing'] = missing
    if ((not state['terminal'] or missing) and not state['superseded_by'] and not state['reminder_issued']
            and instant >= utc(state['deadline_utc'])):
        advice = {'assignment_id': state['assignment_id'], 'request_id': state['request_id'],
                  'reply_to': state['assignment_message_id'], 'worker': state['worker'],
                  'action': ('reconcile_missing_start' if state['last_semantic_id'] else 'request_semantic_start')
                            if missing else 'request_checkpoint',
                  'automatic_send': False, 'automatic_assignment': False}
        state['reminder_issued'] = True
    return state, advice


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.checkins-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assignment', required=True, help='retained actual assignment message JSON')
    parser.add_argument('--snapshot', required=True, help='{observed_at_utc, messages: actual hub messages}')
    parser.add_argument('--state', required=True)
    parser.add_argument('--start-deadline', required=True)
    parser.add_argument('--checkpoint-seconds', type=int, default=900)
    args = parser.parse_args(argv)
    path = Path(args.state)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + '.lock')
    owned = False
    try:
        with lock.open('x', encoding='utf-8'):
            owned = True
        assignment = json.loads(Path(args.assignment).read_text(encoding='utf-8-sig'))
        snapshot = json.loads(Path(args.snapshot).read_text(encoding='utf-8-sig'))
        if utc(snapshot['observed_at_utc']) > datetime.now(timezone.utc):
            raise ValueError('future snapshot observation')
        state = json.loads(path.read_text()) if path.exists() else create(
            assignment, args.start_deadline, args.checkpoint_seconds)
        if state['assignment_sha256'] != digest(assignment):
            raise ValueError('state belongs to a different assignment')
        state = reduce(state, snapshot['messages'], snapshot['observed_at_utc'])
        state, advice = checkpoint(state, datetime.now(timezone.utc).isoformat())
        save(path, state)
        print(json.dumps({k: state[k] for k in ('assignment_id', 'request_id', 'stage',
              'transport_ack', 'started', 'acceptance_missing', 'terminal', 'superseded_by', 'cursor')}
              | {'advice': advice, 'automatic_send': False, 'automatic_assignment': False}))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({'error': str(error), 'automatic_send': False}), file=__import__('sys').stderr)
        return 2
    finally:
        if owned:
            lock.unlink()


if __name__ == '__main__':
    raise SystemExit(main())
