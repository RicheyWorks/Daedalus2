# SPDX-License-Identifier: MIT
"""Prismheart: Windmere, the Village on the world map, is a real place now (Playwright).

    python tools/rpg_demo/village_test.py DEMO_DIR

Checks: the village data is packed and every tile has an image; walking onto the Village landmark enters Windmere at
its gate (no more "the way is sealed"); every villager can be walked up to and says their own lines (not the town's);
the barrel gives a Herb Tonic once; the chest gives gold once; walking out of the gate returns to the world map just
south of the Village; Windmere has no random battles; no page errors.
"""
import functools, http.server, json, os, sys, threading, time
from collections import deque
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot import Bot  # noqa: E402

DEMO = sys.argv[1]
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=DEMO))
threading.Thread(target=srv.serve_forever, daemon=True).start()
D = json.load(open(os.path.join(DEMO, "data.json"), encoding="utf-8"))
V, WORLD = D.get("village") or {}, D["world"]
TT = D["town_tiles"]
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

check("Windmere is packed into the demo", V.get("name") == "Windmere" and V.get("landmark") == "Village", V.get("name"))
check("every Windmere tile has an image", all("town:" + c in D["frames"] for r in V["grid"] for c in r))
VX, VY = next((x, y) for y, r in enumerate(WORLD) for x, c in enumerate(r) if c == V["landmark"])
G = V["grid"]
npcs = {(n["x"], n["y"]) for n in V["npcs"]}
walk = lambda x, y: 0 <= y < len(G) and 0 <= x < len(G[0]) and TT.get(G[y][x], {}).get("walkable") and (x, y) not in npcs

def path(a, goal):
    """BFS over Windmere: directions from a to any tile in goal."""
    prev, q = {a: None}, deque([a])
    while q:
        c = q.popleft()
        if c in goal:
            out = []
            while prev[c]:
                p0, d = prev[c]; out.append(d); c = p0
            return out[::-1]
        for d, (dx, dy) in {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.items():
            n = (c[0] + dx, c[1] + dy)
            if n not in prev and walk(*n):
                prev[n] = (c, d); q.append(n)
    return None

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout; st = bot.st
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(5)"); ev("PRISM_DEMO.speed(6)")
    for _ in range(30):
        s = st()
        if s["mode"] == "field" and not s["dialog"]: break
        bot.press("start" if s["mode"] == "name" else "a", 150)
    W(1200); bot.clear()

    def step(d):
        s0 = st(); ev("PRISM_DEMO.hold('%s',true)" % d)
        t0 = time.time()
        while time.time() - t0 < 3:
            s = st()
            if (s["x"], s["y"]) != (s0["x"], s0["y"]) or s["mode"] != "field" or s["dialog"]: break
            W(15)
        ev("PRISM_DEMO.hold('%s',false)" % d); W(160)

    ev("PRISM_DEMO.warp('world',%d,%d)" % (VX, VY + 1)); W(200)
    step("up"); W(1300); bot.clear()
    s = st()
    check("walking onto the Village enters Windmere at its gate", s["map"] == "village" and (s["x"], s["y"]) == (V["spawn"]["x"], V["spawn"]["y"]), (s["map"], s["x"], s["y"]))
    pg.screenshot(path=os.path.join(DEMO, "..", "t_village.png"))

    town_lines = {"Elder", "Farmer", "Child", "Sailor", "Mage"}
    for n in V["npcs"]:
        nb = {(n["x"] + dx, n["y"] + dy): d for (dx, dy), d in {(0, 1): "up", (0, -1): "down", (1, 0): "left", (-1, 0): "right"}.items()}
        here = (st()["x"], st()["y"])
        route = path(here, set(k for k in nb if walk(*k)))
        if route is None:
            check("reach the %s" % n["type"], False); continue
        for d in route:
            step(d)
        bot.face(nb[(st()["x"], st()["y"])])
        bot.press("a", 500)
        said = st()["dialog"] or ""
        check("the %s says their own Windmere line" % n["type"], said and said.startswith(n["lines"][0][:24]), said[:60])
        for _ in range(8):
            if not st()["dialog"]: break
            bot.press("a", 300)
        check("...no battle broke out on the way (%d steps)" % len(route), st()["mode"] == "field" and st()["map"] == "village")

    def interact_tile(name):
        tx, ty = next((x, y) for y, r in enumerate(G) for x, c in enumerate(r) if c == name)
        nb = {(tx + dx, ty + dy): d for (dx, dy), d in {(0, 1): "up", (0, -1): "down", (1, 0): "left", (-1, 0): "right"}.items()}
        route = path((st()["x"], st()["y"]), set(k for k in nb if walk(*k)))
        for d in route: step(d)
        bot.face(nb[(st()["x"], st()["y"])]); bot.press("a", 500)
        out = st()["dialog"] or ""
        for _ in range(6):
            if not st()["dialog"]: break
            bot.press("a", 300)
        bot.face(nb[(st()["x"], st()["y"])]); bot.press("a", 500)
        again = st()["dialog"] or ""
        for _ in range(6):
            if not st()["dialog"]: break
            bot.press("a", 300)
        return out, again

    herbs = st()["bag"].get("Herb Tonic", 0)
    first, again = interact_tile("Barrel")
    check("the barrel gives a Herb Tonic once", "HERB TONIC" in first and "EMPTY" in again and st()["bag"].get("Herb Tonic", 0) == herbs + 1, (first, again))
    g0 = st()["gold"]
    first, again = interact_tile("Chest")
    check("the chest gives gold once", "GOLD" in first and "EMPTY" in again and st()["gold"] > g0, (first, again, g0, st()["gold"]))

    route = path((st()["x"], st()["y"]), {(x, V["exit_row"]) for x in range(len(G[0])) if walk(x, V["exit_row"])})
    for d in route: step(d)
    W(1300)
    s = st()
    check("walking out of the gate returns to the world, just south of the Village", s["map"] == "world" and (s["x"], s["y"]) == (VX, VY + 1), (s["map"], s["x"], s["y"]))
    check("no page errors", not errs, errs[:3])
    b.close()

k = sum(res)
print("VILLAGE %d/%d %s" % (k, len(res), "PASS" if k == len(res) else "FAIL"))
sys.exit(0 if k == len(res) else 1)
