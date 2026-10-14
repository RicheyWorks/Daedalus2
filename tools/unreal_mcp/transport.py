# SPDX-License-Identifier: MIT
"""Bounded, single-attempt JSON-RPC response transport for local Unreal MCP.

Reading a response is not proof that the tool completed. Failures after submitting
a request retain an unknown outcome; callers must not automatically replay it.
"""
import http.client
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

MAX_RESPONSE_BYTES = 16 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
_UNSPECIFIED = object()


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _http_status(resp):
    value = getattr(resp, "status", None)
    if value is None:
        value = getattr(resp, "code", None)
    return value if type(value) is int else None


class TransportFailure(RuntimeError):
    def __init__(self, stage, message, received=0, expected=None):
        super().__init__("Unreal MCP %s: %s (received=%s, expected=%s)" %
                         (stage, message, received, expected))
        self.data = {"stage": stage, "receivedBytes": received,
                     "expectedBytes": expected, "outcome": "unknown",
                     "retryable": False, "replayed": False}


def _decode_reply(raw, request_id, received, expected):
    try:
        text = raw.decode("utf-8")
        if not text.strip():
            return None
        # SSE data belongs to complete events, not individual lines. Progress
        # notifications can precede the final JSON-RPC reply.
        if text.lstrip().startswith(("event:", "data:", ":")):
            events, lines = [], []
            for line in text.splitlines():
                if not line:
                    if lines:
                        events.append(json.loads("\n".join(lines)))
                        lines = []
                elif line.startswith("data:"):
                    value = line[5:]
                    lines.append(value[1:] if value.startswith(" ") else value)
            if lines:
                raise ValueError("SSE reply event lacks its blank-line terminator")
            candidates = [event for event in events if isinstance(event, dict)
                          and ("result" in event or "error" in event)]
            if request_id is not _UNSPECIFIED:
                candidates = [event for event in candidates
                              if type(event.get("id")) is type(request_id)
                              and event.get("id") == request_id]
            if len(candidates) != 1:
                raise ValueError("expected one complete JSON-RPC reply event")
            reply = candidates[0]
        else:
            reply = json.loads(text)
        if not isinstance(reply, dict) or reply.get("jsonrpc") != "2.0":
            raise ValueError("expected a JSON-RPC 2.0 response object")
        if ("result" in reply) == ("error" in reply):
            raise ValueError("expected exactly one result or error")
        if "error" in reply and (not isinstance(reply["error"], dict)
                or type(reply["error"].get("code")) is not int
                or not isinstance(reply["error"].get("message"), str)):
            raise ValueError("expected a JSON-RPC error code and message")
        if request_id is not _UNSPECIFIED and (
                "id" not in reply or type(reply["id"]) is not type(request_id)
                or reply["id"] != request_id):
            raise ValueError("response id does not match the request")
        return reply
    except (UnicodeError, ValueError) as exc:
        raise TransportFailure("response_decode", str(exc), received, expected) from exc


def read_response(resp, max_response_bytes=MAX_RESPONSE_BYTES,
                  chunk_bytes=READ_CHUNK_BYTES, request_id=_UNSPECIFIED,
                  observation=None, started_monotonic=None):
    """Drain in bounded chunks, then validate completeness before parsing.

    The cap covers wire bytes, including SSE framing. No partial JSON or image is
    returned. read1 preserves delivered-prefix accounting on a later socket reset.
    """
    if (type(max_response_bytes) is not int or max_response_bytes <= 0
            or type(chunk_bytes) is not int or chunk_bytes <= 0):
        raise ValueError("response and chunk byte limits must be positive integers")
    header = resp.headers.get("Content-Length")
    expected = None
    if header is not None:
        if not isinstance(header, str) or not header.isascii() or not header.isdecimal():
            raise TransportFailure("response_headers", "invalid Content-Length")
        expected = int(header)
        if expected > max_response_bytes:
            raise TransportFailure("response_limit", "Content-Length exceeds the byte limit",
                                   expected=expected)
    if observation is not None:
        observation["expectedBytes"] = expected
    chunks, received = [], 0
    read = getattr(resp, "read1", None) or resp.read
    while True:
        size = min(chunk_bytes, max_response_bytes + 1 - received)
        before = time.monotonic() if observation is not None else None
        try:
            chunk = read(size)
        except http.client.IncompleteRead as exc:
            received += len(exc.partial)
            if observation is not None:
                observation["receivedBytes"] = received
                if exc.partial and started_monotonic is not None:
                    observation["secondsToLastByte"] = max(0, time.monotonic() - started_monotonic)
            raise TransportFailure("response_body", "incomplete HTTP body",
                                   received, expected) from exc
        except Exception as exc:
            raise TransportFailure("response_body", "%s: %s" % (type(exc).__name__, exc),
                                   received, expected) from exc
        finally:
            if observation is not None:
                duration = max(0, time.monotonic() - before)
                observation["readCalls"] = observation.get("readCalls", 0) + 1
                observation["maxReadSeconds"] = max(observation.get("maxReadSeconds", 0), duration)
        if not chunk:
            break
        received += len(chunk)
        if observation is not None:
            observation["receivedBytes"] = received
            if started_monotonic is not None:
                observation["secondsToLastByte"] = max(0, time.monotonic() - started_monotonic)
        if received > max_response_bytes:
            raise TransportFailure("response_limit", "body exceeds the byte limit",
                                   received, expected)
        chunks.append(chunk)
    if expected is not None and received != expected:
        raise TransportFailure("response_body", "Content-Length delivery is incomplete",
                               received, expected)
    if observation is not None:
        observation["bodyComplete"] = True
    reply = _decode_reply(b"".join(chunks), request_id, received, expected)
    if observation is not None:
        observation["replyValidated"] = reply is not None
    return reply


def post_json(url, msg, session, timeout=600, observation=None):
    """Submit once. There is intentionally no retry/reinitialization loop."""
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if session.get("id"):
        headers["Mcp-Session-Id"] = session["id"]
    req = urllib.request.Request(url, data=json.dumps(msg).encode("utf-8"),
                                 headers=headers, method="POST")
    request_id = msg.get("id") if "id" in msg else _UNSPECIFIED
    details = observation if observation is not None else {}
    details.clear()
    started = time.monotonic()
    details.update({"startedAt": _utc_now(), "headersAt": None, "finishedAt": None,
                    "timeoutSeconds": timeout, "httpStatus": None,
                    "secondsToHeaders": None, "secondsToLastByte": None,
                    "elapsedSeconds": None, "maxReadSeconds": 0, "readCalls": 0,
                    "receivedBytes": 0, "expectedBytes": None,
                    "bodyComplete": False, "replyValidated": False})
    try:
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            # A valid JSON-RPC error remains intact. Error bodies use the same cap.
            resp = exc
        except Exception as exc:
            raise TransportFailure("request_submission", "%s: %s" % (type(exc).__name__, exc)) from exc
        details["headersAt"] = _utc_now()
        details["secondsToHeaders"] = max(0, time.monotonic() - started)
        details["httpStatus"] = _http_status(resp)
        with resp:
            sid = resp.headers.get("Mcp-Session-Id")
            if sid:
                session["id"] = sid
            try:
                reply = read_response(resp, request_id=request_id,
                                      observation=details, started_monotonic=started)
                if request_id is not _UNSPECIFIED and reply is None:
                    raise TransportFailure("response_body", "request received no JSON-RPC reply")
            except TransportFailure as exc:
                exc.data["responseHeaders"] = {
                    key: (resp.headers.get(key) or "")[:512]
                    for key in ("Content-Type", "Content-Length", "Transfer-Encoding", "Connection", "Content-Encoding")}
                raise
            return reply
    except TransportFailure as exc:
        # Bounded scalar metadata only. No payload, URL, auth/session headers or
        # automatic retry; these timings cannot identify the party causing RST.
        details["finishedAt"] = _utc_now()
        details["elapsedSeconds"] = max(0, time.monotonic() - started)
        exc.data["transfer"] = dict(details)
        raise
    finally:
        if details["finishedAt"] is None:
            details["finishedAt"] = _utc_now()
            details["elapsedSeconds"] = max(0, time.monotonic() - started)
