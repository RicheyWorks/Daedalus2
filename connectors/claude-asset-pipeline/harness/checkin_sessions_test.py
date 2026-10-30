"""Essential session contracts using synthetic retained inputs only."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_pipeline import retained_checkins as retained
from asset_pipeline import team_checkins as reducer
from asset_pipeline import checkin_sessions as sessions

OBSERVED = '2026-10-16T06:40:00.1234567Z'
EVALUATED = '2026-10-16T07:00:00.1234568Z'
DEADLINE = '2026-10-16T06:45:00Z'


def assignment(mid, identity, worker):
    return {'id': mid, 'ts': '2026-10-16T06:30:00.1234567',
            'from': 'pootscoot-coordination', 'to': worker, 'type': 'task.assign',
            'body': {'assignment_id': identity, 'request_id': identity + '-request'}, 'reply_to': None}


def reply(mid, selected, kind, body=None):
    return {'id': mid, 'ts': '2026-10-16T06:31:00', 'from': selected['to'],
            'to': selected['from'], 'type': kind,
            'body': body if body is not None else {'assignment_id': selected['body']['assignment_id']},
            'reply_to': selected['id']}


class CheckinSessions(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.session = self.root / 'session'
        self.first = assignment(10, 'first-task', 'synthetic-alpha')
        self.second = assignment(20, 'second-task', 'synthetic-beta')
        self.keys = [reducer.digest(message) for message in (self.first, self.second)]
        self.count = 0

    def prepare(self, records=None, selections=None, observed=OBSERVED):
        self.count += 1
        folder = self.root / ('inputs-%d' % self.count)
        folder.mkdir()
        records = records if records is not None else [self.first, self.second,
            reply(11, self.first, 'ack', {'id': 10}), reply(21, self.second, 'ack', {'id': 20})]
        selections = selections if selections is not None else [('alpha', 10), ('beta', 20)]
        raw = b''.join((json.dumps(message) + '\n').encode() for message in records)
        source, mapping, output = (folder / name for name in ('retained.jsonl', 'map.json', 'prepared'))
        source.write_bytes(raw)
        mapping.write_text(json.dumps({'schema': retained.SCHEMA,
            'source_sha256': hashlib.sha256(raw).hexdigest(), 'assignments': [
                {'label': label, 'message_id': mid, 'start_deadline_utc': DEADLINE, 'checkpoint_seconds': 300}
                for label, mid in selections]}), encoding='utf-8')
        retained.prepare(source, mapping, observed, output)
        return output

    def current(self):
        return (self.session / 'CURRENT.json').read_bytes()

    def assert_uncommitted(self, before):
        self.assertEqual(before, self.current())
        self.assertFalse((self.session / 'generations/00000002.json').exists())

    def test_two_assignment_cli_init_then_progression_and_supersession(self):
        newer = assignment(30, 'new-first-task', self.first['to'])
        initial_records = [self.first, self.second, reply(11, self.first, 'task.start')]
        prepared = self.prepare(initial_records)
        cwd = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, '-B', '-m', 'asset_pipeline.checkin_sessions', 'init',
            '--prepared', str(prepared), '--evaluation-utc', EVALUATED, '--session', str(self.session)],
            cwd=cwd, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        first = json.loads(result.stdout)
        self.assertEqual(1, first['generation'])
        self.assertTrue(first['states'][self.keys[0]]['state']['started'])
        self.assertFalse(first['states'][self.keys[1]]['state']['started'])
        records = initial_records + [newer, reply(31, newer, 'task.blocked'),
                                     reply(32, self.first, 'task.completed')]
        update = self.prepare(records, [('old-alpha', 10), ('beta', 20), ('new-alpha', 30)],
                              '2026-10-16T06:50:00.1234567Z')
        second = sessions.advance(update, '2026-10-16T07:10:00Z', self.session, 1)
        self.assertEqual(2, second['generation'])
        self.assertEqual(30, second['states'][self.keys[0]]['state']['superseded_by'])
        latest = second['states'][reducer.digest(newer)]['state']
        self.assertEqual('blocked', latest['stage'])
        self.assertTrue(latest['acceptance_missing'])
        self.assertFalse(latest['started'])
        self.assertFalse(second['automatic_send'] or second['automatic_assignment'])

    def test_replay_alias_change_preserves_missing_start_deadlines_and_one_advice(self):
        prepared = self.prepare()
        first = sessions.initialize(prepared, EVALUATED, self.session)
        self.assertEqual(2, len(first['new_advice']))
        replay = self.prepare(selections=[('renamed-alpha', 10), ('renamed-beta', 20)])
        second = sessions.advance(replay, '2026-10-16T07:30:00Z', self.session, 1)
        self.assertEqual([], second['new_advice'])
        self.assertEqual(first['states'], second['states'])
        self.assertEqual(set(self.keys), set(second['states']))
        for entry in second['states'].values():
            self.assertEqual(DEADLINE, entry['state']['deadline_utc'])
            self.assertTrue(entry['state']['reminder_issued'] and entry['state']['acceptance_missing'])
            self.assertFalse(entry['state']['started'])
        before = self.current()
        shown = sessions.show(replay, '2026-10-16T07:30:00Z', self.session, 2)
        self.assertEqual([], shown['new_advice'])
        self.assertEqual(before, self.current())

    def test_omitted_assignment_is_retained_without_refresh_or_completion(self):
        prepared = self.prepare()
        first = sessions.initialize(prepared, EVALUATED, self.session)
        records = [self.first, self.second, reply(11, self.first, 'ack', {'id': 10}),
                   reply(21, self.second, 'ack', {'id': 20}), reply(22, self.second, 'task.completed')]
        update = self.prepare(records, [('alpha', 10)], '2026-10-16T06:50:00Z')
        second = sessions.advance(update, '2026-10-16T07:30:00Z', self.session, 1)
        self.assertEqual(first['states'][self.keys[1]], second['states'][self.keys[1]])
        self.assertIn(self.keys[1], second['omitted'])
        self.assertFalse(second['states'][self.keys[1]]['state']['terminal'])

    def test_stale_expected_conflicting_replay_and_rebinding_do_not_commit(self):
        prepared = self.prepare()
        sessions.initialize(prepared, EVALUATED, self.session)
        before = self.current()
        with self.assertRaises((ValueError, OSError)):
            sessions.advance(prepared, EVALUATED, self.session, 2)
        self.assert_uncommitted(before)
        conflict = self.prepare([self.first, self.second,
            reply(11, self.first, 'ack', {'id': 999}), reply(21, self.second, 'ack', {'id': 20})])
        with self.assertRaises((ValueError, OSError)):
            sessions.advance(conflict, EVALUATED, self.session, 1)
        self.assert_uncommitted(before)
        rebound = copy.deepcopy(self.first)
        rebound['id'] = 30
        changed = self.prepare([self.first, self.second, rebound], [('replacement-label', 30)])
        with self.assertRaises((ValueError, OSError)):
            sessions.advance(changed, EVALUATED, self.session, 1)
        self.assert_uncommitted(before)

    def test_incomplete_generation_remains_evidence_and_blocks_replay(self):
        prepared = self.prepare()
        sessions.initialize(prepared, EVALUATED, self.session)
        before = self.current()
        incomplete = self.session / 'generations/00000002.json'
        incomplete.write_bytes(b'{"partial":')
        with self.assertRaises((ValueError, OSError)):
            sessions.advance(prepared, EVALUATED, self.session, 1)
        self.assertEqual(before, self.current())
        self.assertEqual(b'{"partial":', incomplete.read_bytes())
        shown = sessions.show(prepared, EVALUATED, self.session, 1)
        self.assertIn('00000002.json', json.dumps(shown['uncertain_artifacts']))
        self.assertEqual([], shown['new_advice'])
        self.assertEqual(before, self.current())
        interrupted = self.root / 'interrupted-initial-publication'
        with patch.object(sessions.reducer, 'save', side_effect=OSError('synthetic pointer failure')):
            with self.assertRaises((ValueError, OSError)):
                sessions.initialize(prepared, EVALUATED, interrupted)
        self.assertTrue((interrupted / 'generations/00000001.json').is_file())
        self.assertFalse((interrupted / 'CURRENT.json').exists())
        evidence = {path.relative_to(interrupted).as_posix(): path.read_bytes()
                    for path in interrupted.rglob('*') if path.is_file()}
        uncommitted = sessions.show(prepared, EVALUATED, interrupted, 1)
        self.assertIsNone(uncommitted['generation'])
        self.assertEqual([], uncommitted['new_advice'])
        self.assertIn('00000001.json', json.dumps(uncommitted['uncertain_artifacts']))
        self.assertFalse(uncommitted['automatic_send'] or uncommitted['automatic_assignment'])
        with self.assertRaises((ValueError, OSError)):
            sessions.initialize(prepared, EVALUATED, interrupted)
        self.assertEqual(evidence, {path.relative_to(interrupted).as_posix(): path.read_bytes()
                                   for path in interrupted.rglob('*') if path.is_file()})

    def test_foreign_writer_marker_is_not_removed_or_overwritten(self):
        prepared = self.prepare()
        sessions.initialize(prepared, EVALUATED, self.session)
        before = self.current()
        marker = self.session / '.writer.lock'
        marker.write_bytes(b'foreign synthetic writer')
        with self.assertRaises((ValueError, OSError)):
            sessions.advance(prepared, EVALUATED, self.session, 1)
        self.assertEqual(b'foreign synthetic writer', marker.read_bytes())
        self.assert_uncommitted(before)

    def test_all_selected_inputs_validate_before_new_session_mutation(self):
        prepared = self.prepare()
        assignment_path = prepared / 'beta/assignment.json'
        changed = json.loads(assignment_path.read_text())
        changed['body']['request_id'] = 'tampered'
        assignment_path.write_text(json.dumps(changed))
        with self.assertRaises((ValueError, OSError)):
            sessions.initialize(prepared, EVALUATED, self.session)
        self.assertFalse(self.session.exists())

    def test_observation_and_evaluation_order_refuses_without_next_generation(self):
        prepared = self.prepare()
        sessions.initialize(prepared, EVALUATED, self.session)
        before = self.current()
        older = self.prepare(observed='2026-10-16T06:39:00Z')
        for inputs, evaluation in [(older, EVALUATED), (prepared, '2026-10-16T06:30:00Z')]:
            with self.subTest(evaluation=evaluation), self.assertRaises((ValueError, OSError)):
                sessions.advance(inputs, evaluation, self.session, 1)
            self.assert_uncommitted(before)
        for fraction in ('1', '12', '1234', '12345'):
            with self.subTest(fraction=fraction):
                prepared = self.prepare(selections=[('alpha', 10)],
                                        observed='2026-10-16T06:40:00.123456Z')
                observed = '2026-10-16T06:40:00.' + fraction + 'Z'
                deadline = '2026-10-16T06:45:00.1Z'
                manifest_path = prepared / 'manifest.json'
                manifest = json.loads(manifest_path.read_text())
                manifest['observed_at_utc'] = observed
                for row in manifest['assignments']:
                    row['start_deadline_utc'] = deadline
                    snapshot_path = prepared / row['label'] / row['snapshot']
                    snapshot = json.loads(snapshot_path.read_text())
                    snapshot['observed_at_utc'] = observed
                    snapshot_path.write_text(json.dumps(snapshot), encoding='utf-8')
                manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                session = self.root / ('fraction-' + fraction)
                first = sessions.initialize(prepared, '2026-10-16T06:45:00.099999999Z', session)
                self.assertEqual(observed, first['observed_at_utc'])
                self.assertEqual(deadline, first['states'][self.keys[0]]['initial_deadline_utc'])
                self.assertEqual(deadline, first['states'][self.keys[0]]['state']['deadline_utc'])
                self.assertEqual([], first['new_advice'])
                equal = sessions.advance(prepared, deadline, session, 1)
                self.assertEqual(1, len(equal['new_advice']))
                self.assertEqual(observed, equal['observed_at_utc'])
                self.assertEqual(deadline, equal['states'][self.keys[0]]['state']['deadline_utc'])


if __name__ == '__main__':
    unittest.main()
