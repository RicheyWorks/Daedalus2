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
RATE_PER_S = 20.0      # per sender, sustained (borrowed from LoadBalancerPro's load shedding: one noisy bot can't
RATE_BURST = 200.0     # starve the rest); a burst of this many is fine


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
        self.bots = {}          # name -> {role, handles, about, registered}
        self.buckets = {}       # name -> [tokens, last time]
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
                    if m.get("type") == "bot.register":
                        self.bots[m["from"]] = dict(m.get("body") or {}, registered=m["ts"])
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

    def allow(self, frm, now=None):
        """Token bucket per sender: False when a bot is flooding the hub (the HTTP layer answers 429)."""
        now = time.monotonic() if now is None else now
        with self.cond:
            tokens, last = self.buckets.get(frm, (RATE_BURST, now))
            tokens = min(RATE_BURST, tokens + (now - last) * RATE_PER_S)
            ok = tokens >= 1.0
            self.buckets[frm] = (tokens - 1.0 if ok else tokens, now)
            return ok

    def register(self, me, role="", handles=None, about=""):
        """A bot says who it is and which message types it handles; kept in the log, so it survives restarts."""
        body = {"role": str(role), "handles": [str(h) for h in (handles or [])], "about": str(about)}
        mid = self.send(me, "*", "bot.register", body, topic="hub")
        with self.cond:
            self.bots[me] = dict(body, registered=self.messages[-1]["ts"] if self.messages else "")
        return mid

    def directory(self):
        """Every bot the hub knows: what it registered and whether it's alive."""
        pres = self.presence()
        with self.cond:
            names = sorted(set(self.bots) | set(pres))
            return {n: dict(self.bots.get(n, {}), **pres.get(n, {"alive": False, "age_s": None, "status": ""}))
                    for n in names}

    def send(self, frm, to, kind, body=None, reply_to=None, uid=None, topic=None):
        if not frm or not to or not kind:
            raise ValueError("from, to and type are required")
        with self.cond:
            if uid is not None:
                dup = next((m for m in self.messages if m.get("uid") == uid), None)
                if dup is not None:
                    return dup["id"]   # a replayed outbox: same message, no duplicate
            m = {"id": self.last + 1,
                 "ts": datetime.datetime.fromtimestamp(self.clock()).isoformat(timespec="seconds"),
                 "from": str(frm), "to": str(to), "type": str(kind), "body": body if body is not None else {},
                 "reply_to": reply_to}
            if uid is not None:
                m["uid"] = str(uid)
            if topic:
                m["topic"] = str(topic)
            self._append(m)
            self.seen[str(frm)] = (self.clock(), self.seen.get(str(frm), (0, ""))[1])
            self.cond.notify_all()
            return m["id"]

    def _since(self, after):
        """Messages after id `after`, without scanning the whole log (ids are 1, 2, 3... in order)."""
        after = max(0, int(after))
        if after < len(self.messages) and (after == 0 or self.messages[after - 1]["id"] == after):
            return self.messages[after:]
        return [m for m in self.messages if m["id"] > after]

    def _for(self, me, after, topics=None):
        return [m for m in self._since(after) if m["from"] != me and
                (m["to"] == me or (m["to"] == "*" and (not topics or m.get("topic") in topics)))]

    def wait(self, me, after, timeout, topics=None):
        """Messages for `me` after `after`; blocks up to `timeout` s until there is one. With `topics`, broadcasts
        are filtered to those topics (messages addressed to `me` always come through)."""
        deadline = time.monotonic() + max(0.0, min(float(timeout), MAX_WAIT_S))
        with self.cond:
            self.seen[me] = (self.clock(), self.seen.get(me, (0, ""))[1])   # waiting counts as alive
            while True:
                got = self._for(me, after, topics)
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

    def seq_of(self, ref):
        """A broker id from either a broker id or a client's uuid; 0 when unknown."""
        if ref is None or ref == "":
            return 0
        if str(ref).isdigit():
            return int(ref)
        with self.cond:
            return next((m["id"] for m in self.messages if m.get("uid") == str(ref)), 0)

    def log(self, after=0, limit=200):
        with self.cond:
            return [m for m in self.messages if m["id"] > after][:limit]


# ----------------------------------------------------------------------- v1: the Blender team's envelope (BUS-SCHEMA)
# Their client (blender-harness bus.py) speaks {v, id(uuid), from, to, type, asset, at, reply_to, body} on /v1/*.
# The broker stores one log; these map names and types both ways so either side can use its own dialect.

SHORT = {"blender-team": "blender", "unreal-team": "unreal"}
LONG = {v: k for k, v in SHORT.items()}
IN_TYPES = {"ready": "asset.ready", "status": "blender.status"}


def v1_in(broker, env):
    if not isinstance(env, dict):
        raise ValueError("an envelope is a JSON object")
    frm = LONG.get(env.get("from"), env.get("from"))
    to = LONG.get(env.get("to"), env.get("to")) or "*"
    kind = IN_TYPES.get(env.get("type"), env.get("type"))
    body = dict(env.get("body") or {})
    if env.get("asset"):
        body.setdefault("asset", env["asset"])
    reply = broker.seq_of(env.get("reply_to")) or None
    if kind == "ack" and reply:
        try:
            broker.ack(frm, reply)
        except KeyError:
            pass
        return reply
    if kind == "blender.status":
        broker.heartbeat(frm, "%s%s" % (body.get("state", ""), (" " + str(body["progress"])) if body.get("progress") else ""))
    return broker.send(frm, to, kind, body, reply, uid=env.get("id"))


def v1_out(broker, m, viewer):
    t = m["type"]
    for pre in ("asset.", "queue."):
        if t.startswith(pre):
            t = t[len(pre):]
    reply = m.get("reply_to")
    if reply:
        ref = next((x for x in broker.messages if x["id"] == reply), None)
        reply = (ref.get("uid") if ref else None) or str(reply)
    body = m.get("body") or {}
    return {"v": 1, "id": m.get("uid") or str(m["id"]), "seq": m["id"], "from": SHORT.get(m["from"], m["from"]),
            "to": SHORT.get(m["to"], m["to"]) if m["to"] != "*" else SHORT.get(viewer, viewer),
            "type": t, "asset": body.get("asset"), "at": m["ts"], "reply_to": reply, "body": body}


DASHBOARD = """<!doctype html><html><head><meta charset="utf-8"><title>Bot hub</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;font:14px/1.4 system-ui,Segoe UI,sans-serif;background:#0f1216;color:#e8edf2}
header{padding:14px 18px;border-bottom:1px solid #232a33;display:flex;gap:16px;align-items:baseline}
h1{font-size:18px;margin:0}small{color:#8a97a6}
main{display:grid;grid-template-columns:300px 1fr;gap:0;height:calc(100vh - 52px)}
#bots{border-right:1px solid #232a33;overflow:auto;padding:10px}
.bot{padding:8px 10px;border-radius:8px;margin-bottom:6px;background:#161b22}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;background:#555}
.on{background:#3fb950}.name{font-weight:600}.st{color:#8a97a6;font-size:12px}
#log{overflow:auto;padding:10px;font-family:ui-monospace,Consolas,monospace;font-size:12.5px}
.m{padding:3px 6px;border-bottom:1px solid #1b2129;white-space:pre-wrap;word-break:break-word}
.t{color:#79c0ff}.ack{opacity:.45}.ship{color:#3fb950}.rej{color:#f85149}.blk{color:#d29922}
@media(max-width:700px){main{grid-template-columns:1fr;height:auto}#bots{border-right:0}}
</style></head><body>
<header><h1>Bot hub</h1><small id="sum">connecting…</small></header>
<main><section id="bots"></section><section id="log"></section></main>
<script>
let after=0;const log=document.getElementById('log');
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
async function bots(){try{const r=await (await fetch('/bots')).json();let on=0;
document.getElementById('bots').innerHTML=Object.entries(r).map(([n,b])=>{if(b.alive)on++;
return `<div class="bot"><span class="dot ${b.alive?'on':''}"></span><span class="name">${esc(n)}</span>
${b.role?' · '+esc(b.role):''}<div class="st">${esc(b.status||'')}${b.age_s!=null?' · '+b.age_s+' s ago':''}</div></div>`}).join('');
document.getElementById('sum').textContent=on+' bots online · '+Object.keys(r).length+' known';}catch(e){}}
async function poll(){try{const r=await (await fetch('/log?after='+after+'&limit=300')).json();
for(const m of r.messages){after=m.id;const c=m.type==='ack'?'ack':/shipped/.test(m.type)?'ship':/rejected/.test(m.type)?'rej':/blocked|waiting/.test(m.type)?'blk':'';
const d=document.createElement('div');d.className='m '+c;
d.innerHTML=`#${m.id} ${esc(m.ts.slice(11))} <b>${esc(m.from)}</b> → ${esc(m.to)} <span class="t">${esc(m.type)}</span> ${esc(JSON.stringify(m.body))}`;
log.prepend(d);}while(log.children.length>500)log.lastChild.remove();}catch(e){}}
bots();poll();setInterval(bots,3000);setInterval(poll,1000);
</script></body></html>"""


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
                if path == "/v1/health":
                    return self._out(200, {"ok": True, "v": 1, "last": broker.last})
                if path == "/v1/messages":
                    me = LONG.get(q.get("to", ""), q.get("to", ""))
                    if not me:
                        raise KeyError("to")
                    got, _ = broker.wait(me, broker.seq_of(q.get("since")), float(q.get("wait", 0)))
                    return self._out(200, [v1_out(broker, m, me) for m in got])
                if path == "/v1/status":
                    return self._out(200, {"presence": broker.presence(), "last": broker.last})
                if path in ("/", "/dashboard"):
                    data = DASHBOARD.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return None
                if path == "/bots":
                    return self._out(200, broker.directory())
                if path == "/wait":
                    topics = [t for t in q.get("topics", "").split(",") if t] or None
                    got, last = broker.wait(q["me"], int(q.get("after", 0)), float(q.get("timeout", 25)), topics)
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
                if path == "/v1/messages":
                    seq = v1_in(broker, b)
                    return self._out(200, {"ok": True, "id": b.get("id") or str(seq), "seq": seq})
                if path == "/send":
                    if b.get("from") and not broker.allow(str(b["from"])):
                        return self._out(429, {"error": "slow down: more than %d messages a second from %s"
                                                        % (RATE_PER_S, b["from"])})
                    return self._out(200, {"id": broker.send(b.get("from"), b.get("to"), b.get("type"), b.get("body"),
                                                             b.get("reply_to"), topic=b.get("topic"))})
                if path == "/register":
                    return self._out(200, {"id": broker.register(b["me"], b.get("role", ""), b.get("handles"),
                                                                 b.get("about", ""))})
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


def serve(folder=DEFAULT_DIR, port=PORT, ready=None, bus_json=None):
    broker = Broker(folder)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(broker))
    server.daemon_threads = True
    if bus_json:   # discovery for the Blender team's client (BUS-SCHEMA: art\BUS.json)
        try:
            os.makedirs(os.path.dirname(bus_json), exist_ok=True)
            with open(bus_json, "w", encoding="utf-8") as f:
                json.dump({"url": "http://127.0.0.1:%d" % server.server_address[1], "v": 1,
                           "spec": "Daedalus2/docs/TEAMLINK.md", "log": broker.path,
                           "since": datetime.datetime.now().isoformat(timespec="seconds")}, f, indent=1)
        except OSError:
            pass
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

    def send(self, to, kind, body=None, reply_to=None, topic=None):
        r = self._call("POST", "/send", {"from": self.me, "to": to, "type": kind, "body": body or {},
                                         "reply_to": reply_to, "topic": topic})
        return r and r.get("id")

    def register(self, role="", handles=None, about=""):
        r = self._call("POST", "/register", {"me": self.me, "role": role, "handles": handles or [], "about": about})
        return r and r.get("id")

    def bots(self):
        return self._call("GET", "/bots") or {}

    def wait(self, after, timeout=25.0, topics=None):
        r = self._call("GET", "/wait?me=%s&after=%d&timeout=%s%s" % (self.me, after, timeout,
                                                                      "&topics=" + ",".join(topics) if topics else ""),
                       timeout=timeout + 5)
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
    s.add_argument("--bus-json", default=os.path.join(os.path.dirname(DEFAULT_DIR), "art", "BUS.json"),
                   help="where to write {url} for clients to find the broker ('' for none)")
    for name in ("send", "wait", "pending", "presence", "ping", "log"):
        p = sub.add_parser(name)
        p.add_argument("--me", default="unreal-team")
        p.add_argument("--port", type=int, default=PORT)
        if name == "send":
            p.add_argument("--to", required=True)
            p.add_argument("--type", required=True)
            p.add_argument("--body", default="{}", help="JSON (or use --asset / --text: no quoting trouble in PowerShell)")
            p.add_argument("--asset", help="shorthand for --body {\"asset\": ...}")
            p.add_argument("--text", nargs="+", help="shorthand for --body {\"text\": ...}; the rest of the line")
        if name in ("wait", "log"):
            p.add_argument("--after", type=int, default=0)
            p.add_argument("--timeout", type=float, default=25)
        if name == "ping":
            p.add_argument("--to", default="blender-team")
            p.add_argument("--timeout", type=float, default=20)
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        serve(a.folder, a.port, bus_json=a.bus_json or None)
        return 0
    link = Link(a.me, a.port)
    if a.cmd == "send":
        body = json.loads(a.body)
        if a.asset:
            body["asset"] = a.asset
        if a.text:
            body["text"] = " ".join(a.text)
        out = {"id": link.send(a.to, a.type, body)}
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
