# SPDX-License-Identifier: MIT
"""Prismheart waystones (contest G10): wake them on foot, travel between awake ones for gold and time, saved at the inn (Playwright).

    python tools/rpg_demo/waystone_test.py DEMO_DIR

Checks: data.json carries the placed waystones and the fare; a new journey has none awake; stepping on one wakes it once
(toast + dialog), a second visit with no other awake stone does nothing; with two awake the stone offers the trip with
its fare; GO pays base + per-tile gold, takes 30 minutes and lands you on the other stone; a short purse is refused and
keeps the gold; NEXT walks the offers nearest first and STAY leaves you put; the inn writes a WAY1 string; CONTINUE
brings back exactly the awake stones; a corrupt WAY1 string loads as none awake (the rest of the save still loads); a
save from before waystones still loads; NEW GAME clears them; no page errors.
"""
import functools, http.server, json, os, sys, threading
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot import Bot  # noqa: E402

DEMO = sys.argv[1]
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=DEMO))
threading.Thread(target=srv.serve_forever, daemon=True).start()
D = json.load(open(os.path.join(DEMO, "data.json"), encoding="utf-8"))
WORLD, WT, WS, FARE = D["world"], D["world_tiles"], D["waystones"], D["waystone_fare"]
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

DIRS = {"left": (1, 0), "right": (-1, 0), "up": (0, 1), "down": (0, -1)}     # walk <dir> from (x+dx, y+dy) onto (x, y)
SPOTS = {(w["x"], w["y"]) for w in WS} | {(c["x"], c["y"]) for c in D.get("sky_caches", [])}
def approach(w):
    for d, (dx, dy) in DIRS.items():
        x, y = w["x"] + dx, w["y"] + dy
        if 0 <= y < len(WORLD) and 0 <= x < len(WORLD[0]):
            t = WT.get(WORLD[y][x], {})
            if t.get("walkable") and t.get("kind") != "landmark" and (x, y) not in SPOTS:
                return d, x, y
    raise SystemExit("no tile next to waystone " + w["id"])

check("data.json has the placed waystones and the fare", len(WS) >= 2 and all({"id", "bit", "name", "x", "y"} <= set(w) for w in WS)
      and {"base_gold", "gold_per_tile", "minutes"} <= set(FARE), [w["id"] for w in WS])
check("every waystone stands on walkable, non-landmark ground", all(WT[WORLD[w["y"]][w["x"]]]["walkable"] and WT[WORLD[w["y"]][w["x"]]].get("kind") != "landmark" for w in WS))

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout; st = bot.st
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(3)"); ev("PRISM_DEMO.speed(6)")
    def new_game():
        for _ in range(30):
            s = st()
            if s["mode"] == "field" and not s["dialog"]: break
            bot.press("start" if s["mode"] == "name" else "a", 150)
        W(1200); bot.clear()
    def title(cont=True):
        pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
        ev("PRISM_DEMO.speed(6)")
        if cont:
            bot.press("down", 150); bot.press("a", 300); W(1200); bot.clear()
        else:
            new_game()
    awake = lambda: sorted(w["id"] for w in ev("PRISM_DEMO.waystones()") if w["awake"])
    def walk_onto(w):
        d, x, y = approach(w)
        ev("PRISM_DEMO.warp('world',%d,%d)" % (x, y)); W(150)
        ev("PRISM_DEMO.hold('%s',true)" % d)
        for _ in range(200):
            s = st()
            if (s["x"], s["y"]) == (w["x"], w["y"]): break
            W(10)
        ev("PRISM_DEMO.hold('%s',false)" % d); W(900)                # let the question finish typing before answering
        return st()

    new_game()
    check("a new journey has no waystones awake", awake() == [], awake())
    A, B, C = WS[0], WS[1], WS[2]
    s = walk_onto(A)
    check("stepping on " + A["name"] + " wakes it (dialog + toast)", awake() == [A["id"]] and s["dialog"] and "WAKES" in s["dialog"]
          and "WAYSTONE" in ev("PRISM_DEMO.toast()").upper(), (s["dialog"], ev("PRISM_DEMO.toast()")))
    bot.clear()
    s = walk_onto(A)
    check("a second visit with no other stone awake does nothing", awake() == [A["id"]] and not s["dialog"], s["dialog"])
    walk_onto(B); bot.clear()
    check("two awake", awake() == sorted([A["id"], B["id"]]), awake())

    tiles = abs(A["x"] - B["x"]) + abs(A["y"] - B["y"]); fare = FARE["base_gold"] + FARE["gold_per_tile"] * tiles
    ev("PRISM_DEMO.setGold(%d)" % (fare - 1))
    s = walk_onto(A)
    check("an awake stone offers the trip with its fare", s["dialog"] and B["name"].upper() in s["dialog"] and (" %d G" % fare) in s["dialog"], s["dialog"])
    bot.press("a", 300)
    s = st()
    check("a short purse is refused and keeps the gold", s["gold"] == fare - 1 and (s["x"], s["y"]) == (A["x"], A["y"]) and s["dialog"] and ("ASKS %d GOLD" % fare) in s["dialog"], (s["gold"], s["dialog"]))
    bot.clear()

    ev("PRISM_DEMO.setGold(500)"); ev("PRISM_DEMO.setClock(2, 600)")
    walk_onto(B); W(100)
    t0 = ev("PRISM_DEMO.clock()")["minute"]
    bot.press("a", 900); bot.clear(); W(300)
    s = st(); c = ev("PRISM_DEMO.clock()")
    check("GO pays %d gold, takes %d minutes and lands on %s" % (fare, FARE["minutes"], A["name"]),
          s["gold"] == 500 - fare and (s["x"], s["y"]) == (A["x"], A["y"]) and s["map"] == "world" and c["minute"] - t0 == FARE["minutes"], (s["gold"], s["x"], s["y"], c["minute"] - t0))

    walk_onto(C); bot.clear()
    ev("PRISM_DEMO.setGold(500)")
    s = walk_onto(A)
    near = sorted([B, C], key=lambda w: (abs(w["x"] - A["x"]) + abs(w["y"] - A["y"]), w["id"]))
    first = s["dialog"] or ""
    bot.press("down", 150); bot.press("a", 900); s2 = st()
    second = s2["dialog"] or ""
    check("offers walk nearest first (NEXT)", near[0]["name"].upper() in first and near[1]["name"].upper() in second, (first, second))
    bot.press("down", 150); bot.press("a", 300); W(200); s3 = st()
    check("STAY leaves you put and keeps the gold", (s3["x"], s3["y"]) == (A["x"], A["y"]) and s3["gold"] == 500 and not s3["dialog"], (s3["x"], s3["y"], s3["gold"], s3["dialog"]))

    want = awake()
    bot.rest()
    key = ev("Object.keys(localStorage).find(k => { try { return JSON.parse(localStorage.getItem(k)).v === 1 } catch (e) { return false } })")
    sv = json.loads(ev("localStorage.getItem(%s)" % json.dumps(key)))
    mask = sum(1 << w["bit"] for w in WS if w["id"] in want)
    check("the inn writes a WAY1 string with the awake bits", isinstance(sv.get("ways"), str) and sv["ways"].startswith("WAY1.%x." % mask), sv.get("ways"))
    title()
    check("CONTINUE brings back exactly the awake stones", awake() == want and st()["mode"] == "field", awake())

    bad = dict(sv); bad["ways"] = sv["ways"][:-1] + ("0" if sv["ways"][-1] != "0" else "1")
    ev("localStorage.setItem(%s, %s)" % (json.dumps(key), json.dumps(json.dumps(bad))))
    title()
    check("a corrupt WAY1 string loads as none awake; the rest of the save loads", awake() == [] and st()["mode"] == "field" and st()["gold"] == sv["gold"], (awake(), st()["gold"]))
    old = dict(sv); old.pop("ways")
    ev("localStorage.setItem(%s, %s)" % (json.dumps(key), json.dumps(json.dumps(old))))
    title()
    check("a save from before waystones still loads (none awake)", awake() == [] and st()["mode"] == "field", awake())
    ev("localStorage.setItem(%s, %s)" % (json.dumps(key), json.dumps(json.dumps(sv))))
    title(cont=False)
    check("NEW GAME clears them", awake() == [], awake())
    pg.screenshot(path=os.path.join(DEMO, "..", "t_waystone.png"))
    check("no page errors", not errs, errs[:3])
    b.close()

k = sum(res)
print("WAYSTONES %d/%d %s" % (k, len(res), "PASS" if k == len(res) else "FAIL"))
sys.exit(0 if k == len(res) else 1)
