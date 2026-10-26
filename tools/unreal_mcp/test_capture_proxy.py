# SPDX-License-Identifier: MIT
"""Offline native capture transport contracts: memory readers and a synthetic PNG.

No server, editor, capture, sockets, GPU, or output image files are used.
Run: python -B tools/unreal_mcp/test_capture_proxy.py
"""
import base64
import copy
import http.client
import io
import json
import random
import struct
import unittest
from unittest.mock import patch
import zlib

if __package__:
    from tools.unreal_mcp import stdio_proxy, transport
else:
    import transport
    import stdio_proxy


def png_chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload +
            struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))


def synthetic_png():
    """A valid 512x384 RGBA PNG whose base64 is approximately one MiB."""
    width, height = 512, 384
    pixels = random.Random(29760).randbytes(width * height * 4)
    rows = b"".join(b"\0" + pixels[y * width * 4:(y + 1) * width * 4]
                    for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" +
            png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) +
            png_chunk(b"IDAT", zlib.compress(rows)) + png_chunk(b"IEND", b""))


PNG = synthetic_png()
PNG_BASE64 = base64.b64encode(PNG).decode("ascii")
AUTO_LENGTH = object()


def envelope(result, request_id=0):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def capture_request(request_id=0):
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": {
        "name": "call_tool", "arguments": {
            "toolset_name": "EditorToolset.EditorAppToolset",
            "tool_name": "CaptureViewport", "arguments": {
                "annotations": {"maxLabels": 12}, "bShowUI": False}}}}


def capture_value():
    # Preserve null, false, zero and empty collections; annotations are not recomputed.
    return {"returnValue": {
        "image": {"mimeType": "image/png", "data": PNG_BASE64},
        "cameraLocation": {"x": 0.004, "y": 0, "z": -7},
        "cameraRotation": {"pitch": 0, "yaw": 90, "roll": 0},
        "cameraFOV": 0,
        "grid": {"spacingCm": 0, "extentCm": 0, "height": 0},
        "labeledActors": [], "selected": False, "parent": None,
    }}


def native_reply(is_error=False):
    return envelope({"isError": is_error, "content": [
        {"type": "text", "text": json.dumps(capture_value())}]})


class MemoryResponse:
    """Bounded read interface; events can inject a reset after a known byte prefix."""
    def __init__(self, data=b"", length=AUTO_LENGTH, content_type="application/json", events=None):
        self.events = list(events) if events is not None else [data]
        self.headers = {"Content-Type": content_type}
        if length is AUTO_LENGTH:
            self.headers["Content-Length"] = str(len(data))
        elif length is not None:
            self.headers["Content-Length"] = str(length)
        self.read_sizes, self.delivered = [], 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True

    def read(self, size):
        if not isinstance(size, int) or size <= 0:
            raise AssertionError("transport must make bounded positive byte reads")
        self.read_sizes.append(size)
        if not self.events:
            return b""
        current = self.events[0]
        if isinstance(current, BaseException):
            self.events.pop(0)
            raise current
        result = current[:size]
        if len(current) <= size:
            self.events.pop(0)
        else:
            self.events[0] = current[size:]
        self.delivered += len(result)
        return result


class ResponseTests(unittest.TestCase):
    def failure(self, response, **kwargs):
        with self.assertRaises(transport.TransportFailure) as caught:
            transport.read_response(response, **kwargs)
        data = caught.exception.data
        self.assertIsInstance(data["stage"], str)
        self.assertTrue(data["stage"])
        self.assertEqual(data["outcome"], "unknown")
        self.assertIs(data["retryable"], False)
        self.assertIs(data["replayed"], False)
        self.assertIn("receivedBytes", data)
        self.assertIn("expectedBytes", data)
        return data

    def test_native_json_text_one_mib_is_preserved_across_small_reads(self):
        expected = native_reply()
        raw = json.dumps(expected).encode()
        response = MemoryResponse(raw)
        self.assertEqual(transport.read_response(response, chunk_bytes=4093, request_id=0), expected)
        self.assertGreater(len(response.read_sizes), 200)
        self.assertLessEqual(max(response.read_sizes), 4093)
        self.assertEqual(response.delivered, len(raw))

    def test_standard_mcp_image_one_mib_is_preserved(self):
        expected = envelope({"content": [
            {"type": "image", "mimeType": "image/png", "data": PNG_BASE64},
            {"type": "text", "text": "offline annotation metadata"}]})
        response = MemoryResponse(json.dumps(expected).encode())
        observed = transport.read_response(response, request_id=0)
        self.assertEqual(observed, expected)
        self.assertEqual(base64.b64decode(observed["result"]["content"][0]["data"], validate=True), PNG)

    def test_false_zero_empty_and_null_results_are_not_discarded(self):
        for value in (False, 0, [], None):
            with self.subTest(result=value):
                expected = envelope(value)
                self.assertEqual(transport.read_response(MemoryResponse(json.dumps(expected).encode()),
                                                         request_id=0), expected)

    def test_id_zero_is_checked_against_a_different_reply_id(self):
        raw = json.dumps(envelope(False, request_id=1)).encode()
        self.failure(MemoryResponse(raw), request_id=0)

    def test_declared_length_incomplete_at_eof_cannot_publish_parseable_prefix(self):
        raw = json.dumps(envelope(False)).encode()
        data = self.failure(MemoryResponse(raw, length=len(raw) + 9), request_id=0)
        self.assertEqual(data["receivedBytes"], len(raw))
        self.assertEqual(data["expectedBytes"], len(raw) + 9)

    def test_reset_after_prefix_reports_exact_received_and_expected_bytes(self):
        prefix = b'{"jsonrpc":"2.0","id":0,"result":'
        response = MemoryResponse(length=123, events=[prefix, ConnectionResetError(10054, "offline body reset")])
        data = self.failure(response, request_id=0, chunk_bytes=11)
        self.assertEqual(data["receivedBytes"], len(prefix))
        self.assertEqual(data["expectedBytes"], 123)

    def test_incomplete_read_partial_bytes_are_included_in_evidence(self):
        prefix, partial = b'{"jsonrpc":', b'"2.0","id":0'
        response = MemoryResponse(length=97, events=[prefix, http.client.IncompleteRead(partial, 30)])
        data = self.failure(response, request_id=0)
        self.assertEqual(data["receivedBytes"], len(prefix) + len(partial))
        self.assertEqual(data["expectedBytes"], 97)

    def test_announced_limit_is_rejected_before_any_body_read(self):
        response = MemoryResponse(b"unread", length=101)
        data = self.failure(response, max_response_bytes=100)
        self.assertEqual(response.read_sizes, [])
        self.assertEqual(data["receivedBytes"], 0)
        self.assertEqual(data["expectedBytes"], 101)

    def test_unannounced_limit_stops_bounded_reading(self):
        response = MemoryResponse(b"x" * 1000, length=None)
        self.failure(response, max_response_bytes=17, chunk_bytes=7)
        self.assertLessEqual(response.delivered, 18, "read at most one byte beyond the configured limit")
        self.assertLessEqual(max(response.read_sizes), 7)

    def test_exact_limit_succeeds(self):
        expected = envelope(False)
        raw = json.dumps(expected).encode()
        self.assertEqual(transport.read_response(MemoryResponse(raw), max_response_bytes=len(raw),
                                                chunk_bytes=7, request_id=0), expected)

    def test_empty_notification_response_is_none(self):
        self.assertIsNone(transport.read_response(MemoryResponse(b"")))

    def test_bad_json_and_bad_utf8_are_structured_failures(self):
        for raw in (b'{"jsonrpc":', b'\xff'):
            with self.subTest(raw=raw):
                self.failure(MemoryResponse(raw), request_id=0)

    def test_sse_progress_and_complete_final_response_keep_id_zero(self):
        expected = envelope(False)
        progress = {"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progress": 0}}
        raw = ("event: message\ndata: " + json.dumps(progress) + "\n\n" +
               "event: message\ndata: " + json.dumps(expected) + "\n\n").encode()
        self.assertEqual(transport.read_response(MemoryResponse(raw, content_type="text/event-stream"),
                                                request_id=0, chunk_bytes=5), expected)

    def test_unterminated_sse_reply_is_not_a_complete_event(self):
        for suffix in ("", "\n"):
            with self.subTest(suffix=repr(suffix)):
                raw = ("data: " + json.dumps(envelope(False)) + suffix).encode()
                self.failure(MemoryResponse(raw, content_type="text/event-stream"), request_id=0)

    def test_malformed_jsonrpc_error_is_not_a_terminal_reply(self):
        for error in (None, False, [], {"code": -32001}, {"code": "-32001", "message": "bad code"}):
            with self.subTest(error=error):
                raw = json.dumps({"jsonrpc": "2.0", "id": 0, "error": error}).encode()
                self.failure(MemoryResponse(raw), request_id=0)

    def test_jsonrpc_error_envelope_is_preserved(self):
        expected = {"jsonrpc": "2.0", "id": 0, "error": {"code": -32602, "message": "offline rejection"}}
        self.assertEqual(transport.read_response(MemoryResponse(json.dumps(expected).encode()),
                                                request_id=0), expected)


class PostTests(unittest.TestCase):
    def test_empty_request_response_is_a_failure(self):
        with patch.object(transport.urllib.request, "urlopen", return_value=MemoryResponse(b"")) as opened:
            with self.assertRaises(transport.TransportFailure) as caught:
                transport.post_json("http://offline.invalid/mcp", capture_request(), {"id": None})
        opened.assert_called_once()
        self.assertEqual(caught.exception.data["outcome"], "unknown")
        self.assertIs(caught.exception.data["retryable"], False)

    def test_post_uses_one_http_request_and_updates_the_session(self):
        expected = envelope(False)
        response = MemoryResponse(json.dumps(expected).encode())
        response.headers["Mcp-Session-Id"] = "new-offline-session"
        session = {"id": "old-offline-session"}
        with patch.object(transport.urllib.request, "urlopen", return_value=response) as opened:
            self.assertEqual(transport.post_json("http://offline.invalid/mcp", capture_request(), session,
                                                 timeout=123), expected)
        opened.assert_called_once()
        request = opened.call_args.args[0]
        self.assertEqual(json.loads(request.data), capture_request())
        self.assertEqual(dict((key.lower(), value) for key, value in request.header_items())
                         ["mcp-session-id"], "old-offline-session")
        self.assertEqual(session["id"], "new-offline-session")
        self.assertTrue(response.closed)

    def test_post_never_reopens_or_replays_after_a_body_reset(self):
        response = MemoryResponse(length=100, events=[b'{"id":0,', ConnectionResetError(10054, "offline reset")])
        with patch.object(transport.urllib.request, "urlopen", return_value=response) as opened:
            with self.assertRaises(transport.TransportFailure) as caught:
                transport.post_json("http://offline.invalid/mcp", capture_request(), {"id": None})
        opened.assert_called_once()
        self.assertEqual(caught.exception.data["receivedBytes"], 8)
        self.assertIs(caught.exception.data["retryable"], False)
        self.assertIs(caught.exception.data["replayed"], False)
        self.assertTrue(response.closed)


class CapturePresentationTests(unittest.TestCase):
    def test_png_fixture_has_valid_crc_dimensions_and_decodable_pixels(self):
        offset, kinds, compressed = 8, [], bytearray()
        self.assertEqual(PNG[:8], b"\x89PNG\r\n\x1a\n")
        while offset < len(PNG):
            size = struct.unpack(">I", PNG[offset:offset + 4])[0]
            kind = PNG[offset + 4:offset + 8]
            payload = PNG[offset + 8:offset + 8 + size]
            crc = struct.unpack(">I", PNG[offset + 8 + size:offset + 12 + size])[0]
            self.assertEqual(crc, zlib.crc32(kind + payload) & 0xffffffff)
            kinds.append(kind)
            if kind == b"IHDR":
                self.assertEqual(struct.unpack(">IIBBBBB", payload), (512, 384, 8, 6, 0, 0, 0))
            elif kind == b"IDAT":
                compressed.extend(payload)
            offset += size + 12
        self.assertEqual(kinds, [b"IHDR", b"IDAT", b"IEND"])
        self.assertEqual(len(zlib.decompress(compressed)), 384 * (1 + 512 * 4))
        self.assertGreater(len(PNG_BASE64), 1024 * 1024)
        self.assertLess(len(PNG_BASE64), 1100 * 1024)

    def test_matching_native_capture_exposes_exact_image_and_preserves_metadata(self):
        request, original = capture_request(), native_reply()
        before_request, before_reply = copy.deepcopy(request), copy.deepcopy(original)
        observed = stdio_proxy.expose_capture_image(request, original)
        self.assertEqual(original, before_reply, "presentation must not rewrite the source envelope")
        self.assertEqual(request, before_request)
        self.assertEqual(observed["id"], 0)
        self.assertIs(observed["result"]["isError"], False)
        content = observed["result"]["content"]
        self.assertEqual(len(content), 2)
        images = [(i, item) for i, item in enumerate(content) if item.get("type") == "image"]
        texts = [item for item in content if item.get("type") == "text"]
        self.assertEqual(len(images), 1)
        self.assertEqual(len(texts), 1)
        image_index, image = images[0]
        self.assertEqual(image["mimeType"], "image/png")
        self.assertEqual(image["data"], PNG_BASE64)
        self.assertEqual(base64.b64decode(image["data"], validate=True), PNG)
        metadata = json.loads(texts[0]["text"])
        expected = capture_value()
        del expected["returnValue"]["image"]["data"]
        expected["returnValue"]["image"].update(byteLength=len(PNG), contentIndex=image_index)
        self.assertEqual(metadata, expected)

    def test_matching_native_without_optional_iserror_flag_can_expose_image(self):
        original = native_reply()
        del original["result"]["isError"]
        observed = stdio_proxy.expose_capture_image(capture_request(), original)
        self.assertTrue(any(item.get("type") == "image" for item in observed["result"]["content"]))

    def test_already_standard_mcp_images_and_metadata_are_unchanged(self):
        original = envelope({"isError": False, "content": [
            {"type": "image", "mimeType": "image/png", "data": PNG_BASE64},
            {"type": "text", "text": json.dumps({"selected": False, "count": 0, "actors": [], "parent": None})}]})
        before = copy.deepcopy(original)
        self.assertEqual(stdio_proxy.expose_capture_image(capture_request(), original), before)
        self.assertEqual(original, before)

    def test_unrelated_method_meta_tool_toolset_or_tool_does_not_convert(self):
        cases = []
        request = capture_request(); request["method"] = "tools/list"; cases.append(request)
        request = capture_request(); request["params"]["name"] = "describe_toolset"; cases.append(request)
        request = capture_request(); request["params"]["arguments"]["toolset_name"] = "Other.EditorAppToolset"; cases.append(request)
        request = capture_request(); request["params"]["arguments"]["tool_name"] = "CaptureViewportPNG"; cases.append(request)
        request = capture_request(); request["params"]["arguments"]["tool_name"] = "EditorToolset.EditorAppToolset.CaptureViewport"; cases.append(request)
        for request in cases:
            with self.subTest(request=request):
                original = native_reply()
                self.assertEqual(stdio_proxy.expose_capture_image(request, original), original)

    def test_tool_errors_and_jsonrpc_errors_are_not_presented_as_captured_images(self):
        for original in (native_reply(True), {"jsonrpc": "2.0", "id": 0,
                                             "error": {"code": -32001, "message": "offline transport failure"}}):
            with self.subTest(error=original.get("error", "tool-error")):
                before = copy.deepcopy(original)
                self.assertEqual(stdio_proxy.expose_capture_image(capture_request(), original), before)
                self.assertEqual(original, before)

    def test_missing_image_and_falsey_return_values_are_left_untouched(self):
        for value in (False, 0, [], None, {"image": None}, {"image": {}}, {"image": {"mimeType": "image/png", "data": ""}}):
            with self.subTest(value=value):
                original = envelope({"content": [{"type": "text", "text": json.dumps({"returnValue": value})}]})
                self.assertEqual(stdio_proxy.expose_capture_image(capture_request(), original), original)

    def test_invalid_base64_and_non_png_bytes_do_not_create_a_false_image_claim(self):
        for data in ("not valid base64!", base64.b64encode(b"not a PNG").decode()):
            with self.subTest(data=data):
                value = capture_value(); value["returnValue"]["image"]["data"] = data
                original = envelope({"content": [{"type": "text", "text": json.dumps(value)}]})
                before = copy.deepcopy(original)
                self.assertEqual(stdio_proxy.expose_capture_image(capture_request(), original), before)
                self.assertEqual(original, before)

    def test_png_signature_only_or_missing_iend_is_not_promoted_as_an_image(self):
        for png in (PNG[:8], PNG[:-12]):
            with self.subTest(byte_length=len(png)):
                value = capture_value()
                value["returnValue"]["image"]["data"] = base64.b64encode(png).decode()
                original = envelope({"content": [{"type": "text", "text": json.dumps(value)}]})
                before = copy.deepcopy(original)
                self.assertEqual(stdio_proxy.expose_capture_image(capture_request(), original), before)
                self.assertEqual(original, before)

    def test_non_object_request_params_leave_reply_unchanged(self):
        for params in (None, [], "unrelated"):
            with self.subTest(params=params):
                request = capture_request()
                request["params"] = params
                original = native_reply()
                self.assertEqual(stdio_proxy.expose_capture_image(request, original), original)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__)))
    print("%d/%d" % (result.testsRun - len(result.failures) - len(result.errors), result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() else 1)
