# SPDX-License-Identifier: MIT
"""Prismheart airship: the Prism Skiff lifts after the first Warden, flies anywhere, lands on open ground (Playwright).

    python tools/rpg_demo/airship_test.py DEMO_DIR

Checks: the skiff sprite is in the atlas (two square frames); before the first Warden the dock says the envelope
hangs slack and nothing boards; after it, walking onto the skiff boards it; aboard you cross mountains and deep sea
the walker cannot; flying is faster than walking; no random battle in 60 flown steps over battle ground; landmarks do
not open from the air; A over a mountain refuses to land, A over grass lands and parks the skiff there; walking away
leaves it parked, walking back boards it; a chest waits in each pocket of land no one can walk to (armour the shops do
not sell), landing on it opens it once; the parked spot and the opened caches are is saved at the inn and comes back on CONTINUE; NEW GAME
moors it at the dock again; no page errors.
"""
import functools, http.server, json, os, sys, threading, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot import Bot  # noqa: E402

DEMO = sys.argv[1]
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=DEMO))
threading.Thread(target=srv.serve_forever, daemon=True).start()
D = json.load(open(os.path.join(DEMO, "data.json"), encoding="utf-8"))
WORLD, WT = D["world"], D["world_tiles"]
PAD = next((x, y) for y, r in enumerate(WORLD) for x, c in enumerate(r) if c == "AirshipPad")
FIRST_WARDEN = D["dungeons"][0]["boss_data"]["name"]
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

def tile(x, y):
    return WORLD[y][x] if 0 <= y < len(WORLD) and 0 <= x < len(WORLD[0]) else None

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout; st = bot.st
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(4)"); ev("PRISM_DEMO.speed(6)")
    air = lambda: ev("PRISM_DEMO.airship()")

    def new_game():
        for _ in range(30):
            s = st()
            if s["mode"] == "field" and not s["dialog"]: break
            bot.press("start" if s["mode"] == "name" else "a", 150)
        W(1200); bot.clear()

    def warp(x, y):
        ev("PRISM_DEMO.warp('world',%d,%d)" % (x, y)); W(150)

    def step(d, n=1, limit=3000):
        """Hold a direction until the hero has moved n tiles (or bumped). Returns tiles moved."""
        moved = 0
        for _ in range(n):
            s0 = st(); ev("PRISM_DEMO.hold('%s',true)" % d)
            t0 = time.time()
            while (time.time() - t0) * 1000 < limit:
                s = st()
                if (s["x"], s["y"]) != (s0["x"], s0["y"]) or s["mode"] != "field" or s["dialog"]: break
                W(15)
            ev("PRISM_DEMO.hold('%s',false)" % d); W(140)
            s = st()
            if (s["x"], s["y"]) == (s0["x"], s0["y"]): break
            moved += 1
            if s["mode"] != "field" or s["dialog"]: break
        return moved

    r = D["rects"]["sprites"].get("Vehicle_Prism_Airship")
    check("the skiff sprite is in the atlas: two square frames", r and r[2] == 2 * r[3], r)

    new_game()
    warp(PAD[0] - 1, PAD[1])
    a0 = air()
    check("a new journey: the skiff is moored at the dock, not yet able to fly", not a0["unlocked"] and (a0["x"], a0["y"]) == PAD, a0)
    step("right")
    s = st()
    check("before the first Warden the dock says the envelope hangs slack", s["dialog"] and "SLACK" in s["dialog"], s["dialog"])
    bot.clear()
    check("...and nothing boards", not air()["flying"])

    ev("PRISM_DEMO.beat(%s)" % json.dumps(FIRST_WARDEN))
    warp(PAD[0] - 1, PAD[1])
    check("after the first Warden the skiff can fly", air()["unlocked"])
    step("right")
    check("walking onto the skiff boards it", air()["flying"] and st()["map"] == "world", air())
    pg.screenshot(path=os.path.join(DEMO, "..", "t_airship.png"))

    # mountains and deep sea, which the walker cannot cross
    mx, my = next((x, y) for y, row in enumerate(WORLD) for x, c in enumerate(row)
                  if c == "Mountain" and tile(x - 1, y) and WT.get(tile(x - 1, y), {}).get("airship_lands"))
    warp(mx - 1, my)
    check("aboard, a warp keeps you flying", air()["flying"])
    step("right")
    check("aboard you fly over a mountain", (st()["x"], st()["y"]) == (mx, my) and tile(mx, my) == "Mountain", (st()["x"], st()["y"]))
    bot.press("a", 250)
    check("A over a mountain refuses to land", air()["flying"] and "NO PLACE" in ev("PRISM_DEMO.toast()"), ev("PRISM_DEMO.toast()"))
    sx, sy = next((x, y) for y, row in enumerate(WORLD) for x, c in enumerate(row) if c == "DeepSea" and tile(x + 1, y) == "DeepSea" and tile(x + 2, y) == "DeepSea")
    warp(sx, sy); step("right", 2)
    check("aboard you fly over deep sea", tile(st()["x"], st()["y"]) == "DeepSea" and st()["x"] == sx + 2, (st()["x"], st()["y"]))

    # speed: tiles covered while holding a direction for the same time
    def tiles_in(ms, d="right"):
        s0 = st(); ev("PRISM_DEMO.hold('%s',true)" % d); W(ms); ev("PRISM_DEMO.hold('%s',false)" % d); W(300)
        return abs(st()["x"] - s0["x"])
    gx, row = next((x, y) for y, r_ in enumerate(WORLD) for x in range(len(r_) - 9)
                   if WT.get(r_[x], {}).get("airship_lands") and all(WT.get(c, {}).get("walkable") and WT.get(c, {}).get("kind") != "landmark" for c in r_[x:x + 9]))
    warp(gx, row); fly = tiles_in(600)
    warp(gx, row); bot.press("a", 200)                                         # land at the start of the same stretch
    check("landing on grass works", not air()["flying"], air())
    step("right"); warp(gx + 1, row); walk = tiles_in(600)
    check("flying is faster than walking", fly > walk >= 1, {"fly": fly, "walk": walk})

    # no random battles while flying
    zone_tile = next(c for c, t in WT.items() if t.get("encounter_zone"))
    ax, ay = air()["x"], air()["y"]
    warp(ax - 1, ay); step("right")
    check("walking back onto the parked skiff boards it again", air()["flying"], air())
    zx, zy = next((x, y) for y, row in enumerate(WORLD) for x, c in enumerate(row) if c == zone_tile and tile(x + 1, y) and tile(x + 1, y) != "Town")
    warp(zx, zy)
    battles = 0
    for i in range(60):
        step("right" if i % 2 == 0 else "left")
        if st()["mode"] == "battle": battles += 1; break
    check("no random battle in 60 flown steps over battle ground (%s)" % zone_tile, battles == 0 and st()["mode"] == "field")

    # landmarks stay shut from the air
    tx, ty = next((x, y) for y, row in enumerate(WORLD) for x, c in enumerate(row) if c == "Town")
    warp(tx - 1, ty); step("right")
    check("flying over the Town does not enter it", st()["map"] == "world" and (st()["x"], st()["y"]) == (tx, ty), st()["map"])

    # land somewhere new, walk away, the skiff stays
    lx, ly = tx + 1, ty
    if not WT.get(tile(lx, ly), {}).get("airship_lands"):
        lx, ly = next((x, y) for y, row in enumerate(WORLD) for x, c in enumerate(row) if c == "Grass" and abs(x - tx) + abs(y - ty) > 2
                      and WT.get(tile(x + 1, y), {}).get("walkable"))
    warp(lx, ly); bot.press("a", 250)
    a1 = air()
    check("A over open ground lands and parks the skiff there", not a1["flying"] and (a1["x"], a1["y"]) == (lx, ly), a1)
    moved = step("right")
    a2 = air()
    check("walking away leaves it parked", moved == 1 and (a2["x"], a2["y"]) == (lx, ly) and not a2["flying"], a2)

    # sky caches: chests only the skiff can reach
    from collections import deque
    town = next((x, y) for y, row in enumerate(WORLD) for x, c in enumerate(row) if c == "Town")
    foot, q = {town}, deque([town])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if tile(*n) and n not in foot and (WT.get(tile(*n), {}).get("walkable") or WT.get(tile(*n), {}).get("kind") == "landmark"):
                foot.add(n); q.append(n)
    caches = ev("PRISM_DEMO.skyCaches()")
    check("the map has sky caches, each on landable ground no one can walk to",
          len(caches) >= 2 and all((c["x"], c["y"]) not in foot and WT.get(tile(c["x"], c["y"]), {}).get("airship_lands") for c in caches), caches)
    check("...and their loot is armour the shops do not sell", all(c["item"] in D["gear"] and not any(c["item"] == i["name"] for it in D["interiors"].values() for i in it.get("stock", [])) for c in caches[:2]),
          [c["item"] for c in caches])
    c0 = caches[0]
    have = lambda it: ev("PRISM_DEMO.state()")["bag"].get(it, 0)
    n0 = have(c0["item"])
    ax, ay = air()["x"], air()["y"]
    warp(ax - 1, ay); step("right")                                               # board again
    warp(c0["x"], c0["y"]); bot.press("a", 400)
    d0 = st()["dialog"] or ""
    check("landing on a cache opens it: the item goes in the bag", have(c0["item"]) == n0 + 1 and "CHEST" in d0, (n0, have(c0["item"]), d0))
    bot.clear()
    check("...and marks it opened", next(c for c in ev("PRISM_DEMO.skyCaches()") if c["x"] == c0["x"])["opened"])
    step("left"); step("right")                                                   # walk off and back: no second prize
    check("an opened cache gives nothing twice", have(c0["item"]) == n0 + 1 and not st()["dialog"], have(c0["item"]))
    pg.screenshot(path=os.path.join(DEMO, "..", "t_skycache.png"))
    # fly back to ground the party can walk to and park there (a player who rests at the inn walked there)
    if not air()["flying"]:
        a_ = air(); warp(a_["x"] - 1, a_["y"]); step("right")
    lx, ly = next((x, y) for y, row in enumerate(WORLD) for x, c in enumerate(row) if (x, y) in foot and c == "Grass")
    warp(lx, ly); bot.press("a", 300); bot.clear()
    check("parked again on walkable grass before resting", not air()["flying"] and (air()["x"], air()["y"]) == (lx, ly), air())

    # save at the inn, CONTINUE
    bot.rest()
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); bot.press("down", 150); bot.press("a", 300); W(1200); bot.clear()
    warp(1, 1)
    a3 = air()
    check("the parked spot is saved at the inn and back on CONTINUE", a3["unlocked"] and (a3["x"], a3["y"]) == (lx, ly) and not a3["flying"], a3)
    check("opened caches are saved too", next(c for c in ev("PRISM_DEMO.skyCaches()") if c["x"] == c0["x"])["opened"])

    # a skiff saved where no one can walk (field-menu SAVE on a sky cache) flies home on CONTINUE (review 32769)
    rec = lambda v: ev("PRISM_DEMO.recoverAir(%s)" % json.dumps(v))
    reach_land = next((x, y) for y, row in enumerate(WORLD) for x, c in enumerate(row) if (x, y) in foot and WT.get(c, {}).get("airship_lands") and c != "AirshipPad")
    walk_noland = next((x, y) for y, row in enumerate(WORLD) for x, c in enumerate(row) if (x, y) in foot and WT.get(c, {}).get("walkable") and not WT.get(c, {}).get("airship_lands"))
    r1 = rec({"x": reach_land[0], "y": reach_land[1]})
    check("recovery keeps a parked spot the party can walk to", (r1["x"], r1["y"]) == reach_land and not r1["recalled"], r1)
    r2 = rec({"x": c0["x"], "y": c0["y"]})
    check("recovery sends a skiff parked in a walled-off pocket home to the dock", (r2["x"], r2["y"]) == PAD and r2["recalled"], r2)
    r3 = rec({"x": walk_noland[0], "y": walk_noland[1]})
    check("...and one on reachable ground it could never land on (%s)" % tile(*walk_noland), (r3["x"], r3["y"]) == PAD and r3["recalled"], r3)
    bad = [rec(v) for v in ({"x": -1, "y": 3}, {"x": 999, "y": 999}, {"x": "7", "y": 3}, {"x": 2.5, "y": 1}, {})]
    check("...and bad coordinates (negative, off the map, text, fractional, missing)", all((r["x"], r["y"]) == PAD and r["recalled"] for r in bad), bad)
    r4 = rec(None)
    check("no saved skiff: moored at the dock, nothing recalled", (r4["x"], r4["y"]) == PAD and not r4["recalled"], r4)
    # the real path: board, land on the cache, SAVE from the field menu, CONTINUE
    ax, ay = air()["x"], air()["y"]
    ev("PRISM_DEMO.warp('world',%d,%d)" % (PAD[0] - 1, PAD[1])); W(200)
    if air()["x"] != PAD[0] or air()["y"] != PAD[1]:
        warp(ax - 1, ay)
    s_ = st(); a_ = air()
    warp(a_["x"] - 1, a_["y"]); step("right")
    warp(c0["x"], c0["y"]); bot.press("a", 400); bot.clear()
    check("parked on the walled-off cache, on foot", not air()["flying"] and (air()["x"], air()["y"]) == (c0["x"], c0["y"]), air())
    mn = lambda: ev("PRISM_DEMO.menu()")
    bot.press("start", 250)
    while mn()["idx"] != mn()["cmds"].index("SAVE"): bot.press("down", 60)
    bot.press("a", 300); bot.press("b", 150); bot.press("b", 150); bot.clear()
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); bot.press("down", 150); bot.press("a", 300); W(1200); bot.clear()
    warp(1, 1)
    a5 = air()
    check("CONTINUE after a field-menu SAVE on the cache: the skiff is home at the dock, still able to fly", (a5["x"], a5["y"]) == PAD and a5["unlocked"] and not a5["flying"], a5)
    check("...and the cache it found stays opened", next(c for c in ev("PRISM_DEMO.skyCaches()") if c["x"] == c0["x"])["opened"])
    warp(PAD[0] - 1, PAD[1]); step("right")
    check("...and boards from the dock as usual", air()["flying"], air())

    # NEW GAME moors it at the dock again
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); new_game(); warp(1, 1)
    a4 = air()
    check("NEW GAME: moored at the dock, grounded again", not a4["unlocked"] and (a4["x"], a4["y"]) == PAD, a4)
    check("NEW GAME: every cache closed again", not any(c["opened"] for c in ev("PRISM_DEMO.skyCaches()")))
    check("no page errors", not errs, errs[:3])
    b.close()

ok = sum(res)
print("AIRSHIP %d/%d %s" % (ok, len(res), "PASS" if ok == len(res) else "FAIL"))
sys.exit(0 if ok == len(res) else 1)
