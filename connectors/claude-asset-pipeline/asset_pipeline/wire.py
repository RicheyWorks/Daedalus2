# SPDX-License-Identifier: MIT
"""One JSON line each way over TCP: the wire format both connectors speak.

Claude Blender Bridge (127.0.0.1:9876) and Claude Unreal Bridge (127.0.0.1:9877) take
{"id", "type", "params"} and answer {"id", "status": "ok"|"error", "result"|"message"}.
"""
import json
import os
import socket
import uuid

BLENDER = (os.environ.get("CLAUDE_BLENDER_HOST", "127.0.0.1"), int(os.environ.get("CLAUDE_BLENDER_PORT", "9876")))
UNREAL = (os.environ.get("CLAUDE_UNREAL_HOST", "127.0.0.1"), int(os.environ.get("CLAUDE_UNREAL_PORT", "9877")))


class BridgeError(Exception):
    """The bridge answered, with an error."""

    def __init__(self, side, reply):
        super().__init__("%s: %s" % (side, reply.get("message", "bridge error")))
        self.side = side
        self.reply = reply


MAX_REPLY_BYTES = 64 * 1024 * 1024


def reject_nonfinite(value):
    raise ValueError("nonfinite JSON number: " + value)


def validate_reply(reply, request_id, side):
    """Validate only the existing envelope; preserve the command result exactly."""
    if not isinstance(reply, dict):
        raise BridgeError(side, {"message": "response must be a JSON object", "request_id": request_id})
    if reply.get("id") != request_id:
        raise BridgeError(side, {"message": "response identity does not match request", "request_id": request_id,
                                 "observed_id": reply.get("id")})
    if reply.get("status") not in ("ok", "error"):
        raise BridgeError(side, {"message": "invalid response status", "request_id": request_id,
                                 "observed_status": reply.get("status")})
    if reply["status"] == "error":
        raise BridgeError(side, reply)
    if "result" not in reply:
        raise BridgeError(side, {"message": "successful response lacks result", "request_id": request_id})
    return reply["result"]


def call(addr, command, timeout=600, side="bridge", receipt=None, on_progress=None, **params):
    """One request, one validated reply. A transport failure never triggers a retry.

    receipt is optional host evidence, not an extra wire field. on_progress may
    persist it before dispatch so a killed host leaves its last known state.
    """
    request_id = uuid.uuid4().hex
    evidence = receipt if receipt is not None else {}
    evidence.update(request_id=request_id, command=command, side=side, state="prepared")
    payload = (json.dumps({"id": request_id, "type": command, "params": params}, allow_nan=False) + "\n").encode("utf-8")
    def publish(state):
        evidence["state"] = state
        if on_progress is not None:
            on_progress(evidence)
    publish("prepared")
    try:
        connection = socket.create_connection(addr, timeout=timeout)
    except OSError:
        publish("not-dispatched")
        raise
    with connection as stream:
        # Persist unknown before send: sendall can fail after a partial write.
        publish("outcome-unknown")
        stream.sendall(payload)
        data = bytearray()
        while b"\n" not in data:
            chunk = stream.recv(min(1 << 20, MAX_REPLY_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_REPLY_BYTES:
                raise BridgeError(side, {"message": "response exceeds byte limit", "request_id": request_id})
    if b"\n" not in data:
        raise BridgeError(side, {"message": "connection closed before complete response", "request_id": request_id})
    try:
        reply = json.loads(bytes(data).split(b"\n", 1)[0].decode("utf-8"),
                           parse_constant=reject_nonfinite)
    except (ValueError, UnicodeError) as error:
        raise BridgeError(side, {"message": "malformed JSON response", "request_id": request_id}) from error
    if isinstance(reply, dict) and reply.get("id") == request_id and reply.get("status") == "error":
        evidence["error_reply"] = reply
        publish("error-received")
    result = validate_reply(reply, request_id, side)
    publish("reply-received")
    return result


def obj(result, side="bridge", what="the code"):
    """The `result` a script left, which must be a JSON object. A bridge that answers with anything else (a bare
    true/false, null, a string) used to crash later as "'bool' object is not subscriptable" with no clue which side
    or call it was; this names both and shows what came back."""
    inner = result.get("result") if isinstance(result, dict) else result
    if not isinstance(inner, dict):
        raise BridgeError(side, {"message": "%s returned %s %s, expected a JSON object (is the editor in Play, or did the "
                                 "script stop before setting result?)" % (what, type(inner).__name__, repr(inner)[:80])})
    return inner


def reachable(addr, timeout=2.0):
    try:
        with socket.create_connection(addr, timeout=timeout):
            return True
    except OSError:
        return False
