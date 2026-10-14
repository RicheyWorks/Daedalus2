# SPDX-License-Identifier: MIT
"""stdio <-> Streamable-HTTP proxy for the Epic Unreal MCP server, so the Claude desktop app (which launches local
MCP servers over stdio) can use the editor's server on http://127.0.0.1:8000/mcp.

claude_desktop_config.json:
    "mcpServers": {"epic_unreal": {"command": "python", "args": ["C:\\\\Users\\\\730ri\\\\projects\\\\D2-build\\\\tools\\\\unreal_mcp\\\\stdio_proxy.py"]}}

Newline-delimited JSON-RPC on stdin/stdout. Requests are forwarded once; the Mcp-Session-Id the server issues
on initialize is kept for the rest of the run. Notifications (no id) get no reply. If the editor's server is down,
requests get a JSON-RPC error instead of a hang, so the app shows the server as failed rather than frozen.
"""
import json
import base64
import binascii
import struct
import sys
import zlib

if __package__:
    from .transport import TransportFailure, post_json
else:
    from transport import TransportFailure, post_json

URL = "http://127.0.0.1:8000/mcp"
SESSION = {"id": None}


def _is_complete_png(png):
    """Check PNG framing and chunk CRCs without inflating pixel data."""
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    offset, saw_header, saw_pixels = 8, False, False
    while offset + 12 <= len(png):
        length = struct.unpack_from(">I", png, offset)[0]
        end = offset + 12 + length
        if end > len(png):
            return False
        kind = png[offset + 4:offset + 8]
        payload = png[offset + 8:end - 4]
        crc = struct.unpack_from(">I", png, end - 4)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != crc:
            return False
        if not saw_header:
            if kind != b"IHDR" or length != 13:
                return False
            width, height = struct.unpack_from(">II", payload)
            if width == 0 or height == 0:
                return False
            saw_header = True
        elif kind == b"IHDR":
            return False
        if kind == b"IDAT":
            saw_pixels = True
        if kind == b"IEND":
            return length == 0 and saw_pixels and end == len(png)
        offset = end
    return False


def post(msg):
    return expose_capture_image(msg, post_json(URL, msg, SESSION))


def expose_capture_image(msg, reply):
    """Move the exact native capture PNG into MCP image content for the viewer.

    Epic currently wraps returnValue.image in JSON text. Other tool replies and
    existing MCP image blocks pass through unchanged. Annotation/camera metadata
    remains in text; the base64 appears once rather than being duplicated.
    """
    params = msg.get("params", {})
    args = params.get("arguments", {}) if isinstance(params, dict) else {}
    if (msg.get("method") != "tools/call" or not isinstance(params, dict)
            or params.get("name") != "call_tool"
            or not isinstance(args, dict)
            or args.get("toolset_name") != "EditorToolset.EditorAppToolset"
            or args.get("tool_name") != "CaptureViewport"
            or not isinstance(reply, dict)):
        return reply
    result = reply.get("result")
    if not isinstance(result, dict) or result.get("isError"):
        return reply
    content = result.get("content")
    if (not isinstance(content, list) or len(content) != 1
            or not isinstance(content[0], dict) or content[0].get("type") != "text"):
        return reply
    try:
        native = json.loads(content[0]["text"])
        capture = native["returnValue"]
        image = capture["image"]
        if image["mimeType"] != "image/png" or not isinstance(image["data"], str):
            return reply
        png = base64.b64decode(image["data"], validate=True)
        if not _is_complete_png(png):
            return reply
    except (KeyError, TypeError, ValueError, binascii.Error):
        return reply
    image_content = {"type": "image", "mimeType": image["mimeType"], "data": image["data"]}
    capture["image"] = {key: value for key, value in image.items() if key != "data"}
    capture["image"].update({"byteLength": len(png), "contentIndex": 0})
    metadata = dict(content[0], text=json.dumps(native))
    return dict(reply, result=dict(result, content=[image_content, metadata]))


def main():
    out = sys.stdout
    for line in sys.stdin:
        line = line.strip().lstrip("﻿")
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError as e:
            sys.stderr.write("stdio_proxy: not JSON (%s): %r\n" % (e, line[:120]))
            sys.stderr.flush()
            continue
        has_id = isinstance(msg, dict) and "id" in msg
        if not isinstance(msg, dict):
            sys.stderr.write("stdio_proxy: expected a JSON-RPC object\n")
            continue
        try:
            reply = post(msg)
        except TransportFailure as e:
            reply = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {
                "code": -32001, "message": str(e), "data": e.data}}
        except Exception as e:
            reply = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {
                "code": -32001, "message": "Unreal MCP proxy error: %s" % e,
                "data": {"outcome": "unknown", "retryable": False, "replayed": False}}}
        if has_id and reply is not None:
            out.write(json.dumps(reply) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
