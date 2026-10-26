# SPDX-License-Identifier: MIT
"""One bridge call: one TCP connection, one JSON line each way (PROTOCOL.md)."""
import json
import socket


def call(command, params=None, host="127.0.0.1", port=9877, timeout=120):
    params = dict(params or {})
    params.setdefault("bridge_timeout", timeout)
    with socket.create_connection((host, port), timeout=timeout + 5) as s:
        s.sendall((json.dumps({"id": 1, "type": command, "params": params}) + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = s.recv(1 << 20)
            if not chunk:
                break
            data += chunk
    if not data:
        return {"status": "error", "message": "the bridge closed the connection without answering"}
    return json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
