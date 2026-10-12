# SPDX-License-Identifier: MIT
"""The team link (ADR-053): the broker, its HTTP skin, the client, and the Unreal team's watcher on it.

    python harness/teamlink_test.py        # prints n/m last; exits 1 on a failure
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from asset_pipeline import artqueue, teamlink, wire   # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s %s" % ("ok  " if ok else "FAIL", name, "" if ok else detail))


# 1. The broker alone.
d = tempfile.mkdtemp(prefix="link-")
clock = {"t": 1760000000.0}
b = teamlink.Broker(d, clock=lambda: clock["t"])
i1 = b.send("blender-team", "unreal-team", "asset.ready", {"asset": "Tool_Axe"})
i2 = b.send("blender-team", "*", "note", {"text": "hello all"})
b.send("blender-team", "art-master", "note", {"text": "not for unreal"})
got, last = b.wait("unreal-team", 0, 0)
check("ids only go up", (i1, i2, last) == (1, 2, 3))
check("a team gets what's addressed to it and to everyone, in order", [m["id"] for m in got] == [1, 2], got)
check("a team never gets its own messages", b.wait("blender-team", 0, 0)[0] == [])

t0 = time.monotonic()
threading.Timer(0.15, lambda: b.send("blender-team", "unreal-team", "ping")).start()
got, _ = b.wait("unreal-team", 3, 5)
dt = time.monotonic() - t0
check("a waiting team wakes the moment a message lands (not on a poll)", got and got[0]["type"] == "ping" and dt < 1.0,
      "%.2f s" % dt)
t0 = time.monotonic()
got, _ = b.wait("unreal-team", 99, 0.3)
check("an empty wait ends at its timeout", got == [] and 0.25 < time.monotonic() - t0 < 1.5)

check("pending lists what's not acked", [m["id"] for m in b.pending("unreal-team")] == [1, 2, 4])
check("ack is new the first time", b.ack("unreal-team", 1) is True)
check("ack twice is harmless", b.ack("unreal-team", 1) is False)
check("pending drops the acked one", [m["id"] for m in b.pending("unreal-team")] == [2, 4])
receipt = [m for m in b.wait("blender-team", 0, 0)[0] if m["type"] == "ack"]
check("the sender gets a receipt", receipt and receipt[0]["body"]["id"] == 1 and receipt[0]["reply_to"] == 1, receipt)
try:
    b.ack("unreal-team", 999)
    check("ack of an unknown id is refused", False)
except KeyError:
    check("ack of an unknown id is refused", True)

b.heartbeat("unreal-team", "ok")
clock["t"] += 10
b.heartbeat("blender-team", "building Tool_Axe")
clock["t"] += 25
p = b.presence()
check("presence: the recent beat is alive, the old one is not",
      p["blender-team"]["alive"] and not p["unreal-team"]["alive"] and p["blender-team"]["status"] == "building Tool_Axe", p)

with open(os.path.join(d, "log.jsonl"), "a", encoding="utf-8") as f:
    f.write('{"id": 99, "torn')   # a crash mid-line
b2 = teamlink.Broker(d)
check("restart: the log comes back, a torn line is skipped", b2.last == b.last, (b2.last, b.last))
check("restart: receipts come back too", [m["id"] for m in b2.pending("unreal-team")] == [2, 4])
check("restart: ids keep going up", b2.send("unreal-team", "blender-team", "note", {}) == b.last + 1)
for bad in ((None, "x", "t"), ("a", "", "t"), ("a", "b", "")):
    try:
        b2.send(*bad)
        check("send refuses a message missing from/to/type %s" % (bad,), False)
    except ValueError:
        check("send refuses a message missing from/to/type %s" % (bad,), True)
shutil.rmtree(d)

# 2. Over HTTP, the way both teams use it.
d = tempfile.mkdtemp(prefix="link-")
box = {}
th = threading.Thread(target=teamlink.serve, kwargs={"folder": d, "port": 0,
                                                    "ready": lambda s, br: box.update(server=s, broker=br)}, daemon=True)
th.start()
for _ in range(50):
    if "server" in box:
        break
    time.sleep(0.05)
port = box["server"].server_address[1]
blender, unreal = teamlink.Link("blender-team", port), teamlink.Link("unreal-team", port)
check("health answers", (blender.health() or {}).get("ok") is True)
mid = blender.send("unreal-team", "asset.ready", {"asset": "Tool_Axe"})
msgs, last = unreal.wait(0, 2)
check("HTTP: send then wait", mid == 1 and msgs and msgs[0]["body"]["asset"] == "Tool_Axe", msgs)
unreal.ack(mid)


def responder():
    after = last
    for _ in range(40):
        ms, after = unreal.wait(after, 0.5)
        for m in ms:
            if m["type"] == "ping":
                unreal.ack(m["id"])
                unreal.send(m["from"], "pong", {}, reply_to=m["id"])
                return


threading.Thread(target=responder, daemon=True).start()
t0 = time.time()
pid = blender.send("unreal-team", "ping")
after, pong = 0, None
while pong is None and time.time() - t0 < 5:
    ms, after = blender.wait(after, 2)
    pong = next((m for m in ms if m["type"] == "pong" and m["reply_to"] == pid), None)
rtt = (time.time() - t0) * 1000
check("HTTP: a live ping/pong round trip, well under a second", pong is not None and rtt < 1000, "%.0f ms" % rtt)
check("HTTP: the ping got a receipt", any(m["type"] == "ack" and m["body"]["id"] == pid for m in box["broker"].log(0, 999)))
blender.heartbeat("building")
check("HTTP: presence shows both teams", set(unreal.presence()) >= {"blender-team", "unreal-team"})
req = urllib.request.Request("http://127.0.0.1:%d/send" % port, data=b'{"from":"x"}', method="POST")
try:
    urllib.request.urlopen(req, timeout=3)
    check("HTTP: a bad message is a 400, not a crash", False)
except urllib.error.HTTPError as e:
    check("HTTP: a bad message is a 400, not a crash", e.code == 400 and "required" in json.loads(e.read())["error"])
check("HTTP: the broker is still up after it", unreal.health() is not None)
dead = teamlink.Link("unreal-team", 1)
check("a dead broker: calls return nothing and never raise", dead.send("x", "y") is None and dead.wait(0, 0.1) == ([], 0)
      and dead.up is False)

# 3. The Unreal team's watcher on the link.
BOARD = """# Art queue

| # | Asset | Kind | Size | Status | Notes |
|---|---|---|---|---|---|
| 1 | Tool_Pickaxe | tool | 0.9 m | SHIPPED (440 tris, 0.90 m) | |
| 2 | Tool_Axe | tool | 0.9 m | TODO | |
"""
art = tempfile.mkdtemp(prefix="art-")
with open(os.path.join(art, "QUEUE.md"), "w", encoding="utf-8") as f:
    f.write(BOARD)


def fake_ship(*a, **k):
    return {"ok": True, "checks": [], "dest": "/Game/Daedalus/Art/Tool/" + a[0],
            "blender": {"objects": [{"triangles": 300, "materials": ["m"], "dims": [0.9, 0.1, 0.3]}]},
            "unreal": {"meshes": [{"triangles": 300}]}}


wire.reachable = lambda addr, timeout=2.0: True
wire.call = lambda addr, command, timeout=600, side="bridge", **p: {
    "result": False if "get_game_world" in p["code"] else {"opened": False, "blocked": False} if "open_mainfile" in p["code"]
    else {"source": "collection", "objects": ["Axe_Head"]}}
w = artqueue.Watcher(art, ship=fake_ship, link=unreal)
start = box["broker"].last
mid = blender.send("unreal-team", "asset.ready", {"asset": "Tool_Axe"})
ms, _ = unreal.wait(start, 2)
wake = w.on_message(next(m for m in ms if m["id"] == mid))
rows, _ = artqueue.parse(open(os.path.join(art, "QUEUE.md"), encoding="utf-8").read())
check("watcher: asset.ready turns a TODO row READY and asks for a pass now",
      wake and next(r for r in rows if r["asset"] == "Tool_Axe")["status"] == "READY")
w.tick()
seen = [m for m in box["broker"].log(mid, 999) if m["to"] == "*"]
types = [m["type"] for m in seen]
check("watcher: shipping and shipped go out live to everyone", "asset.shipping" in types and "asset.shipped" in types, types)
check("watcher: the shipped message names the asset and the result",
      any(m["type"] == "asset.shipped" and m["body"]["asset"] == "Tool_Axe" and "SHIPPED" in m["body"]["result"] for m in seen))
mid = blender.send("unreal-team", "asset.ready", {"asset": "Prop_Fern"})
w.on_message(box["broker"].log(mid - 1, 1)[0])
rows, _ = artqueue.parse(open(os.path.join(art, "QUEUE.md"), encoding="utf-8").read())
fern = next((r for r in rows if r["asset"] == "Prop_Fern"), None)
check("watcher: an asset not on the board is added to it, READY, numbered next",
      fern and fern["status"] == "READY" and fern["cells"][0] == "3" and fern["cells"][2] == "prop", fern)
check("watcher: the rest of the board is untouched", "| 1 | Tool_Pickaxe | tool | 0.9 m | SHIPPED (440 tris, 0.90 m) | |"
      in open(os.path.join(art, "QUEUE.md"), encoding="utf-8").read())
mid = blender.send("unreal-team", "ping")
w.on_message(box["broker"].log(mid - 1, 1)[0])
check("watcher: answers a ping with a pong", any(m["type"] == "pong" and m["reply_to"] == mid for m in box["broker"].log(mid, 99)))
mid = blender.send("unreal-team", "queue.status")
w.on_message(box["broker"].log(mid - 1, 1)[0])
st = next((m for m in box["broker"].log(mid, 99) if m["type"] == "queue.state"), None)
check("watcher: queue.status answers with the board's counts", st and st["body"]["counts"].get("SHIPPED") == 2, st)
check("watcher: every message it handled is acked", unreal.pending() == [], unreal.pending())
box["server"].shutdown()
shutil.rmtree(d)
shutil.rmtree(art)

n = sum(results)
print("%d/%d" % (n, len(results)))
sys.exit(0 if n == len(results) else 1)
