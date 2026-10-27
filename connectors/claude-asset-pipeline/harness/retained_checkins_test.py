"""Synthetic retained-copy contracts; never open a broker log or connect."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_pipeline import retained_checkins as adapter
from asset_pipeline import team_checkins as reducer

OBSERVED = '2026-10-16T07:00:00.1234567Z'
DEADLINE = '2026-10-16T06:45:00Z'


def assignment(mid=10, identity='retained-task'):
    return {'id': mid, 'ts': '2026-10-16T06:30:00.1234567',
            'from': 'pootscoot-coordination', 'to': 'synthetic-worker', 'type': 'ping',
            'body': {'assignment_id': identity, 'request_id': identity + '-request'}, 'reply_to': None}


def reply(mid, kind, body, parent=10):
    return {'id': mid, 'ts': '2026-10-16T06:31:00', 'from': 'synthetic-worker',
            'to': 'pootscoot-coordination', 'type': kind, 'body': body, 'reply_to': parent}


class RetainedInputs(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source, self.mapping, self.output = (self.root / name for name in ('retained.jsonl', 'map.json', 'prepared'))

    def inputs(self, records=None, rows=None, raw=None):
        records = records if records is not None else [assignment(), reply(11, 'ack', {'id': 10})]
        if raw is None:
            raw = b''.join((json.dumps(m) + '\n').encode() for m in records)
        self.source.write_bytes(raw)
        rows = rows if rows is not None else [{'label': 'friendly-alias', 'message_id': 10,
            'start_deadline_utc': DEADLINE, 'checkpoint_seconds': 300}]
        mapping = {'schema': adapter.SCHEMA, 'source_sha256': hashlib.sha256(raw).hexdigest(), 'assignments': rows}
        self.mapping.write_text(json.dumps(mapping), encoding='utf-8')
        return records

    def prepare(self):
        return adapter.prepare(self.source, self.mapping, OBSERVED, self.output)

    def load(self, label, name):
        return json.loads((self.output / label / name).read_text())

    def test_cli_generated_inputs_run_unchanged_reducer_without_inventing_start(self):
        records = self.inputs()
        original = self.source.read_bytes()
        cwd = Path(__file__).resolve().parents[1]
        state = self.root / 'caller-state.json'
        prepared = subprocess.run([sys.executable, '-B', '-m', 'asset_pipeline.retained_checkins',
            '--retained-copy', str(self.source), '--selection-map', str(self.mapping),
            '--observed-at-utc', OBSERVED, '--output', str(self.output)], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(0, prepared.returncode, prepared.stderr)
        manifest = json.loads(prepared.stdout)
        self.assertFalse(manifest['automatic_send'] or manifest['automatic_assignment'])
        self.assertFalse(state.exists())
        self.assertEqual(records[0], self.load('friendly-alias', 'assignment.json'))
        snapshot = self.load('friendly-alias', 'snapshot.json')
        self.assertEqual(records, snapshot['messages'])
        self.assertEqual(OBSERVED, snapshot['observed_at_utc'])
        called = subprocess.run([sys.executable, '-B', '-m', 'asset_pipeline.team_checkins',
            '--assignment', str(self.output / 'friendly-alias/assignment.json'),
            '--snapshot', str(self.output / 'friendly-alias/snapshot.json'), '--state', str(state),
            '--start-deadline', DEADLINE, '--checkpoint-seconds', '300'], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(0, called.returncode, called.stderr)
        report = json.loads(called.stdout)
        self.assertEqual('delivered', report['stage'])
        self.assertTrue(report['transport_ack'] and report['acceptance_missing'])
        self.assertFalse(report['started'] or report['automatic_send'] or report['automatic_assignment'])
        self.assertEqual(original, self.source.read_bytes())

    def test_alias_cannot_supply_missing_assignment_facts_or_select_ack(self):
        for selected in (dict(assignment(), body={'text': 'START'}), reply(10, 'ack', {'id': 9})):
            with self.subTest(selected=selected):
                self.inputs([selected])
                with self.assertRaises(ValueError):
                    self.prepare()
                self.assertFalse(self.output.exists())

    def test_supersession_and_missing_start_result_survive_full_snapshot(self):
        records = [assignment(), assignment(20, 'new-task'),
                   reply(21, 'task.completed', {'assignment_id': 'retained-task'}),
                   reply(22, 'task.blocked', {'assignment_id': 'new-task'}, 20)]
        rows = [{'label': label, 'message_id': mid, 'start_deadline_utc': DEADLINE, 'checkpoint_seconds': 300}
                for label, mid in [('old', 10), ('new', 20)]]
        self.inputs(records, rows)
        self.prepare()
        for label in ('old', 'new'):
            selected = self.load(label, 'assignment.json')
            snapshot = self.load(label, 'snapshot.json')
            state = reducer.reduce(reducer.create(selected, DEADLINE, 300), snapshot['messages'], OBSERVED)
            self.assertFalse(state['started'])
            self.assertTrue(state['acceptance_missing'])
            self.assertEqual(DEADLINE, state['deadline_utc'])
            self.assertEqual('completed' if label == 'old' else 'blocked', state['stage'])
            self.assertEqual(20 if label == 'old' else None, state['superseded_by'])

    def test_exact_replays_preserved_and_conflicting_id_refused(self):
        records = [assignment(), copy.deepcopy(assignment())]
        self.inputs(records)
        self.prepare()
        self.assertEqual(records, self.load('friendly-alias', 'snapshot.json')['messages'])
        self.output = self.root / 'conflict-output'
        records[1]['body']['request_id'] = 'conflict'
        self.inputs(records)
        with self.assertRaisesRegex(ValueError, 'conflicting broker ID'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_malformed_partial_utf8_and_ambiguous_records_refuse(self):
        good = json.dumps(assignment()).encode()
        for raw in (good, good + b'\n{', b'\xff\n', b'\n', b'{"id":10,"id":11}\n',
                    b'{"id":NaN}\n', b'{"id":1e999}\n', b'[]\n'):
            with self.subTest(raw=raw[:40]):
                self.inputs(raw=raw)
                with self.assertRaises(ValueError):
                    self.prepare()
                self.assertFalse(self.output.exists())

    def test_unknown_records_are_visible_and_never_filtered(self):
        unknown = reply(12, 'future.record', {'text': 'START'})
        missing = reply(13, 'task.start', {}, None)
        records = [assignment(), unknown, missing]
        self.inputs(records)
        manifest = self.prepare()
        self.assertEqual([{'line': 2, 'id': 12, 'reason': 'unknown_type'},
                          {'line': 3, 'id': 13, 'reason': 'missing_correlation'}], manifest['unqualified_records'])
        snapshot = self.load('friendly-alias', 'snapshot.json')
        self.assertEqual(records, snapshot['messages'])
        state = reducer.reduce(reducer.create(records[0], DEADLINE), snapshot['messages'], OBSERVED)
        self.assertFalse(state['started'])

    def test_change_during_read_refused_before_output(self):
        self.inputs()
        actual_fstat, calls = os.fstat, 0
        def clock(info, difference):
            return SimpleNamespace(st_dev=info.st_dev, st_ino=info.st_ino, st_size=info.st_size,
                st_mtime_ns=info.st_mtime_ns, st_ctime_ns=info.st_ctime_ns + difference)
        with patch.object(adapter.os, 'fstat', side_effect=lambda fd: clock(actual_fstat(fd), 100)):
            self.prepare()  # Stable source, different path/handle ctime representations.
        self.output = self.root / 'ctime-change'
        def changed_clock(fileno):
            nonlocal calls
            calls += 1
            return clock(actual_fstat(fileno), 100 if calls == 2 else 0)
        with patch.object(adapter.os, 'fstat', side_effect=changed_clock):
            with self.assertRaisesRegex(ValueError, 'changed during read'):
                self.prepare()
        self.assertFalse(self.output.exists())
        self.output = self.root / 'content-change'
        calls = 0
        def changed(fileno):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.source.write_bytes(self.source.read_bytes() + b'\n')
            return actual_fstat(fileno)
        with patch.object(adapter.os, 'fstat', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed during read'):
                self.prepare()
        self.assertFalse(self.output.exists())

    def test_limits_source_pin_and_fresh_output_are_enforced(self):
        self.inputs()
        for name in ('MAX_SOURCE_BYTES', 'MAX_MAP_BYTES', 'MAX_LINE_BYTES', 'MAX_RECORDS', 'MAX_OUTPUT_BYTES'):
            with self.subTest(limit=name), patch.object(adapter, name, 1):
                with self.assertRaises(ValueError):
                    self.prepare()
                self.assertFalse(self.output.exists())
        mapping = json.loads(self.mapping.read_text())
        mapping['source_sha256'] = '0' * 64
        self.mapping.write_text(json.dumps(mapping))
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            self.prepare()
        self.inputs()
        self.output.mkdir()
        sentinel = self.output / 'caller-state.json'
        sentinel.write_bytes(b'unchanged')
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(b'unchanged', sentinel.read_bytes())


if __name__ == '__main__':
    unittest.main()
