# SPDX-License-Identifier: MIT
"""Large-response fault fixtures using the real HTTP parser, without sockets.

The injected resets reproduce the observed failure boundary and accounting, not
the Unreal server's unproven reason for resetting. Payloads are synthetic JSON,
not captured images. No native call, listener, timer, or automatic replay runs.
"""
import http.client
import io
import json
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from tools.unreal_mcp import capture, transport


OBSERVED_PREFIXES = ((3470375, 3512149), (2946200, 3008399), (3010190, 3064801))


def json_body(length, request_id=2):
    reply = {"jsonrpc": "2.0", "id": request_id, "result": {"synthetic": ""}}
    overhead = len(json.dumps(reply, separators=(",", ":")).encode())
    reply["result"]["synthetic"] = "x" * (length - overhead)
    body = json.dumps(reply, separators=(",", ":")).encode()
    assert len(body) == length
    return body


class ScriptedRaw(io.RawIOBase):
    """A socket-like raw stream whose tail can end, reset, or time out.

    BufferedReader is deliberately real: header read-ahead and discarded bytes
    on a blocking read failure must not be hidden by a fake Response.read().
    """
    def __init__(self, wire, ending="eof", fragments=(4093, 16381, 65536)):
        super().__init__()
        self.wire, self.ending, self.fragments = wire, ending, fragments
        self.position = 0
        self.read_sizes = []
        self.faults = 0
        self.on_read = None

    def readable(self):
        return True

    def readinto(self, target):
        self.read_sizes.append(len(target))
        if self.on_read is not None:
            self.on_read(self.position == len(self.wire))
        if self.position == len(self.wire):
            if self.ending == "reset":
                self.faults += 1
                raise ConnectionResetError(10054, "synthetic peer reset")
            if self.ending == "timeout":
                self.faults += 1
                raise TimeoutError("synthetic read timeout")
            return 0
        fragment = self.fragments[(len(self.read_sizes) - 1) % len(self.fragments)]
        count = min(len(target), fragment, len(self.wire) - self.position)
        target[:count] = self.wire[self.position:self.position + count]
        self.position += count
        return count


def http_response(body, *, prefix=None, ending="eof", declared=True,
                  chunked=False, terminator=True, content_type="application/json"):
    headers = ["HTTP/1.1 200 OK", "Content-Type: " + content_type,
               "Mcp-Session-Id: synthetic-session", "Connection: close"]
    if chunked:
        headers.append("Transfer-Encoding: chunked")
        pieces = []
        for offset in range(0, len(body), 8191):
            piece = body[offset:offset + 8191]
            pieces.append(("%x\r\n" % len(piece)).encode() + piece + b"\r\n")
        encoded = b"".join(pieces) + (b"0\r\n\r\n" if terminator else b"")
    else:
        if declared:
            headers.append("Content-Length: " + str(len(body)))
        encoded = body if prefix is None else body[:prefix]
    wire = ("\r\n".join(headers) + "\r\n\r\n").encode() + encoded
    raw = ScriptedRaw(wire, ending=ending)
    buffered = io.BufferedReader(raw)

    class MemorySocket:
        def makefile(self, mode):
            assert mode == "rb"
            return buffered

    response = http.client.HTTPResponse(MemorySocket(), method="POST")
    response.begin()
    return response, raw


class LargeCaptureTransferTests(unittest.TestCase):
    def assert_unknown(self, failure, received, expected):
        data = getattr(failure, "data", failure)
        self.assertEqual(data["stage"], "response_body")
        self.assertEqual(data["receivedBytes"], received)
        self.assertEqual(data["expectedBytes"], expected)
        self.assertEqual(data["outcome"], "unknown")
        self.assertIs(data["retryable"], False)
        self.assertIs(data["replayed"], False)

    def test_real_http_reader_counts_observed_prefix_before_reset(self):
        for received, expected in OBSERVED_PREFIXES:
            body = json_body(expected)
            for chunk_size in (4096, 65536, 262144):
                with self.subTest(received=received, expected=expected, chunk=chunk_size):
                    response, raw = http_response(body, prefix=received, ending="reset")
                    with response, self.assertRaises(transport.TransportFailure) as error:
                        transport.read_response(response, chunk_bytes=chunk_size, request_id=2)
                    self.assert_unknown(error.exception, received, expected)
                    self.assertIsInstance(error.exception.__cause__, ConnectionResetError)
                    self.assertEqual(raw.faults, 1)

    def test_orderly_short_body_is_also_incomplete_not_success(self):
        received, expected = OBSERVED_PREFIXES[0]
        response, raw = http_response(json_body(expected), prefix=received)
        with response, self.assertRaises(transport.TransportFailure) as error:
            transport.read_response(response, request_id=2)
        self.assert_unknown(error.exception, received, expected)
        self.assertEqual(raw.faults, 0)
        self.assertIn("Content-Length", str(error.exception))

    def test_complete_large_declared_body_does_not_read_past_its_frame(self):
        # A 4.1 MB PNG expands beyond 5 MB in a native base64 JSON response.
        for size in (3512149, 6 * 1024 * 1024):
            with self.subTest(size=size):
                response, raw = http_response(json_body(size), ending="reset")
                with response:
                    reply = transport.read_response(response, request_id=2)
                self.assertEqual(reply["id"], 2)
                self.assertEqual(len(json.dumps(reply, separators=(",", ":")).encode()), size)
                self.assertEqual(raw.position, len(raw.wire))
                self.assertEqual(raw.faults, 0, "the peer's later reset is outside the declared frame")

    def test_chunked_complete_large_body_needs_terminal_chunk(self):
        body = json_body(3512149)
        for complete in (True, False):
            with self.subTest(terminator=complete):
                response, _ = http_response(body, chunked=True, terminator=complete)
                with response:
                    if complete:
                        self.assertEqual(transport.read_response(response, request_id=2)["id"], 2)
                    else:
                        with self.assertRaises(transport.TransportFailure) as error:
                            transport.read_response(response, request_id=2)
                        self.assert_unknown(error.exception, len(body), None)

    def test_close_delimited_sse_distinguishes_event_and_transport_completion(self):
        final = b"event: message\ndata: " + json_body(3512149) + b"\n\n"
        for ending, event_complete in (("eof", True), ("eof", False), ("reset", True)):
            with self.subTest(ending=ending, event_complete=event_complete):
                body = final if event_complete else final[:-1]
                response, _ = http_response(body, declared=False, ending=ending,
                                            content_type="text/event-stream")
                with response:
                    if ending == "eof" and event_complete:
                        self.assertEqual(transport.read_response(response, request_id=2)["id"], 2)
                    else:
                        with self.assertRaises(transport.TransportFailure) as error:
                            transport.read_response(response, request_id=2)
                        if ending == "reset":
                            self.assert_unknown(error.exception, len(body), None)
                        else:
                            self.assertEqual(error.exception.data["stage"], "response_decode")

    def test_body_timeout_and_reset_each_submit_once_without_changing_budget(self):
        received, expected = OBSERVED_PREFIXES[0]
        for ending in ("timeout", "reset"):
            with self.subTest(ending=ending):
                response, _ = http_response(json_body(expected), prefix=received, ending=ending)
                session = {"id": None}
                with patch.object(transport.urllib.request, "urlopen", return_value=response) as opening:
                    with self.assertRaises(transport.TransportFailure) as error:
                        transport.post_json("http://synthetic.invalid/mcp", {"id": 2}, session, timeout=7)
                opening.assert_called_once()
                self.assertEqual(opening.call_args.kwargs["timeout"], 7)
                self.assert_unknown(error.exception, received, expected)
                self.assertEqual(session["id"], "synthetic-session")
                self.assertEqual(error.exception.data["responseHeaders"]["Content-Length"], str(expected))
                self.assertEqual(error.exception.data["responseHeaders"]["Connection"], "close")
                self.assertIn("TimeoutError" if ending == "timeout" else "ConnectionResetError", str(error.exception))

    def test_capture_disk_destination_does_not_bypass_incomplete_http_body(self):
        received, expected = OBSERVED_PREFIXES[0]
        initialization, _ = http_response(b'{"jsonrpc":"2.0","id":1,"result":{"name":"synthetic"}}')
        notification, _ = http_response(b"")
        failing, _ = http_response(json_body(expected), prefix=received, ending="reset")
        stderr = io.StringIO()
        with patch.object(transport.urllib.request, "urlopen",
                          side_effect=[initialization, notification, failing]) as opening, \
                patch.object(capture.sys, "stderr", stderr), \
                patch.object(capture.os, "makedirs") as folders, \
                patch("builtins.open") as writing:
            result = capture.main(["synthetic-never-written.png"])
        self.assertEqual(result, 1)
        self.assertEqual(opening.call_count, 3, "initialize, notification, and one capture")
        self.assertEqual([json.loads(call.args[0].data)["method"] for call in opening.call_args_list],
                         ["initialize", "notifications/initialized", "tools/call"])
        self.assertEqual(json.loads(opening.call_args_list[-1].args[0].data)["params"]["arguments"]["tool_name"],
                         "CaptureViewport")
        folders.assert_not_called()
        writing.assert_not_called()
        receipt = json.loads(stderr.getvalue())["data"]
        self.assert_unknown(receipt, received, expected)


class FakeClock:
    """Deterministic observation clock; advances only at scripted read events."""
    def __init__(self):
        self.value = 100.0

    def monotonic(self):
        return self.value

    def utc(self):
        origin = datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)
        return (origin + timedelta(seconds=self.value - 100)).isoformat(timespec="microseconds").replace("+00:00", "Z")

    def advance(self, seconds):
        self.value += seconds


class TransferObservationTests(unittest.TestCase):
    def post_fixture(self, response, raw, observation):
        clock = FakeClock()
        raw.on_read = lambda at_end: clock.advance(6.25 if at_end and raw.ending != "eof" else 0.125)

        def opening(request, timeout):
            clock.advance(0.25)
            return response

        with patch.object(transport.time, "monotonic", side_effect=clock.monotonic), \
                patch.object(transport, "_utc_now", side_effect=clock.utc), \
                patch.object(transport.urllib.request, "urlopen", side_effect=opening) as open_mock:
            try:
                reply = transport.post_json("http://synthetic.invalid/mcp?secret=synthetic-url-secret",
                                            {"id": 2, "params": {"private": "synthetic-payload-secret"}},
                                            {"id": "synthetic-request-session-secret"}, timeout=7,
                                            observation=observation)
                failure = None
            except transport.TransportFailure as error:
                reply, failure = None, error
        open_mock.assert_called_once()
        self.assertEqual(open_mock.call_args.kwargs["timeout"], 7)
        return reply, failure, clock

    def test_read_gap_and_transfer_times_are_measured_with_fake_clock(self):
        received, expected = OBSERVED_PREFIXES[0]
        response, raw = http_response(json_body(expected), prefix=received, ending="reset")
        observed = {}
        reply, failure, clock = self.post_fixture(response, raw, observed)
        self.assertIsNone(reply)
        self.assertIsNotNone(failure)
        self.assertEqual(observed["httpStatus"], 200)
        self.assertEqual(observed["timeoutSeconds"], 7)
        self.assertEqual(observed["secondsToHeaders"], 0.25)
        self.assertEqual(observed["maxReadSeconds"], 6.25)
        self.assertEqual(observed["elapsedSeconds"], clock.value - 100)
        self.assertEqual(observed["secondsToLastByte"], observed["elapsedSeconds"] - 6.25)
        self.assertEqual(observed["startedAt"], "2024-01-02T12:00:00.000000Z")
        self.assertEqual(observed["headersAt"], "2024-01-02T12:00:00.250000Z")
        self.assertEqual(observed["finishedAt"], clock.utc())
        self.assertEqual((observed["receivedBytes"], observed["expectedBytes"]), (received, expected))
        self.assertGreater(observed["readCalls"], 1)
        self.assertIs(observed["bodyComplete"], False)
        self.assertIs(observed["replyValidated"], False)
        self.assertEqual(failure.data["transfer"], observed)

    def test_complete_body_and_valid_reply_are_separate_observations(self):
        for body, valid in ((json_body(3512149), True), (b'{"jsonrpc":"2.0","id":99,"result":null}', False)):
            with self.subTest(valid_reply=valid):
                response, raw = http_response(body, ending="reset")
                observed = {}
                reply, failure, clock = self.post_fixture(response, raw, observed)
                self.assertIs(observed["bodyComplete"], True)
                self.assertIs(observed["replyValidated"], valid)
                self.assertEqual(observed["receivedBytes"], len(body))
                self.assertEqual(observed["expectedBytes"], len(body))
                self.assertEqual(observed["finishedAt"], clock.utc())
                self.assertEqual(raw.faults, 0)
                if valid:
                    self.assertEqual(reply["id"], 2)
                    self.assertIsNone(failure)
                else:
                    self.assertEqual(failure.data["stage"], "response_decode")

    def test_observation_exports_only_allowlisted_headers_and_no_private_inputs(self):
        response, raw = http_response(json_body(4096), prefix=4000, ending="reset")
        for key, value in (("Authorization", "synthetic-auth-secret"),
                           ("Set-Cookie", "synthetic-cookie-secret"),
                           ("X-Private", "synthetic-header-secret"), ("Content-Encoding", "identity")):
            response.headers[key] = value
        observed = {"oldPayload": "synthetic-caller-secret"}
        _, failure, _ = self.post_fixture(response, raw, observed)
        exported = json.dumps(failure.data, allow_nan=False)
        for private in ("synthetic-url-secret", "synthetic-payload-secret", "synthetic-request-session-secret",
                        "synthetic-session", "synthetic-auth-secret", "synthetic-cookie-secret",
                        "synthetic-header-secret", "synthetic-caller-secret"):
            self.assertNotIn(private, exported)
        self.assertEqual(set(failure.data["responseHeaders"]),
                         {"Content-Type", "Content-Length", "Transfer-Encoding", "Connection", "Content-Encoding"})
        self.assertEqual(failure.data["responseHeaders"]["Content-Encoding"], "identity")

    def test_saved_failure_trace_survives_reuse_of_client_observation_dictionary(self):
        response, raw = http_response(json_body(4096), prefix=4000, ending="reset")
        observed = {}
        _, failure, _ = self.post_fixture(response, raw, observed)
        first_receipt = dict(failure.data["transfer"])
        second, second_raw = http_response(json_body(512))
        reply, second_failure, _ = self.post_fixture(second, second_raw, observed)
        self.assertEqual(reply["id"], 2)
        self.assertIsNone(second_failure)
        self.assertIs(observed["bodyComplete"], True)
        self.assertEqual(failure.data["transfer"], first_receipt,
                         "a later explicit read must not rewrite the saved failure's evidence")


if __name__ == "__main__":
    unittest.main()
