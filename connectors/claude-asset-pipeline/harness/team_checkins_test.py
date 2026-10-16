"""Focused protocol tests; actual broker IDs/routes retained without message prose."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_pipeline.team_checkins import create, reduce, checkpoint, utc

ASSIGNMENT = {'id': 32833, 'from': 'pootscoot-coordination', 'to': 'unreal-team',
              'type': 'ping', 'reply_to': 32822,
              'body': {'assignment_id': 'prismheart-field-save-fish-request-r1',
                       'request_id': 'claude-prismheart-field-save-20261016T0630Z'}}
OLD = {'id': 32822, 'from': 'unreal-team', 'to': 'pootscoot-coordination',
       'type': 'checkin', 'reply_to': 32760, 'body': {}}
AT = '2026-10-16T06:40:00Z'
DEADLINE = '2026-10-16T06:45:00Z'


def message(mid, status, **extra):
    return dict(id=mid, **{'from': 'unreal-team', 'to': 'pootscoot-coordination'},
                type='checkin', reply_to=32833,
                body=dict(assignment_id=ASSIGNMENT['body']['assignment_id'], status=status, **extra))


class Checkins(unittest.TestCase):
    def test_actual_powershell_timestamp_precision(self):
        self.assertEqual(utc('2026-10-16T06:43:07.1919086+00:00').microsecond, 191908)

    def state(self):
        return create(ASSIGNMENT, DEADLINE, 300)

    def test_actual_old_checkin_cannot_start_new_assignment(self):
        state = reduce(self.state(), [OLD, ASSIGNMENT], AT)
        self.assertEqual(state['stage'], 'delivered')
        self.assertFalse(state['started'])
        self.assertFalse(state['terminal'])

    def test_transport_ack_is_not_start(self):
        ack = {'id': 32834, 'from': 'unreal-team', 'to': 'pootscoot-coordination',
               'type': 'ack', 'body': {'id': 32833}, 'reply_to': 32833}
        state = reduce(self.state(), [ack], AT)
        self.assertTrue(state['transport_ack'])
        self.assertFalse(state['started'])

    def test_start_progress_complete(self):
        state = self.state()
        for mid, status in [(32834, 'START'), (32835, 'PROGRESS'), (32836, 'COMPLETED')]:
            state = reduce(state, [message(mid, status)], AT)
        self.assertTrue(state['started'] and state['terminal'])
        self.assertEqual(state['stage'], 'completed')

    def test_progress_without_start_does_not_hide_missed_start(self):
        state = reduce(self.state(), [message(32834, 'PROGRESS')], AT)
        self.assertFalse(state['started'])
        self.assertEqual(state['deadline_utc'], DEADLINE)

    def test_blocker_after_start(self):
        state = reduce(self.state(), [message(32834, 'START'), message(32835, 'BLOCKED')], AT)
        self.assertEqual(state['stage'], 'blocked')
        self.assertFalse(state['terminal'])

    def test_reconnect_replay_is_exactly_idempotent(self):
        msgs = [message(32834, 'START'), message(32835, 'PROGRESS')]
        first = reduce(self.state(), msgs, AT)
        self.assertEqual(first, reduce(first, msgs, '2026-10-16T06:44:00Z'))

    def test_conflicting_replay_rejected(self):
        state = reduce(self.state(), [message(32834, 'START')], AT)
        with self.assertRaises(ValueError):
            reduce(state, [message(32834, 'COMPLETED')], AT)

    def test_wrong_sender_or_route_never_qualifies(self):
        for field, value in [('from', 'other-team'), ('to', '*')]:
            msg = message(32834, 'START')
            msg[field] = value
            self.assertFalse(reduce(self.state(), [msg], AT)['started'])

    def test_reply_chain_can_correlate_structured_status(self):
        start = message(32834, 'START')
        start['body'].pop('assignment_id')
        progress = message(32835, 'PROGRESS')
        progress['body'].pop('assignment_id')
        progress['reply_to'] = 32834
        state = reduce(self.state(), [start, progress], AT)
        self.assertEqual(state['stage'], 'progress')

    def test_conflicting_assignment_or_request_cannot_use_reply(self):
        for key in ('assignment_id', 'request_id'):
            msg = message(32834, 'START')
            msg['body'][key] = 'older-other-task'
            self.assertFalse(reduce(self.state(), [msg], AT)['started'])

    def test_free_text_start_is_unqualified(self):
        msg = message(32834, 'START')
        msg['body'] = {'text': 'START done working current task'}
        self.assertFalse(reduce(self.state(), [msg], AT)['started'])

    def test_newer_task_blocks_old_task_advice(self):
        newer = json.loads(json.dumps(ASSIGNMENT))
        newer['id'] = 32835
        newer['body']['assignment_id'] = 'new-task'
        state = reduce(self.state(), [message(32834, 'START'), newer, message(32836, 'COMPLETED')], AT)
        self.assertEqual(state['superseded_by'], 32835)
        state, advice = checkpoint(state, '2026-10-16T07:00:00Z')
        self.assertIsNone(advice)

    def test_coordinator_note_is_not_a_new_assignment(self):
        note = json.loads(json.dumps(ASSIGNMENT))
        note.update(id=32835, type='note')
        note['body']['assignment_id'] = 'other-task'
        self.assertIsNone(reduce(self.state(), [note], AT)['superseded_by'])

    def test_one_reminder_only_and_no_auto_action(self):
        state, advice = checkpoint(self.state(), DEADLINE)
        self.assertEqual(advice['action'], 'request_semantic_start')
        self.assertFalse(advice['automatic_send'] or advice['automatic_assignment'])
        state, again = checkpoint(state, '2026-10-16T08:00:00Z')
        self.assertIsNone(again)

    def test_progress_deadline_and_terminal_stability(self):
        state = reduce(self.state(), [message(32834, 'START')], AT)
        state, advice = checkpoint(state, DEADLINE)
        self.assertEqual(advice['action'], 'request_checkpoint')
        state = reduce(state, [message(32835, 'COMPLETED'), message(32836, 'START')], AT)
        self.assertEqual(state['stage'], 'completed')

    def test_late_lower_id_does_not_roll_back_progress(self):
        state = reduce(self.state(), [message(32834, 'START'), message(32836, 'PROGRESS')], AT)
        state = reduce(state, [message(32835, 'BLOCKED')], AT)
        self.assertEqual(state['stage'], 'progress')

    def test_cli_persists_advice_once_and_strips_prose(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'assignment.json').write_text(json.dumps(ASSIGNMENT))
            past = (datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
            (root/'snapshot.json').write_text(json.dumps({'observed_at_utc': past,
                'messages': [OLD, ASSIGNMENT]}))
            cmd = [sys.executable, '-B', '-m', 'asset_pipeline.team_checkins',
                   '--assignment', str(root/'assignment.json'), '--snapshot', str(root/'snapshot.json'),
                   '--state', str(root/'state.json'), '--start-deadline', past]
            cwd = Path(__file__).resolve().parents[1]
            first = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIsNotNone(json.loads(first.stdout)['advice'])
            again = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertIsNone(json.loads(again.stdout)['advice'])
            saved = json.loads((root/'state.json').read_text())
            self.assertNotIn('body', saved)
            self.assertFalse((root/'state.json.lock').exists())


if __name__ == '__main__':
    unittest.main()
