# SPDX-License-Identifier: MIT
"""Real HTTP, durable restart and delivery-failure checks for agent-side handoffs."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_pipeline import live_handoff as live, teamlink


class HandoffTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.broker = teamlink.Broker(str(self.root/'hub'))
        self.server = teamlink.ThreadingHTTPServer(('127.0.0.1', 0), teamlink.make_handler(self.broker))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.a = teamlink.Link('a', self.server.server_port)
        self.b = teamlink.Link('b', self.server.server_port)
        self.path = self.root/'b.json'
        self.state = dict(version=1, me='b', cursor=0, pending={}, outgoing={})

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.directory.cleanup()

    def put(self, text='please build'):
        return self.a.send('b', 'request', {'text': text})

    def test_collect_never_acknowledges_or_claims_acceptance(self):
        mid = self.put(); live.collect(self.state, self.b)
        self.assertEqual(self.state['pending'][str(mid)]['state'], 'queued')
        self.assertNotIn(('b', mid), self.broker.acked)
        self.assertEqual(live.summary(self.state)['pending_count'], 1)

    def test_human_ack_text_is_not_hidden_as_a_transport_receipt(self):
        mid = self.a.send('b', 'ack', {'text':'Recovery complete; heads ready'}, reply_to=99)
        live.collect(self.state, self.b)
        self.assertIn(str(mid), self.state['pending'])
        self.assertEqual(live.summary(self.state)['messages'][0]['text'], 'Recovery complete; heads ready')

    def test_only_pure_broker_receipts_are_filtered(self):
        mid = self.put(); self.b.ack(mid)
        state = dict(version=1, me='a', cursor=mid, pending={}, outgoing={})
        live.collect(state, self.a)
        self.assertEqual(state['pending'], {})
        meaningful = self.b.send('a', 'ack', {'id':mid,'text':'build started'}, reply_to=mid)
        live.collect(state, self.a)
        self.assertIn(str(meaningful), state['pending'])

    def test_non_object_body_is_visible_instead_of_crashing_summary(self):
        mid = self.broker.send('a','b','note','plain text')
        live.collect(self.state, self.b)
        self.assertEqual(live.summary(self.state)['messages'][0]['text'], 'plain text')

    def test_explicit_response_reaches_sender_and_ack_is_separate(self):
        mid = self.put(); live.collect(self.state, self.b)
        live.respond(self.state, self.b, mid, 'accepted', 'building now')
        response = next(m for m in self.broker.messages if m['type']=='request.accepted')
        self.assertEqual(response['reply_to'], mid)
        self.assertEqual(response['from'], 'b')
        self.assertIn(('b', mid), self.broker.acked)
        self.assertEqual(live.summary(self.state)['pending_count'], 1)
        live.respond(self.state, self.b, mid, 'completed', 'build proof attached')
        self.assertEqual(live.summary(self.state)['pending_count'], 0)
        with self.assertRaises(ValueError):
            live.respond(self.state, self.b, mid, 'accepted', 'backwards')

    def test_response_retry_deduplicates_but_resume_is_a_new_event(self):
        mid = self.put(); live.collect(self.state, self.b)
        first = live.respond(self.state, self.b, mid, 'accepted', 'building')
        self.assertEqual(live.respond(self.state, self.b, mid, 'accepted', 'building'), first)
        live.respond(self.state, self.b, mid, 'blocked', 'missing file')
        resumed = live.respond(self.state, self.b, mid, 'accepted', 'building')
        self.assertNotEqual(first, resumed)

    def test_restart_preserves_unread_messages_and_cursor(self):
        mid = self.put()
        with live.locked_state(self.path, 'b', 0) as state:
            live.collect(state, self.b)
        with live.locked_state(self.path, 'b') as state:
            self.assertIn(str(mid), state['pending'])
            self.assertEqual(state['cursor'], mid)
            live.collect(state, self.b)
            self.assertEqual(len(state['pending']), 1)

    def test_bootstrap_and_identity_are_explicit(self):
        with self.assertRaises(ValueError):
            with live.locked_state(self.path, 'b'):
                pass
        with live.locked_state(self.path, 'b', 0):
            pass
        with self.assertRaises(ValueError):
            with live.locked_state(self.path, 'different'):
                pass

    def test_backpressure_does_not_skip_an_unretained_request(self):
        first, second = self.put('one'), self.put('two')
        with patch.object(live, 'MAX_PENDING', 1):
            live.collect(self.state, self.b)
        self.assertEqual(self.state['cursor'], first)
        self.assertNotIn(str(second), self.state['pending'])
        self.state['pending'].clear(); live.collect(self.state, self.b)
        self.assertIn(str(second), self.state['pending'])

    def test_ordinary_receipt_does_not_satisfy_acceptance_deadline(self):
        sender = dict(version=1, me='a', cursor=0, pending={}, outgoing={})
        item = live.request(sender, self.a, 'build', 'b', 'build now', 30, now=100)
        mid = live.send_request(item, self.a)
        self.b.ack(mid); live.collect(sender, self.a)
        self.assertEqual(item['state'], 'received')
        self.assertTrue(live.summary(sender, now=131)['requests'][0]['acceptance_overdue'])
        self.b.send('a', 'request.accepted', {'text':'on it'}, reply_to=mid)
        live.collect(sender, self.a)
        self.assertEqual(item['state'], 'accepted')
        self.assertFalse(live.summary(sender, now=132)['requests'][0]['acceptance_overdue'])

    def test_wrong_logical_sender_does_not_satisfy_target_reply(self):
        sender = dict(version=1, me='a', cursor=0, pending={}, outgoing={})
        item = live.request(sender, self.a, 'build', 'b', 'build now')
        mid = live.send_request(item, self.a)
        self.broker.send('c', 'a', 'request.completed', {'text':'fake'}, reply_to=mid)
        live.collect(sender, self.a)
        self.assertEqual(item['state'], 'sent')

    def test_request_retry_after_lost_http_confirmation_is_one_message(self):
        path = self.root/'a.json'
        with live.locked_state(path, 'a', 0) as state:
            live.request(state, self.a, 'stable', 'b', 'build')
        original = self.a._call
        def lose_response(method, route, *args, **kwargs):
            result = original(method, route, *args, **kwargs)
            return None if route == '/v1/messages' else result
        with self.assertRaises(ConnectionError):
            with live.locked_state(path, 'a') as state, patch.object(self.a, '_call', side_effect=lose_response):
                live.send_request(state['outgoing']['stable'], self.a)
        with live.locked_state(path, 'a') as state:
            live.send_request(state['outgoing']['stable'], self.a)
        self.assertEqual(len([m for m in self.broker.messages if m['type']=='request']), 1)

    def test_failed_poll_preserves_cursor(self):
        with patch.object(self.b, '_call', return_value=None), self.assertRaises(ConnectionError):
            live.collect(self.state, self.b)
        self.assertEqual(self.state['cursor'], 0)

    def test_os_lock_rejects_competing_writers_and_old_file_does_not_block(self):
        with live.locked_state(self.path, 'b', 0):
            with self.assertRaises(OSError):
                with live.locked_state(self.path, 'b', 0):
                    pass
        self.assertTrue(Path(str(self.path)+'.lock').exists())
        with live.locked_state(self.path, 'b') as state:
            self.assertEqual(state['cursor'], 0)

    def test_uncertain_response_retries_the_saved_envelope(self):
        mid = self.put()
        with live.locked_state(self.path, 'b', 0) as state:
            live.collect(state, self.b)
            live.prepare_response(state, self.b, mid, 'accepted', 'building')
        original = self.b._call
        def lose_response(method, route, *args, **kwargs):
            result = original(method, route, *args, **kwargs)
            return None if route == '/v1/messages' else result
        with self.assertRaises(ConnectionError):
            with live.locked_state(self.path, 'b') as state, patch.object(self.b, '_call', side_effect=lose_response):
                live.respond(state, self.b, mid, 'accepted', 'building')
        with live.locked_state(self.path, 'b') as state:
            live.respond(state, self.b, mid, 'accepted', 'building')
        self.assertEqual(len([m for m in self.broker.messages if m['type']=='request.accepted']), 1)

    def test_new_queued_request_precedes_already_accepted_work(self):
        old = self.put('accepted work'); live.collect(self.state, self.b)
        live.respond(self.state, self.b, old, 'accepted', 'working')
        new = self.put('new question'); live.collect(self.state, self.b)
        self.assertEqual(live.summary(self.state)['messages'][0]['id'], new)

    def test_oversized_request_is_rejected_before_persisting_outgoing(self):
        with self.assertRaises(ValueError):
            live.request(self.state, self.b, 'big', 'a', 'x'*16001)
        self.assertEqual(self.state['outgoing'], {})

    def test_long_poll_wakes_on_real_delivery(self):
        threading.Timer(.08, self.put).start()
        start = time.monotonic()
        messages, _ = self.b.wait(0, 2)
        elapsed = time.monotonic()-start
        self.assertEqual(messages[0]['type'], 'request')
        self.assertLess(elapsed, 1)

    def test_batch_responses_correlate_and_retry_after_partial_delivery(self):
        ids = [self.put('first'), self.put('second')]
        live.collect(self.state, self.b)
        with live.locked_state(self.path, 'b', 0) as state:
            state.update(self.state)
        args = ['--me','b','--state',str(self.path),'--port',str(self.server.server_port),
                'respond','--id',str(ids[0]),'--id',str(ids[1]),'--id',str(ids[0]),
                '--status','accepted','--text','owning both; building now']
        original = live.deliver
        def fail_second(link, envelope):
            if envelope['reply_to'] == str(ids[1]):
                raise ConnectionError('simulated interruption')
            return original(link, envelope)
        with patch.object(live, 'deliver', side_effect=fail_second):
            with self.assertRaises(ConnectionError):
                live.main(args)
        with contextlib.redirect_stdout(io.StringIO()):
            live.main(args)
            live.main(args)
        responses = [m for m in self.broker.messages if m['type']=='request.accepted']
        self.assertEqual([m['reply_to'] for m in responses], ids)
        self.assertEqual(len(responses), 2)

    def test_batch_invalid_id_sends_nothing(self):
        mid = self.put(); live.collect(self.state, self.b)
        with live.locked_state(self.path, 'b', 0) as state:
            state.update(self.state)
        with self.assertRaises(ValueError):
            live.main(['--me','b','--state',str(self.path),'--port',str(self.server.server_port),
                       'respond','--id',str(mid),'--id','999999',
                       '--status','accepted','--text','building'])
        self.assertFalse(any(m['type']=='request.accepted' for m in self.broker.messages))

    def test_cli_request_poll_and_response_work_with_real_state_files(self):
        def run(me, path, *args):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                live.main(['--me', me, '--state', str(path), '--port', str(self.server.server_port),
                           '--start-after', '0', *args])
            return json.loads(output.getvalue())
        a_path = self.root/'a.json'
        result = run('a', a_path, 'request', '--to','b','--key','one','--text','build')
        mid = result['requests'][0]['id']
        result = run('b', self.path, 'poll')
        self.assertEqual(result['messages'][0]['id'], mid)
        run('b', self.path, 'respond', '--id',str(mid),'--status','accepted','--text','building')
        result = run('a', a_path, 'poll')
        self.assertEqual(result['requests'][0]['state'], 'accepted')
        result = run('b', self.path, 'replay', '--after','0')
        self.assertEqual(result['cursor'], 0)
        result = run('b', self.path, 'poll')
        self.assertEqual(result['pending_count'], 1)
        self.assertEqual(result['messages'][0]['state'], 'accepted')


if __name__ == '__main__':
    unittest.main(verbosity=2)
