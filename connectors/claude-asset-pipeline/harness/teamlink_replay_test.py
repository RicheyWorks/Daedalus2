# SPDX-License-Identifier: MIT
"""Focused cold-start replay and unavailable-service tests; no live service/editor.

The historical string ACK below is the unchanged raw row from log.jsonl, ID48029.
Tests operate exclusively on temporary copies. Socket servers, threads and process
launches are mocked where startup is exercised; the real persisted log is never read
or changed by this test module.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_pipeline import teamlink  # noqa: E402


HISTORICAL_STRING_ACK = (
    b'{"id": 48029, "ts": "2026-10-19T00:09:13", "from": "art-master-flex", '
    b'"to": "pootscoot-coordination", "type": "ack", "body": "ACK 48021", "reply_to": 48021}\r\n'
)
HISTORICAL_SHA256 = "f70c0b0413aedd4abc3982f8afc252b0b5aef7beb5c9bda9ebc43fc15a3c1a24"


def message(mid, kind="ping", body=None, sender="pootscoot-coordination", recipient="art-master-flex"):
    return {"id": mid, "ts": "2026-10-19T00:09:12", "from": sender, "to": recipient,
            "type": kind, "body": {} if body is None else body, "reply_to": None}


def encoded(row):
    return json.dumps(row).encode("utf-8") + b"\r\n"


class ReplayStartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="teamlink-replay-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.log = self.folder / "log.jsonl"

    def history(self, suffix=b""):
        raw = encoded(message(48021)) + HISTORICAL_STRING_ACK + suffix
        self.log.write_bytes(raw)
        return raw

    def no_launches(self):
        stack = contextlib.ExitStack()
        for owner, attribute in ((subprocess, "Popen"), (os, "system"), (os, "startfile")):
            stack.enter_context(mock.patch.object(owner, attribute, create=True,
                side_effect=AssertionError("process/editor launch forbidden in focused tests")))
        return stack

    def test_exact_historical_string_ack_preserved_without_receipt_inference(self):
        self.assertEqual(hashlib.sha256(HISTORICAL_STRING_ACK).hexdigest(), HISTORICAL_SHA256)
        raw = self.history()
        broker = teamlink.Broker(str(self.folder))
        self.assertEqual(self.log.read_bytes(), raw)
        self.assertEqual(broker.last, 48029)
        self.assertEqual(broker.messages[-1], json.loads(HISTORICAL_STRING_ACK))
        self.assertEqual(broker.acked, set())
        self.assertEqual([row["id"] for row in broker.pending("art-master-flex")], [48021])

    def test_structured_object_ack_restores_receipt_beside_legacy_string(self):
        receipt = message(48030, "ack", {"id": 48021, "type": "ping"},
                          "art-master-flex", "pootscoot-coordination")
        receipt["reply_to"] = 48021
        raw = self.history(encoded(receipt))
        broker = teamlink.Broker(str(self.folder))
        self.assertEqual(broker.acked, {("art-master-flex", 48021)})
        self.assertEqual(broker.pending("art-master-flex"), [])
        self.assertEqual(broker.last, 48030)
        self.assertEqual(self.log.read_bytes(), raw)

    def test_malformed_ack_bodies_or_ids_never_create_receipts(self):
        bodies = [None, False, True, 48021, [48021], {"id": None}, {"id": True},
                  {"id": 48021.0}, {"id": "48021"}, {"id": []}, {"id": {}},
                  {"id": 0}, {"id": -1}, {}, "{\"id\": 48021}"]
        rows = []
        for offset, body in enumerate(bodies):
            row = message(48030 + offset, "ack", {}, "art-master-flex", "pootscoot-coordination")
            row["body"], row["reply_to"] = body, 48021
            rows.append(encoded(row))
        raw = self.history(b"".join(rows))
        broker = teamlink.Broker(str(self.folder))
        self.assertEqual(broker.acked, set())
        self.assertEqual([row["id"] for row in broker.pending("art-master-flex")], [48021])
        self.assertEqual(self.log.read_bytes(), raw)

    def test_invalid_receipt_sender_is_not_promoted_to_state(self):
        rows = [encoded(message(48030 + index, "ack", {"id": 48021}, sender,
                                "pootscoot-coordination"))
                for index, sender in enumerate((None, [], {}, ""))]
        raw = self.history(b"".join(rows))
        broker = teamlink.Broker(str(self.folder))
        self.assertEqual(broker.acked, set())
        self.assertEqual(self.log.read_bytes(), raw)

    def test_normal_generated_receipt_still_survives_cold_restart(self):
        broker = teamlink.Broker(str(self.folder))
        mid = broker.send("sender", "receiver", "note", {"text": "synthetic"})
        self.assertTrue(broker.ack("receiver", mid))
        raw = self.log.read_bytes()
        restored = teamlink.Broker(str(self.folder))
        self.assertEqual(restored.acked, {("receiver", mid)})
        self.assertFalse(restored.ack("receiver", mid))
        self.assertEqual(restored.pending("receiver"), [])
        self.assertEqual(self.log.read_bytes(), raw)

    def test_repeated_restart_preserves_history_and_next_id(self):
        raw = self.history()
        for _ in range(2):
            broker = teamlink.Broker(str(self.folder))
            self.assertEqual(broker.last, 48029)
            self.assertEqual(self.log.read_bytes(), raw)
        self.assertEqual(broker.send("synthetic", "receiver", "note", {}), 48030)
        self.assertTrue(self.log.read_bytes().startswith(raw))

    def test_empty_cold_start_does_not_launch_any_process(self):
        with self.no_launches():
            broker = teamlink.Broker(str(self.folder))
        self.assertEqual(broker.messages, [])
        self.assertEqual(broker.last, 0)
        self.assertFalse(self.log.exists())

    def test_serve_reaches_ready_once_after_replay_with_all_effects_mocked(self):
        raw = self.history()
        server = mock.Mock(server_address=("127.0.0.1", 12345))
        ready = mock.Mock()
        with self.no_launches(), mock.patch.object(teamlink, "ThreadingHTTPServer", return_value=server) as bind, \
             mock.patch.object(teamlink, "FileBridge") as bridge, \
             mock.patch.object(teamlink.threading, "Thread") as thread, contextlib.redirect_stdout(io.StringIO()):
            teamlink.serve(str(self.folder), port=12345, files=False, ready=ready)
        bind.assert_called_once()
        server.serve_forever.assert_called_once_with()
        ready.assert_called_once()
        self.assertEqual(ready.call_args.args[1].last, 48029)
        bridge.assert_not_called()
        thread.assert_not_called()
        self.assertEqual(self.log.read_bytes(), raw)

    def test_bind_unavailable_fails_immediately_without_retry_ready_or_launch(self):
        raw = self.history()
        ready = mock.Mock()
        with self.no_launches(), mock.patch.object(teamlink, "ThreadingHTTPServer",
                side_effect=OSError("synthetic port unavailable")) as bind, \
             mock.patch.object(teamlink, "FileBridge") as bridge, \
             mock.patch.object(teamlink.threading, "Thread") as thread:
            with self.assertRaisesRegex(OSError, "synthetic port unavailable"):
                teamlink.serve(str(self.folder), files=False, ready=ready)
        bind.assert_called_once()
        ready.assert_not_called()
        bridge.assert_not_called()
        thread.assert_not_called()
        self.assertEqual(self.log.read_bytes(), raw)

    def test_service_unavailable_doctor_reports_nonzero_without_starting_anything(self):
        output = io.StringIO()
        with self.no_launches(), mock.patch.object(teamlink.urllib.request, "urlopen",
                side_effect=urllib.error.URLError("synthetic refused")) as request, \
             mock.patch.object(teamlink, "Broker", side_effect=AssertionError("no implicit broker restart")), \
             mock.patch.object(teamlink, "ThreadingHTTPServer", side_effect=AssertionError("no socket bind")), \
             contextlib.redirect_stdout(output):
            result = teamlink.main(["doctor", "--me", "synthetic-replay-test"])
        report = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertFalse(report["ok"])
        self.assertFalse(report["broker_up"])
        self.assertEqual(set(report["unavailable"]), {"health", "locks", "inbox", "pending"})
        self.assertEqual(request.call_count, 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
