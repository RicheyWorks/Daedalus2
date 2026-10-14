# SPDX-License-Identifier: MIT
"""stdio <-> Streamable-HTTP proxy for the Epic Unreal MCP server, so the Claude desktop app (which launches local
MCP servers over stdio) can use the editor's server on http://127.0.0.1:8000/mcp.

claude_desktop_config.json:
    "mcpServers": {"epic_unreal": {"command": "python", "args": ["C:\\\\Users\\\\730ri\\\\projects\\\\D2-build\\\\tools\\\\unreal_mcp\\\\stdio_proxy.py"]}}

Newline-delimited JSON-RPC on stdin/stdout. Every message is forwarded as-is; the Mcp-Session-Id the server issues
on initialize is kept for the rest of the run. Notifications (no id) get no reply. If the editor's server is down,
requests get a JSON-RPC error instead of a hang, so the app shows the server as failed rather than frozen.
"""
import json
import sys
import urllib.error
import urllib.request

URL = "http://127.0.0.1:8000/mcp"
SESSION = {"id": None}


def post(msg):
    hdr = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if SESSION["id"]:
        hdr["Mcp-Session-Id"] = SESSION["id"]
    req = urllib.request.Request(URL, data=json.dumps(msg).encode(), headers=hdr, method="POST")
    with urllib.request.urlopen(req, timeout=600) as resp:
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            SESSION["id"] = sid
        raw = resp.read().decode()
    if not raw.strip():
        return None
    if raw.lstrip().startswith("event:") or raw.lstrip().startswith("data:"):   # SSE framing: take the data lines
        datas = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
        raw = datas[-1] if datas else ""
    return json.loads(raw) if raw else None


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
        try:
            reply = post(msg)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                reply = json.loads(body)
            except ValueError:
                reply = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32000, "message": "HTTP %s: %s" % (e.code, body[:300])}}
        except Exception as e:
            reply = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32001, "message": "Unreal MCP server not reachable at %s: %s" % (URL, e)}}
        if has_id and reply is not None:
            out.write(json.dumps(reply) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
