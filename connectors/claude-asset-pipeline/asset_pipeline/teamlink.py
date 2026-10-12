# SPDX-License-Identifier: MIT
"""Team link (ADR-053): a real-time channel between the Blender team and the Unreal team on this PC.

The Markdown board (QUEUE.md) stays the official record. This link is how each side hears about a change the moment
it happens, and how each side knows the other one is alive.

    one broker:  python -m asset_pipeline.teamlink serve          127.0.0.1:9890, log in bot-team\\link\\log.jsonl

Every message is one JSON object, kept forever in an append-only log (each line is flushed and fsynced):

    {"id": 42, "ts": "2026-10-12T11:55:01", "from": "blender-team", "to": "unreal-team", "type": "asset.ready",
     "body": {"asset": "Tool_Axe"}, "reply_to": null}

`to` is a team name or "*" (everyone). `id` is the broker's: it only ever goes up, so "everything after 41" is the
way to catch up after a restart. Nothing is lost while a side is down.

HTTP (JSON in, JSON out; any language can use it):

    POST /send       {from, to, type, body, reply_to?}        -> {id}
    GET  /wait       ?me=NAME&after=ID&timeout=S              -> {messages: [...], last: ID}   long-poll: returns the
                                                                 moment something for NAME arrives (S <= 55)
    POST /ack        {me, id}                                 -> {ok}   a receipt; the sender gets type "ack"
    GET  /pending    ?me=NAME                                 -> messages to NAME not yet acked (catch-up)
    POST /heartbeat  {me, status?}                            -> {ok}   every <= 10 s
    GET  /presence                                            -> {NAME: {age_s, alive, status}}   alive: age < 30 s
    GET  /log        ?after=ID&limit=N                        -> the log, for anyone
    GET  /health                                              -> {ok, last, since}

Message types the two teams agreed on so far (anything else is passed through untouched):

    asset.ready     Blender → Unreal   {asset}            ship it now (no waiting for the 10 s board pass)
    asset.shipping / asset.shipped / asset.rejected / asset.blocked / asset.waiting
                    Unreal → all       {asset, status, why?, report?}
    ping / pong     either             {}                 a live round trip
    ack             broker             {id}               the receiver has it
    note            either             {text}             words for the other team (and Richmond)
"""
import argparse
import datetime
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = 9890
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "projects", "bot-team", "link")
ALIVE_S = 30
MAX_WAIT_S = 55
MAX_BODY = 256 * 1024


class Broker:
    """The log, the receipts and who's alive. Thread-safe; the HTTP layer is a thin skin over it."""

    def __init__(self, folder, clock=time.time):
        self.folder = folder
        self.clock = clock
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, "log.jsonl")
        self.cond = threading.Condition()
        self.messages = []
        self.acked = set()      # (me, id)
        self.seen = {}          # name -> (time, status)
        self.since = clock()
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        m = json.loads(line)
                    except ValueError:
                        continue   # a torn last line from a crash: skip it, never stop
                    self.messages.append(m)
                    if m.get("type") == "ack":
                        self.acked.add((m.get("from"), (m.get("body") or {}).get("id")))

    @property
    def last(self):
        return self.messages[-1]["id"] if self.messages else 0

    def _append(self, m):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self.messages.append(m)

    def send(self, frm, to, kind, body=None, reply_to=None):
        if not frm or not to or not kind:
            raise ValueError("from, to and type are required")
        with self.cond:
            m = {"id": self.last + 1,
                 "ts": datetime.datetime.fromtimestamp(self.clock()).isoformat(timespec="seconds"),
                 "from": str(frm), "to": str(to), "type": str(kind), "body": body if body is not None else {},
                 "reply_to": reply_to}
            self._append(m)
            self.seen[str(frm)] = (self.clock(), self.seen.get(str(frm), (0, ""))[1])
            self.cond.notify_all()
            return m["id"]

    def _for(self, me, after):
        return [m for m in self.messages if m["id"] > after and m["from"] != me and m["to"] in (me, "*")]

    def wait(self, me, after, timeout):
        """Messages for `me` after `after`; blocks up to `timeout` s until there is one."""
        deadline = time.monotonic() + max(0.0, min(float(timeout), MAX_WAIT_S))
        with self.cond:
            self.seen[me] = (self.clock(), self.seen.get(me, (0, ""))[1])   # waiting counts as alive
            while True:
                got = self._for(me, after)
                left = deadline - time.monotonic()
                if got or left <= 0:
                    return got, self.last
                self.cond.wait(left)

    def ack(self, me, mid):
        with self.cond:
            target = next((m for m in self.messages if m["id"] == mid), None)
            if target is None:
                raise KeyError(mid)
            if (me, mid) in self.acked:
                return False
            self.acked.add((me, mid))
        self.send(me, target["from"], "ack", {"id": mid, "type": target["type"]}, reply_to=mid)
        return True

    def pending(self, me):
        with self.cond:
            return [m for m in self._for(me, 0) if m["type"] != "ack" and (me, m["id"]) not in self.acked]

    def heartbeat(self, me, status=""):
        with self.cond:
            self.seen[me] = (self.clock(), status or self.seen.get(me, (0, ""))[1])

    def presence(self):
        now = self.clock()
        with self.cond:
            return {n: {"age_s": round(now - t, 1), "alive": now - t < ALIVE_S, "status": s}
                    for n, (t, s) in sorted(self.seen.items())}

    def log(self, after=0, limit=200):
        with self.cond:
            return [m for m in self.messages if m["id"] > after][:limit]


def make_handler(broker):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _out(self, code, obj):
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _q(self):
            u = urlparse(self.path)
            return u.path, {k: v[-1] for k, v in parse_qs(u.query).items()}

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("message too big (max %d bytes)" % MAX_BODY)
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")

        def do_GET(self):
            path, q = self._q()
            try:
                if path == "/wait":
                    got, last = broker.wait(q["me"], int(q.get("after", 0)), float(q.get("timeout", 25)))
                    return self._out(200, {"messages": got, "last": last})
                if path == "/pending":
                    return self._out(200, {"messages": broker.pending(q["me"])})
                if path == "/presence":
                    return self._out(200, broker.presence())
                if path == "/log":
                    return self._out(200, {"messages": broker.log(int(q.get("after", 0)), int(q.get("limit", 200)))})
                if path == "/health":
                    return self._out(200, {"ok": True, "last": broker.last,
                                           "since": datetime.datetime.fromtimestamp(broker.since).isoformat(timespec="seconds")})
                return self._out(404, {"error": "no such path", "paths": ["/send", "/wait", "/ack", "/pending",
                                                                          "/heartbeat", "/presence", "/log", "/health"]})
            except KeyError as e:
                return self._out(400, {"error": "missing %s" % e})
            except ValueError as e:
                return self._out(400, {"error": str(e)})

        def do_POST(self):
            path, _ = self._q()
            try:
                b = self._body()
                if path == "/send":
                    return self._out(200, {"id": broker.send(b.get("from"), b.get("to"), b.get("type"), b.get("body"),
                                                             b.get("reply_to"))})
                if path == "/ack":
                    return self._out(200, {"ok": True, "new": broker.ack(b["me"], int(b["id"]))})
                if path == "/heartbeat":
                    broker.heartbeat(b["me"], b.get("status", ""))
                    return self._out(200, {"ok": True})
                return self._out(404, {"error": "no such path"})
            except KeyError as e:
                return self._out(400, {"error": "unknown or missing %s" % e})
            except ValueError as e:
                return self._out(400, {"error": str(e)})

    return H


def serve(folder=DEFAULT_DIR, port=PORT, ready=None):
    broker = Broker(folder)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(broker))
    server.daemon_threads = True
    if ready:
        ready(server, broker)
    print("team link on 127.0.0.1:%d, log %s (last id %d)" % (server.server_address[1], broker.path, broker.last),
          flush=True)
    server.serve_forever()


# ----------------------------------------------------------------------------------------------------- client

class Link:
    """A team's end of the link. Never raises on a dead broker: calls return None and `up` turns False."""

    def __init__(self, me, port=PORT, host="127.0.0.1"):
        self.me, self.base, self.up = me, "http://%s:%d" % (host, port), False

    def _call(self, method, path, body=None, timeout=5.0):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                self.up = True
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError, ValueError):
            self.up = False
            return None

    def send(self, to, kind, body=None, reply_to=None):
        r = self._call("POST", "/send", {"from": self.me, "to": to, "type": kind, "body": body or {},
                                         "reply_to": reply_to})
        return r and r.get("id")

    def wait(self, after, timeout=25.0):
        r = self._call("GET", "/wait?me=%s&after=%d&timeout=%s" % (self.me, after, timeout), timeout=timeout + 5)
        return (r["messages"], r["last"]) if r else ([], after)

    def ack(self, mid):
        return self._call("POST", "/ack", {"me": self.me, "id": mid})

    def heartbeat(self, status=""):
        return self._call("POST", "/heartbeat", {"me": self.me, "status": status})

    def pending(self):
        r = self._call("GET", "/pending?me=" + self.me)
        return r["messages"] if r else []

    def presence(self):
        return self._call("GET", "/presence") or {}

    def health(self):
        return self._call("GET", "/health")


# ------------------------------------------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="The Blender team ↔ Unreal team real-time link (ADR-053).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--folder", default=DEFAULT_DIR)
    s.add_argument("--port", type=int, default=PORT)
    for name in ("send", "wait", "pending", "presence", "ping", "log"):
        p = sub.add_parser(name)
        p.add_argument("--me", default="unreal-team")
        p.add_argument("--port", type=int, default=PORT)
        if name == "send":
            p.add_argument("--to", required=True)
            p.add_argument("--type", required=True)
            p.add_argument("--body", default="{}", help="JSON")
        if name in ("wait", "log"):
            p.add_argument("--after", type=int, default=0)
            p.add_argument("--timeout", type=float, default=25)
        if name == "ping":
            p.add_argument("--to", default="blender-team")
            p.add_argument("--timeout", type=float, default=20)
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        serve(a.folder, a.port)
        return 0
    link = Link(a.me, a.port)
    if a.cmd == "send":
        out = {"id": link.send(a.to, a.type, json.loads(a.body))}
    elif a.cmd == "wait":
        msgs, last = link.wait(a.after, a.timeout)
        out = {"messages": msgs, "last": last}
    elif a.cmd == "pending":
        out = {"messages": link.pending()}
    elif a.cmd == "presence":
        out = link.presence()
    elif a.cmd == "log":
        out = link._call("GET", "/log?after=%d" % a.after)
    else:   # ping: a live round trip, timed
        h = link.health()
        if not h:
            print(json.dumps({"up": False}))
            return 2
        t0 = time.time()
        mid = link.send(a.to, "ping", {})
        after, pong = h["last"], None
        while time.time() - t0 < a.timeout and pong is None:
            msgs, after = link.wait(after, max(1.0, a.timeout - (time.time() - t0)))
            pong = next((m for m in msgs if m["type"] == "pong" and m.get("reply_to") == mid), None)
        out = {"ping": mid, "pong": pong is not None, "ms": round((time.time() - t0) * 1000) if pong else None,
               "from": a.to}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if (out if not isinstance(out, dict) else out.get("pong", True) is not False) else 1


if __name__ == "__main__":
    sys.exit(main())
