"""Prepare retained-copy JSONL for team_checkins; never connect, send or dispatch.

The explicit selection-map JSON has schema ``daedalus.retained-checkins-map.v1``,
the retained copy's ``source_sha256``, and ``assignments`` containing
``label``, ``message_id``, ``start_deadline_utc`` and ``checkpoint_seconds``.
Labels name output folders only. Original envelopes/ts are never synthesized.
The caller separately invokes team_checkins with the generated inputs and its
own state path. A final manifest marks complete publication; partial directories
are retained on errors and cannot be overwritten by a retry.
"""
import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

from . import team_checkins as reducer

SCHEMA = 'daedalus.retained-checkins-map.v1'
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_RECORDS = 10000
MAX_MAP_BYTES = 64 * 1024
MAX_ASSIGNMENTS = 64
MAX_OUTPUT_BYTES = 64 * 1024 * 1024


class InputError(ValueError):
    pass


def _need(ok, message):
    if not ok:
        raise InputError(message)


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _copy(path, limit):
    """Bounded regular-file read; refuse replacement or in-place mutation."""
    path = Path(path)
    before = path.lstat()
    _need(stat.S_ISREG(before.st_mode), 'input must be a regular retained-copy file')
    _need(0 < before.st_size <= limit, 'input byte limit exceeded or input empty')
    with path.open('rb') as stream:
        _need(_stamp(os.fstat(stream.fileno())) == _stamp(before), 'input replaced before read')
        raw = stream.read(limit + 1)
        _need(len(raw) <= limit, 'input byte limit exceeded')
        _need(_stamp(os.fstat(stream.fileno())) == _stamp(before), 'input changed during read')
    _need(_stamp(path.lstat()) == _stamp(before), 'input changed after read')
    return raw, (_stamp(before), hashlib.sha256(raw).hexdigest())


def _unchanged(path, pin, limit):
    _need(_copy(path, limit)[1] == pin, 'retained input changed before publication completed')


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, 'duplicate JSON object key: ' + key)
        result[key] = value
    return result


def _number(value, floating=False):
    _need(len(value) <= 128, 'JSON number too long')
    result = float(value) if floating else int(value)
    _need(not floating or math.isfinite(result), 'nonfinite JSON number')
    return result


def _json(raw, context):
    try:
        return json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=_pairs,
                          parse_int=_number, parse_float=lambda s: _number(s, True),
                          parse_constant=lambda s: _need(False, 'nonfinite JSON constant'))
    except (UnicodeError, ValueError, RecursionError) as error:
        raise InputError(context + ': ' + str(error)) from error


def _envelope(message, line):
    prefix = 'line %d: ' % line
    _need(isinstance(message, dict), prefix + 'broker envelope must be an object')
    try:
        reducer.positive(message.get('id'))
        if message.get('reply_to') is not None:
            reducer.positive(message['reply_to'])
    except ValueError as error:
        raise InputError(prefix + str(error)) from error
    for key in ('from', 'to', 'type', 'ts'):
        _need(isinstance(message.get(key), str) and bool(message[key].strip()), prefix + 'missing ' + key)
    _need('body' in message and 'reply_to' in message, prefix + 'missing body/reply_to envelope fields')
    # Validate calendar shape without treating naive broker-local clocks as UTC.
    clock = re.fullmatch(r'([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})'
                         r'(?:\.[0-9]{1,9})?(Z|[+-][0-9]{2}:[0-9]{2})?', message['ts'])
    _need(clock is not None, prefix + 'unsupported original ts; no timezone inference')
    try:
        datetime.fromisoformat(clock[1] + (clock[2] or '').replace('Z', '+00:00'))
    except ValueError as error:
        raise InputError(prefix + 'invalid original ts') from error


def _records(raw):
    _need(raw.endswith(b'\n'), 'unterminated/partial final JSONL record')
    lines = raw[:-1].split(b'\n')
    _need(len(lines) <= MAX_RECORDS, 'record count limit exceeded')
    messages, seen, diagnostics = [], {}, []
    known = {'ping', 'task.assign', 'ack', 'checkin'} | set(reducer.KINDS)
    for line, data in enumerate(lines, 1):
        _need(len(data) <= MAX_LINE_BYTES, 'line %d: byte limit exceeded' % line)
        _need(bool(data.strip()), 'line %d: empty record refused' % line)
        message = _json(data, 'line %d' % line)
        _envelope(message, line)
        mid, pin = message['id'], reducer.digest(message)
        _need(mid not in seen or seen[mid] == pin, 'line %d: conflicting broker ID %d' % (line, mid))
        seen[mid] = pin
        messages.append(message)  # Keep exact replays and every unqualified envelope.
        body = message['body']
        reason = ('unknown_type' if message['type'] not in known else
                  'unstructured_body' if not isinstance(body, dict) else
                  'unknown_checkin_status' if message['type'] == 'checkin' and
                  body.get('status') not in reducer.STATUSES else
                  'missing_correlation' if (message['type'] in reducer.KINDS or message['type'] == 'checkin')
                  and not (isinstance(body.get('assignment_id'), str) and body['assignment_id'])
                  and message['reply_to'] is None else None)
        if reason:
            diagnostics.append({'line': line, 'id': mid, 'reason': reason})
    return messages, diagnostics


def _encode(value, limit=None):
    limit = MAX_OUTPUT_BYTES if limit is None else limit
    encoded = bytearray()
    try:
        for chunk in json.JSONEncoder(sort_keys=True, allow_nan=False,
                                      separators=(',', ':')).iterencode(value):
            raw = chunk.encode('utf-8')
            _need(len(encoded) + len(raw) + 1 <= limit, 'output byte limit exceeded')
            encoded.extend(raw)
    except RecursionError as error:
        raise InputError('JSON nesting exceeds supported encoding depth') from error
    encoded.extend(b'\n')
    return bytes(encoded)


def prepare(retained_copy, selection_map, observed_at_utc, output):
    """Validate explicit retained inputs, then publish fresh reducer input files."""
    reducer.utc(observed_at_utc)
    source_raw, source_pin = _copy(retained_copy, MAX_SOURCE_BYTES)
    map_raw, map_pin = _copy(selection_map, MAX_MAP_BYTES)
    mapping = _json(map_raw, 'selection map')
    _need(isinstance(mapping, dict) and set(mapping) == {'schema', 'source_sha256', 'assignments'},
          'selection map requires schema/source_sha256/assignments only')
    _need(mapping['schema'] == SCHEMA, 'unsupported selection map schema')
    _need(mapping['source_sha256'] == source_pin[1], 'retained source SHA256 mismatch')
    selections = mapping['assignments']
    _need(isinstance(selections, list) and 1 <= len(selections) <= MAX_ASSIGNMENTS,
          'assignment count must be 1..%d' % MAX_ASSIGNMENTS)
    messages, diagnostics = _records(source_raw)
    by_id = {m['id']: m for m in messages}
    snapshot = _encode({'observed_at_utc': observed_at_utc, 'messages': messages})
    labels, files, entries, output_bytes = set(), {}, [], 0
    for row in selections:
        _need(isinstance(row, dict) and set(row) ==
              {'label', 'message_id', 'start_deadline_utc', 'checkpoint_seconds'}, 'invalid assignment-map entry')
        label = row['label']
        _need(isinstance(label, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', label),
              'label must be a simple portable directory name')
        _need(label.upper() not in {'CON', 'PRN', 'AUX', 'NUL'} and
              not re.fullmatch(r'(COM|LPT)[1-9]', label.upper()), 'reserved output label')
        _need(label.casefold() not in labels, 'duplicate output label')
        labels.add(label.casefold())
        mid = reducer.positive(row['message_id'])
        _need(mid in by_id, 'selected broker ID %d is absent' % mid)
        assignment = by_id[mid]
        _need(assignment['type'] in {'ping', 'task.assign'} and isinstance(assignment['body'], dict),
              'label %s selects an unsupported/unstructured assignment' % label)
        try:
            reducer.create(assignment, row['start_deadline_utc'], row['checkpoint_seconds'])
        except (ValueError, KeyError, TypeError) as error:
            raise InputError('label %s: %s' % (label, error)) from error
        encoded_assignment = _encode(assignment, MAX_OUTPUT_BYTES - output_bytes - len(snapshot))
        files[label + '/assignment.json'] = encoded_assignment
        files[label + '/snapshot.json'] = snapshot
        output_bytes += len(encoded_assignment) + len(snapshot)
        entries.append(dict(row, assignment='assignment.json', snapshot='snapshot.json',
                            assignment_sha256=reducer.digest(assignment)))
    manifest = {'schema': 'daedalus.retained-checkins-inputs.v1', 'source_sha256': source_pin[1],
                'selection_sha256': map_pin[1], 'source_bytes': len(source_raw),
                'records': len(messages), 'observed_at_utc': observed_at_utc,
                'event_clock_policy': 'Original ts retained verbatim; naive local clocks are not UTC observations.',
                'assignments': sorted(entries, key=lambda x: x['label']), 'unqualified_records': diagnostics,
                'automatic_send': False, 'automatic_assignment': False}
    files['manifest.json'] = _encode(manifest, MAX_OUTPUT_BYTES - output_bytes)
    _need(sum(map(len, files.values())) <= MAX_OUTPUT_BYTES, 'output byte limit exceeded')
    _unchanged(retained_copy, source_pin, MAX_SOURCE_BYTES)
    _unchanged(selection_map, map_pin, MAX_MAP_BYTES)
    target = Path(output)
    _need(target.parent.is_dir(), 'output parent must already exist')
    target.mkdir()  # Exclusive: no existing output, input or caller state is overwritten.
    try:
        for name in sorted(files):
            if name == 'manifest.json':
                continue
            path = target / name
            path.parent.mkdir(exist_ok=True)
            with path.open('xb') as stream:
                stream.write(files[name])
        _unchanged(retained_copy, source_pin, MAX_SOURCE_BYTES)
        _unchanged(selection_map, map_pin, MAX_MAP_BYTES)
        with (target / 'manifest.json').open('xb') as stream:
            stream.write(files['manifest.json'])
    except (OSError, ValueError) as error:
        raise InputError('publication incomplete; partial output retained at %s: %s' % (target, error)) from error
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained-copy', required=True)
    parser.add_argument('--selection-map', required=True)
    parser.add_argument('--observed-at-utc', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.retained_copy, args.selection_map, args.observed_at_utc, args.output)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        print(json.dumps({'error': str(error), 'automatic_send': False,
                          'automatic_assignment': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
