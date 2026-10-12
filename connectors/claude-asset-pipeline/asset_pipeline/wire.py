# SPDX-License-Identifier: MIT
"""One JSON line each way over TCP: the wire format both connectors speak.

Claude Blender Bridge (127.0.0.1:9876) and Claude Unreal Bridge (127.0.0.1:9877) take
{"id", "type", "params"} and answer {"id", "status": "ok"|"error", "result"|"message"}.
"""
import json
import os
import socket

BLENDER = (os.environ.get("CLAUDE_BLENDER_HOST", "127.0.0.1"), int(os.environ.get("CLAUDE_BLENDER_PORT", "9876")))
UNREAL = (os.environ.get("CLAUDE_UNREAL_HOST", "127.0.0.1"), int(os.environ.get("CLAUDE_UNREAL_PORT", "9877")))


class BridgeError(Exception):
    """The bridge answered, with an error."""

    def __init__(self, side, reply):
        super().__init__("%s: %s" % (side, reply.get("message", "bridge error")))
        self.side = side
        self.reply = reply


def call(addr, command, timeout=600, side="bridge", **params):
    """Send one command to the bridge at addr=(host, port) and return its result."""
    with socket.create_connection(addr, timeout=timeout) as s:
        s.sendall((json.dumps({"id": 1, "type": command, "params": params}) + "\n").encode("utf-8"))
        data = b""
        while b"\n" not in data:
            chunk = s.recv(1 << 20)
            if not chunk:
                break
            data += chunk
    if not data:
        raise BridgeError(side, {"message": "the bridge closed the connection without answering"})
    reply = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
    if reply.get("status") != "ok":
        raise BridgeError(side, reply)
    return reply.get("result")


def reachable(addr, timeout=2.0):
    try:
        with socket.create_connection(addr, timeout=timeout):
            return True
    except OSError:
        return False
