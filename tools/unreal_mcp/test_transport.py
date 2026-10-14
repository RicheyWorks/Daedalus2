# SPDX-License-Identifier: MIT
"""Offline transport regressions; no Unreal/editor/server calls."""
import io
import base64
import http.server
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
import urllib.error
from unittest.mock import patch

from tools.unreal_mcp import stdio_proxy, transport


class Response(io.BytesIO):
    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = headers or {}


def encoded(reply):
    return json.dumps(reply).encode("utf-8")


class TransportTests(unittest.TestCase):
    def test_complete_json_with_falsy_result_and_zero_id(self):
        reply = {"jsonrpc": "2.0", "id": 0, "result": False}
        body = encoded(reply)
        self.assertEqual(transport.read_response(Response(body, {"Content-Length": str(len(body))}),
                                                request_id=0), reply)

    def test_boolean_id_does_not_match_integer(self):
        with self.assertRaises(transport.TransportFailure):
            transport.read_response(Response(encoded({"jsonrpc": "2.0", "id": False,
                                                       "result": {}})), request_id=0)

    def test_wrong_id_is_not_forwarded(self):
        with self.assertRaises(transport.TransportFailure):
            transport.read_response(Response(encoded({"jsonrpc": "2.0", "id": 9,
                                                       "result": {}})), request_id=8)

    def test_json_rpc_error_retained(self):
        reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32601, "message": "missing"}}
        self.assertEqual(transport.read_response(Response(encoded(reply)), request_id=None), reply)

    def test_notification_no_content_is_valid(self):
        with patch.object(transport.urllib.request, "urlopen", return_value=Response(b"")) as opening:
            self.assertIsNone(transport.post_json("http://unused.invalid/mcp",
                                                 {"jsonrpc": "2.0", "method": "notifications/initialized"},
                                                 {"id": None}))
        self.assertEqual(opening.call_count, 1)

    def test_requested_reply_cannot_be_empty(self):
        with patch.object(transport.urllib.request, "urlopen", return_value=Response(b"")) as opening:
            with self.assertRaises(transport.TransportFailure):
                transport.post_json("http://unused.invalid/mcp", {"id": 0}, {"id": None})
        self.assertEqual(opening.call_count, 1)

    def test_multiline_sse_progress_then_matching_reply(self):
        data = (': heartbeat\n\nevent: message\ndata: {"jsonrpc":"2.0",'
                '"method":"notifications/progress","params":{}}\n\n'
                'event: message\ndata: {"jsonrpc":"2.0",\ndata: "id":0,"result":[]}\n\n').encode()
        self.assertEqual(transport.read_response(Response(data), request_id=0),
                         {"jsonrpc": "2.0", "id": 0, "result": []})

    def test_sse_unrelated_final_cannot_fake_a_reply(self):
        data = b'data: {"jsonrpc":"2.0","id":1,"result":null}\n\n'
        with self.assertRaises(transport.TransportFailure):
            transport.read_response(Response(data), request_id=0)

    def test_unterminated_sse_event_is_not_a_complete_reply(self):
        for suffix in (b"", b"\n"):
            with self.subTest(suffix=suffix), self.assertRaises(transport.TransportFailure):
                transport.read_response(Response(b'data: {"jsonrpc":"2.0","id":0,"result":false}'
                                                 + suffix), request_id=0)

    def test_malformed_error_cannot_fake_a_response(self):
        for error in (None, {}, {"code": True, "message": "bad"},
                      {"code": -1, "message": None}):
            with self.subTest(error=error), self.assertRaises(transport.TransportFailure):
                transport.read_response(Response(encoded({"jsonrpc": "2.0", "id": 0,
                                                           "error": error})), request_id=0)

    def test_invalid_utf8_is_not_replaced_in_image_data(self):
        with self.assertRaises(transport.TransportFailure) as error:
            transport.read_response(Response(b'\xff'))
        self.assertEqual(error.exception.data["receivedBytes"], 1)

    def test_valid_json_prefix_with_missing_body_is_rejected(self):
        data = encoded({"jsonrpc": "2.0", "id": 0, "result": {}})
        with self.assertRaises(transport.TransportFailure) as error:
            transport.read_response(Response(data, {"Content-Length": str(len(data) + 1)}),
                                    request_id=0)
        self.assertEqual(error.exception.data["receivedBytes"], len(data))

    def test_invalid_content_length_rejected_without_reading(self):
        for value in ("-1", "wat", "1, 2", "١"):
            response = Response(b"secret", {"Content-Length": value})
            with self.subTest(value=value), self.assertRaises(transport.TransportFailure):
                transport.read_response(response)
            self.assertEqual(response.tell(), 0)

    def test_session_header_survives_body_reset(self):
        class Reset(Response):
            def read1(self, size):
                raise ConnectionResetError(10054, "connection reset")
        session = {"id": "old"}
        with patch.object(transport.urllib.request, "urlopen",
                          return_value=Reset(b"", {"Mcp-Session-Id": "new"})) as opening:
            with self.assertRaises(transport.TransportFailure) as error:
                transport.post_json("http://unused.invalid/mcp", {"id": 0}, session)
        self.assertEqual(session["id"], "new")
        self.assertEqual(opening.call_count, 1)
        self.assertEqual(error.exception.data["stage"], "response_body")

    def test_http_error_json_rpc_preserved_without_retry(self):
        reply = {"jsonrpc": "2.0", "id": 0, "error": {"code": -32000, "message": "busy"}}
        error = urllib.error.HTTPError("http://unused.invalid", 409, "busy", {}, io.BytesIO(encoded(reply)))
        with patch.object(transport.urllib.request, "urlopen", side_effect=error) as opening:
            self.assertEqual(transport.post_json("http://unused.invalid", {"id": 0}, {"id": None}), reply)
        self.assertEqual(opening.call_count, 1)

    def test_stdio_response_reset_keeps_unknown_outcome_and_no_replay(self):
        failure = transport.TransportFailure("response_body", "reset", 1234, 1000000)
        request = {"jsonrpc": "2.0", "id": 0, "method": "tools/call"}
        output = io.StringIO()
        with patch.object(stdio_proxy, "post", side_effect=failure) as call, \
                patch.object(stdio_proxy.sys, "stdin", io.StringIO(json.dumps(request) + "\n")), \
                patch.object(stdio_proxy.sys, "stdout", output):
            stdio_proxy.main()
        reply = json.loads(output.getvalue())
        self.assertEqual(call.call_count, 1)
        self.assertEqual(reply["id"], 0)
        self.assertNotIn("not reachable", reply["error"]["message"])
        self.assertEqual(reply["error"]["data"], failure.data)

    def test_submission_reset_never_retries(self):
        with patch.object(transport.urllib.request, "urlopen", side_effect=ConnectionResetError(10054, "reset")) as opening:
            with self.assertRaises(transport.TransportFailure) as error:
                transport.post_json("http://unused.invalid", {"id": 0}, {"id": None})
        self.assertEqual(opening.call_count, 1)
        self.assertFalse(error.exception.data["retryable"])

    def test_capture_cli_reports_transfer_evidence_without_writing_or_replay(self):
        from tools.unreal_mcp import capture
        error = transport.TransportFailure("response_body", "reset", 1234, 1000000)
        error.data["responseHeaders"] = {"Content-Type": "application/json"}
        stderr = io.StringIO()
        with patch.object(capture, "Mcp") as client, patch.object(capture.sys, "stderr", stderr), \
                patch("builtins.open") as writing:
            client.return_value.call.side_effect = error
            self.assertEqual(capture.main(["unused.png"]), 1)
        self.assertEqual(client.return_value.call.call_count, 1)
        writing.assert_not_called()
        self.assertEqual(json.loads(stderr.getvalue())["data"], error.data)

    def test_one_mib_native_image_crosses_loopback_http_and_stdio_subprocess(self):
        # An ephemeral fixture server exercises urllib/socket/pipe behavior. It
        # does not contact Unreal or represent a real captured viewport.
        from tools.unreal_mcp.test_capture_proxy import PNG, capture_request, native_reply
        payload = encoded(native_reply())
        calls = []

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                calls.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Transfer-Encoding", "chunked")
                self.send_header("Connection", "close")
                self.end_headers()
                for offset in range(0, len(payload), 8192):
                    piece = payload[offset:offset + 8192]
                    self.wfile.write(("%x\r\n" % len(piece)).encode("ascii") + piece + b"\r\n")
                self.wfile.write(b"0\r\n\r\n")

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = "http://127.0.0.1:%d/mcp" % server.server_port
        try:
            run = subprocess.run([sys.executable, "-c",
                                  "from tools.unreal_mcp import stdio_proxy as p; p.URL=%r; p.main()" % url],
                                 input=json.dumps(capture_request()) + "\n", text=True,
                                 capture_output=True, timeout=10,
                                 cwd=Path(__file__).resolve().parents[2])
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(calls, [capture_request()])
            reply = json.loads(run.stdout)
            self.assertNotIn("error", reply, reply.get("error"))
            image = reply["result"]["content"][0]
            self.assertEqual(image["type"], "image")
            self.assertEqual(image["mimeType"], "image/png")
            self.assertEqual(base64.b64decode(image["data"], validate=True), PNG)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
