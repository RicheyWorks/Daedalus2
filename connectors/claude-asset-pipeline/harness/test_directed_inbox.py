"""Focused offline receiver tests. No broker import, network or message actions."""
import ast
import copy
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent
# Published layout: harness/test_directed_inbox.py and the sibling package
# asset_pipeline/directed_inbox.py. Explicit overrides support an isolated
# source candidate without depending on a personal checkout or importing it.
MODULE = Path(os.environ.get('DIRECTED_INBOX_SOURCE',
    ROOT.parent / 'asset_pipeline' / 'directed_inbox.py')).resolve()
BROKER = Path(os.environ.get('DIRECTED_INBOX_BROKER_SOURCE', MODULE.with_name('teamlink.py'))).resolve()
spec = importlib.util.spec_from_file_location('directed_inbox', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ME = 'pootscoot-coordination'


def message(mid=47870, **changes):
    value = {'id': mid, 'ts': '2026-10-18T23:07:18', 'from': 'blender-team',
        'to': 'unreal-team', 'type': 'note', 'body': {'text': 'NEED @pootscoot-coordination'}, 'reply_to': None}
    value.update(changes)
    return value


class ReceiverTests(unittest.TestCase):
    def test_directed_request_precedes_older_broadcast_backlog(self):
        records = [message(1, to='*'), message(2, to='*'), message(100, to=ME)]
        original = copy.deepcopy(records)
        result = m.inspect_batch({'messages': records, 'last': 100}, ME)
        self.assertEqual([row['id'] for row in result['notices']], [100, 1, 2])
        self.assertEqual(set(result['unhandled_ids']), {1, 2, 100})
        self.assertEqual(result['retained_after'], 0)
        self.assertEqual(records, original)

    def test_actual_broker_route_matches_and_mention_is_not_delivery(self):
        # Execute only the real pure _for method AST, not the broker module.
        tree = ast.parse(BROKER.read_text(encoding='utf-8'))
        broker = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Broker')
        node = next(n for n in broker.body if isinstance(n, ast.FunctionDef) and n.name == '_for')
        scope = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'actual-broker-_for-only', 'exec'), scope)
        records = [message(), message(47871, to=ME), message(47872, to='*'),
            message(47873, to=ME, **{'from': ME})]
        actual = scope['_for'](SimpleNamespace(_since=lambda after: records), ME, 0)
        self.assertEqual([r['id'] for r in actual], [47871, 47872])
        result = m.inspect_batch({'messages': records, 'last': 47880}, ME)
        self.assertEqual([row['id'] for row in result['mention_only']], [47870])
        self.assertEqual([r['id'] for r in result['notices']], [47871, 47872])

    def test_topic_filter_only_applies_to_broadcasts(self):
        records = [message(1, to=ME, topic='other'), message(2, to='*', topic='other'),
            message(3, to='*', topic='wanted')]
        out = m.inspect_batch({'messages': records}, ME, topics=['wanted'])
        self.assertEqual(out['unhandled_ids'], [1, 3])

    def test_global_last_does_not_consume_unhandled_or_other_pending(self):
        records = [message(1, to=ME), message(2, to=ME), message(3, to='another-team')]
        original = copy.deepcopy(records)
        out = m.inspect_batch({'messages': records, 'last': 99}, ME, after=0, handled_ids=[1])
        self.assertEqual(out['unhandled_ids'], [2])
        self.assertEqual(out['retained_after'], 0)
        self.assertEqual(out['reported_broker_last'], 99)
        self.assertFalse(out['ack_or_send_performed'])
        self.assertEqual(records, original)

    def test_missing_transport_response_is_unknown_not_empty_healthy(self):
        out = m.inspect_batch(None, ME, after=9)
        self.assertEqual(out['observation'], 'UNKNOWN')
        self.assertEqual(out['retained_after'], 9)
        self.assertIsNone(out['automatic_wake'])

    def test_exact_reply_and_sender_do_not_infer_semantic_or_parent_read(self):
        reply = message(47881, to=ME, reply_to=47879, type='communication.reply',
            body={'request_id': 'grok-blender-roundtrip-47870-20261019-r1'})
        out = m.inspect_batch({'messages': [reply]}, ME, probe_id=47879, expected_sender='blender-team',
            request_id='grok-blender-roundtrip-47870-20261019-r1')
        self.assertEqual(out['correlated_replies'][0]['status'], 'CORRELATED_EVIDENCE_ONLY')
        self.assertEqual(out['correlated_replies'][0]['kind'], 'REPLY_CONTENT_UNVERIFIED')
        self.assertIsNone(out['parent_read'])
        self.assertEqual(out['unhandled_ids'], [47881])
        wrong = m.inspect_batch({'messages': [reply]}, ME, probe_id=47879,
            expected_sender='blender-team', request_id='different-request')
        self.assertEqual(wrong['correlated_replies'][0]['status'], 'UNCONFIRMED')

    def test_ack_requires_consistent_id_and_expected_sender_but_is_not_acceptance(self):
        for sender, body_id, expected in [('blender-team', 7, 'CORRELATED_EVIDENCE_ONLY'),
            ('another-team', 7, 'UNCONFIRMED'), ('blender-team', 8, 'UNCONFIRMED')]:
            msg = message(10, to=ME, type='ack', reply_to=7, body={'id': body_id}, **{'from': sender})
            out = m.inspect_batch({'messages': [msg]}, ME, probe_id=7, expected_sender='blender-team')
            self.assertEqual(out['correlated_replies'][0]['status'], expected)
            self.assertEqual(out['correlated_replies'][0]['kind'], 'BROKER_ACK_ONLY')
            self.assertEqual(out['unhandled_ids'], [])

    def test_conflicting_duplicate_or_malformed_batch_refuses_without_consuming(self):
        for records in ([message(), message(body={'text': 'changed'})], [{'id': 1}], [message(reply_to=True)]):
            with self.assertRaises(ValueError): m.inspect_batch({'messages': records}, ME)

    def test_mentions_are_exact_hints_and_duplicate_observation_is_deduplicated(self):
        records = [message(body={'text': '@pootscoot-coordination-extra'}), message(2, to=ME)]
        records.append(copy.deepcopy(records[-1]))
        out = m.inspect_batch({'messages': records}, ME)
        self.assertEqual(out['mention_only'], [])
        self.assertEqual(out['unhandled_ids'], [2])


if __name__ == '__main__':
    unittest.main(verbosity=2)
