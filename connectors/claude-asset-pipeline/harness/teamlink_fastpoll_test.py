# SPDX-License-Identifier: MIT
"""Fast post-and-poll on the team link: SSE /stream, receipts, the must-act waker, and backward compatibility.

    python harness/teamlink_fastpoll_test.py    # prints n/m last; exits 1 on a failure

Runs its own broker on a free port with a temp folder (never the live one on 9890). The webhook values below are
fakes, used to prove they never show up in logs or responses.
"""
import io
import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from asset_pipeline import teamlink   # noqa: E402

results = []
FAKE_URL = "https://hooks.example.invalid/fake-webhook-path-XYZ123"
FAKE_KEY = "FAKEKEY-not-a-secret-0000"


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s %s" % ("ok  " if ok else "FAIL", name, "" if ok else str(detail)[:300]))


def write_cfg(path, **wake):
    cfg = {"url": FAKE_URL, "key": FAKE_KEY, "header": "Authorization", "prefix": "Bearer ",
           "routes": {"grokbot": {}, "grokbot2": {}, "skipme": {}}, "overrides": {"2hot2trot": {}}}
    if wake:
        cfg["wake"] = wake
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)


# ---------------------------------------------------------------- 1. backward compatibility over HTTP
d = tempfile.mkdtemp(prefix="link-fast-")
cfg = os.path.join(d, "relay-webhook.json")
write_cfg(cfg)
logged = []
posts = []
box = {}
port_probe = socket.socket()
port_probe.bind(("127.0.0.1", 0))
PORT = port_probe.getsockname()[1]
port_probe.close()
check("test port is not the live 9890", PORT != 9890)
threading.Thread(target=teamlink.serve, kwargs={"folder": d, "port": PORT, "bus_json": None,
                                                "ready": lambda s, br: box.update(server=s, broker=br)},
                 daemon=True).start()
for _ in range(100):
    if "broker" in box:
        break
    time.sleep(0.05)
br = box["broker"]
base = "http://127.0.0.1:%d" % PORT


def get(path, timeout=10):
    with urllib.request.urlopen(base + path, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def post(path, obj):
    req = urllib.request.Request(base + path, data=json.dumps(obj).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


st, out = post("/send", {"from": "alice", "to": "bob", "type": "note", "body": {"text": "hi"}})
check("compat: POST /send returns {id}", st == 200 and out == {"id": 1}, out)
st, out = get("/pending?me=bob")
check("compat: GET /pending?me= lists the message", st == 200 and [m["id"] for m in out["messages"]] == [1], out)
st, out = get("/wait?me=bob&after=0&timeout=0")
check("compat: GET /wait returns {messages, last}", st == 200 and out["last"] == 1 and out["messages"][0]["id"] == 1)
st, out = post("/ack", {"me": "bob", "id": 1})
check("compat: POST /ack returns {ok, new}", st == 200 and out == {"ok": True, "new": True}, out)
check("compat: pending empties after ack", get("/pending?me=bob")[1]["messages"] == [])
st, out = post("/lock", {"me": "alice", "name": "unreal", "note": "t"})
check("compat: POST /lock", st == 200 and out["ok"] is True, out)
st, out = post("/lock", {"me": "bob", "name": "unreal"})
check("compat: a held lock refuses with 409", st == 409 and out["ok"] is False, out)
st, out = post("/unlock", {"me": "alice", "name": "unreal"})
check("compat: POST /unlock", st == 200 and out["ok"] is True, out)
for p in ("/health", "/presence", "/locks", "/bots", "/log?after=0", "/pending-summary?me=bob", "/inbox?me=bob",
          "/v1/health", "/v1/status"):
    check("compat: GET %s answers 200" % p, get(p)[0] == 200)
lines = [json.loads(l) for l in open(os.path.join(d, "log.jsonl"), encoding="utf-8")]
check("compat: log.jsonl keeps the same keys per line (no receipt fields added)",
      all(set(m) <= {"id", "ts", "from", "to", "type", "body", "reply_to", "uid", "topic"} for m in lines),
      [sorted(m) for m in lines])
check("compat: receipts live in a sidecar receipts.jsonl", os.path.exists(os.path.join(d, "receipts.jsonl")))

# file bridge unchanged
os.makedirs(os.path.join(d, "outbox"), exist_ok=True)
with open(os.path.join(d, "outbox", "pootscoot.jsonl"), "w", encoding="utf-8") as f:
    f.write(json.dumps({"to": "alice", "type": "note", "body": {"text": "from files"}}) + "\n")
br.send("alice", "pootscoot", "note", {"text": "to files"})
ok_in = ok_out = False
for _ in range(60):
    msgs = [m for m in br.messages if m["from"] == "pootscoot"]
    ip = os.path.join(d, "inbox", "pootscoot.jsonl")
    ok_out = bool(msgs)
    ok_in = os.path.exists(ip) and any((json.loads(l).get("body") or {}).get("text") == "to files" for l in open(ip, encoding="utf-8"))
    if ok_in and ok_out:
        break
    time.sleep(0.1)
check("compat: file bridge outbox line becomes a message", ok_out)
check("compat: file bridge inbox gets the JSONL line", ok_in)

# ---------------------------------------------------------------- 2. SSE /stream
got = {}


def reader():
    with urllib.request.urlopen(base + "/stream?me=carol&max_s=5", timeout=10) as r:
        t0 = time.monotonic()
        for raw in r:
            line = raw.decode("utf-8").rstrip("\n")
            if line.startswith("data: "):
                got["m"] = json.loads(line[6:])
                got["dt"] = time.monotonic() - got["sent"]
                return


got["sent"] = 0
th = threading.Thread(target=reader, daemon=True)
th.start()
time.sleep(0.4)
got["sent"] = time.monotonic()
mid = br.send("dave", "carol", "question", {"text": "stream me"})
th.join(6)
check("stream: SSE pushes the message", got.get("m", {}).get("id") == mid, got)
check("stream: within about a second", got.get("dt", 99) < 1.0, got.get("dt"))
st, out = get("/receipts?id=%d" % mid)
check("receipts: SSE delivery stamps delivered_at", out["receipts"][0]["delivered_at"] is not None, out)
check("receipts: read_at is empty before ack", out["receipts"][0]["read_at"] is None, out)
post("/ack", {"me": "carol", "id": mid})
out = get("/receipts?id=%d" % mid)[1]
check("receipts: ack stamps read_at", out["receipts"][0]["read_at"] not in (None, "acked"), out)
out = get("/receipts?from=dave")[1]
check("receipts: ?from= lists what a sender sent", [r["id"] for r in out["receipts"]] == [mid], out)
out = get("/receipts?me=carol")[1]
check("receipts: ?me= lists what an addressee got", [r["id"] for r in out["receipts"]] == [mid], out)
check("compat: /send without fields is still a 400", post("/send", {})[0] == 400)
b2 = teamlink.Broker(d)
check("receipts: survive a restart", b2.receipts.get(("carol", mid), {}).get("read_at") is not None)
check("compat: no waker unless --wake-config", get("/wake-status")[1] == {"enabled": False})

# ---------------------------------------------------------------- 3. the waker (injected clock + poster)
d3 = tempfile.mkdtemp(prefix="link-wake-")
cfg3 = os.path.join(d3, "relay-webhook.json")
write_cfg(cfg3, skip=["skipme"])
clock = {"t": 1760000000.0}
b3 = teamlink.Broker(d3, clock=lambda: clock["t"])
sent = []
lines = []
w = teamlink.Waker(b3, cfg3, clock=lambda: clock["t"], post=lambda t, p: sent.append((t, p)) or True,
                   log=lines.append)

for kind in ("note", "fyi", "status", "asset.ready", "ping"):
    b3.send("claude", "grokbot", kind, {"text": "x"})
b3.send("claude", "*", "need", {"text": "broadcast"})
q0 = b3.send("claude", "grokbot2", "question", {"text": "q"})
b3.ack("grokbot2", q0)     # makes an ack (receipt) message to claude, and receipts.jsonl lines
check("waker: notes, FYIs, statuses, receipts, acks and broadcasts cause no wake", w.tick() == [] and sent == [], sent)

n1 = b3.send("claude", "grokbot", "need", {"text": "SECRET BODY one"})
n2 = b3.send("codex", "grokbot", "QUESTION", {"text": "SECRET BODY two"})
n3 = b3.send("cursor", "grokbot", "need", {"text": "SECRET BODY three"})
woke = w.tick()
check("waker: three must-act messages become ONE wake", woke == [("grokbot", [n1, n2, n3])] and len(sent) == 1, woke)
text = sent[0][1]["messages"][0]["text"]
check("waker: wake text is one line with ids and a pointer", "\n" not in text and "ids %d,%d,%d" % (n1, n2, n3) in text
      and "GET /pending?me=grokbot" in text, text)
check("waker: no message bodies in the wake", "SECRET BODY" not in json.dumps(sent[0][1]), sent[0][1])
check("waker: poster gets the url and key from the local config", sent[0][0]["url"] == FAKE_URL and sent[0][0]["key"] == FAKE_KEY)

n4 = b3.send("claude", "grokbot", "need", {"text": "later"})
clock["t"] += 60
check("waker: rate limit holds a second wake inside 5 min", w.tick() == [] and len(sent) == 1)
n5 = b3.send("claude", "grokbot", "question", {"text": "later 2"})
clock["t"] += 241
woke = w.tick()
check("waker: after 5 min the queued ones go as one digest", woke == [("grokbot", [n4, n5])], woke)
n6 = b3.send("claude", "grokbot", "need", {"text": "acked first"})
b3.ack("grokbot", n6)
clock["t"] += 400
check("waker: a message acked before its wake is dropped", w.tick() == [])

b3.send("grokbot2", "grokbot", "need", {"text": "g2g"})
clock["t"] += 400
check("waker: grok-to-grok need wakes by default", len(w.tick()) == 1)
write_cfg(cfg3, skip=["skipme"], grok_to_grok=False)
b3.send("grokbot2", "grokbot", "need", {"text": "g2g off"})
clock["t"] += 400
check("waker: grok_to_grok false is config, no code change", w.tick() == [])
b3.send("claude", "skipme", "need", {"text": "relay covers me"})
b3.send("claude", "unrouted", "need", {"text": "not a grok bot"})
check("waker: skip list and unrouted bots get no wake", w.tick() == [])
write_cfg(cfg3, min_interval_s=30)
b3.send("claude", "grokbot2", "need", {"text": "a"})
clock["t"] += 400
w.tick()
b3.send("claude", "grokbot2", "need", {"text": "b"})
clock["t"] += 31
check("waker: min_interval_s is configurable", len(w.tick()) == 1)
b3.send("claude", "2hot2trot", "need", {"text": "override"})
clock["t"] += 400
check("waker: bots listed under overrides are routed", [x[0] for x in w.tick()] == ["2hot2trot"])

# a failing post: logged without the url/key or the exception text
def boom(t, p):
    raise OSError("connect to %s with %s failed" % (t["url"], t["key"]))


w.post = boom
b3.send("claude", "grokbot", "need", {"text": "will fail"})
clock["t"] += 400
w.tick()
st3 = w.status()
blob = json.dumps(st3) + "\n".join(lines)
check("waker: a failed post keeps the message queued for retry", st3["failed"] == 1 and st3["queued"].get("grokbot"), st3)
check("secrets: never in waker logs or /wake-status", FAKE_URL not in blob and FAKE_KEY not in blob and "hooks.example" not in blob, blob)

# secrets via HTTP: a served broker with the fake config
box4 = {}
p4 = socket.socket()
p4.bind(("127.0.0.1", 0))
PORT4 = p4.getsockname()[1]
p4.close()
d4 = tempfile.mkdtemp(prefix="link-wake-http-")
cfg4 = os.path.join(d4, "relay-webhook.json")
write_cfg(cfg4)
buf = io.StringIO()
real_stdout = sys.stdout
sys.stdout = buf   # capture everything the broker prints
try:
    threading.Thread(target=teamlink.serve, kwargs={"folder": d4, "port": PORT4, "bus_json": None,
                                                    "wake_config": cfg4,
                                                    "ready": lambda s, br: box4.update(broker=br)},
                     daemon=True).start()
    for _ in range(100):
        if "broker" in box4:
            break
        time.sleep(0.05)
    box4["broker"].send("claude", "grokbot", "need", {"text": "x"})   # the real poster fails on .invalid
    time.sleep(2.5)
finally:
    sys.stdout = real_stdout
base = "http://127.0.0.1:%d" % PORT4
responses = ""
for p in ("/wake-status", "/health", "/pending?me=grokbot", "/receipts?me=grokbot", "/log?after=0", "/bots", "/nope"):
    try:
        responses += json.dumps(get(p)[1])
    except urllib.error.HTTPError as e:
        responses += e.read().decode("utf-8")
check("waker: on with --wake-config", '"enabled": true' in responses)
everything = responses + buf.getvalue() + open(os.path.join(d4, "log.jsonl"), encoding="utf-8").read()
if os.path.exists(os.path.join(d4, "receipts.jsonl")):
    everything += open(os.path.join(d4, "receipts.jsonl"), encoding="utf-8").read()
check("secrets: fake url/key never in responses, stdout, log.jsonl or receipts.jsonl",
      FAKE_URL not in everything and FAKE_KEY not in everything and "hooks.example" not in everything)

print("%d/%d" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
