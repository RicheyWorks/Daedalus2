# SPDX-License-Identifier: MIT
"""Prismheart time of day: steps pass time, the field darkens at night, lamps glow, the inn wakes you (Playwright).

    python tools/rpg_demo/clock_test.py DEMO_DIR

Checks: a new journey starts day 1 at 08:00; a world-map step costs 4 minutes, a town step 2, a dungeon step 1; a
battle 15; time rolls over midnight into day 2; phases dawn/day/dusk/night at the right hours; the town is clearly
darker at 23:00 than at noon (mean canvas brightness) and indoors stays lit; the field menu shows the clock; at night the rare fish bite more often
(night_weight); a night at the inn wakes you at 07:00 the next day; the clock is saved and back on CONTINUE; a save
from before the clock still loads; NEW GAME resets it; no page errors.
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
WORLD, WT = D["world"], D["world_tiles"]
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

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
    new_game()
    clk = lambda: ev("PRISM_DEMO.clock()")
    c = clk()
    check("a new journey starts on day 1 at 08:00, by day", (c["day"], c["minute"], c["phase"]) == (1, 480, "day"), c)

    def step(d):
        s0 = st(); ev("PRISM_DEMO.hold('%s',true)" % d)
        for _ in range(200):
            s = st()
            if (s["x"], s["y"]) != (s0["x"], s0["y"]): break
            W(10)
        ev("PRISM_DEMO.hold('%s',false)" % d); W(160)
    def cost(kind, x, y, d, floor=0, di=0):
        ev("PRISM_DEMO.warp('%s',%d,%d,%d,%d)" % (kind, x, y, floor, di)); W(200)
        ev("PRISM_DEMO.setClock(1, 600)"); ev("PRISM_DEMO.seed(77)")
        step(d)
        return clk()["minute"] - 600
    gx, gy = next((x, y) for y, r in enumerate(WORLD) for x, c in enumerate(r) if c == "Road" and WT.get(r[x + 1], {}).get("walkable") and WT.get(r[x + 1]).get("kind") != "landmark")
    check("a world-map step takes 4 minutes (on the road: no battle)", cost("world", gx, gy, "right") == 4)
    check("a town step takes 2", cost("town", 11, 12, "up") == 2)
    fl = D["dungeons"][0]["floors"][0]
    sx, sy = fl["stairs_up"]["x"], fl["stairs_up"]["y"]
    dsteps = [(d, sx + dx, sy + dy) for d, (dx, dy) in {"down": (0, 1), "right": (1, 0), "left": (-1, 0), "up": (0, -1)}.items()
              if fl["grid"][sy + dy][sx + dx] in D["dungeon_walkable"]]
    d_, _, _ = dsteps[0]
    dm = cost("dungeon", sx, sy, d_)
    check("a dungeon step takes 1 (a battle there would add 15)", dm in (1, 16), dm)
    ev("PRISM_DEMO.setClock(1, 600)"); ev("PRISM_DEMO.battle('plains')"); W(400)
    check("a battle takes 15 minutes", clk()["minute"] == 615, clk())
    bot.finish()

    ev("PRISM_DEMO.warp('world',%d,%d)" % (gx, gy)); W(200)
    ev("PRISM_DEMO.setClock(1, 1438)"); step("right")
    c = clk()
    check("time rolls over midnight into day 2", (c["day"], c["minute"]) == (2, 2), c)
    ph = {m: ev("(()=>{PRISM_DEMO.setClock(1,%d);return PRISM_DEMO.clock().phase})()" % m) for m in (5 * 60, 7 * 60, 12 * 60, 18 * 60 + 30, 20 * 60, 2 * 60)}
    check("phases: dawn 5, day 7-18, dusk 18-20, night 20-5", ph == {300: "dawn", 420: "day", 720: "day", 1110: "dusk", 1200: "night", 120: "night"}, ph)

    # darkness and lamps (town)
    lamp = next((x, y) for y, r in enumerate(D["town"]["grid"]) for x, c in enumerate(r) if c == "Lamp")
    ev("PRISM_DEMO.warp('town',%d,%d)" % (lamp[0] + 1, lamp[1])); W(200)
    def shot():
        return pg.evaluate("""() => { const c = document.getElementById('screen'), g = c.getContext('2d');
            const d = g.getImageData(0, 0, c.width, c.height).data; let s = 0; for (let i = 0; i < d.length; i += 4) s += d[i] + d[i+1] + d[i+2]; return s / (d.length / 4); }""")
    ev("PRISM_DEMO.setClock(1, 720)"); W(150); noon = shot()
    ev("PRISM_DEMO.setClock(1, 1380)"); W(150); night = shot()
    check("the town is clearly darker at 23:00 than at noon", night < noon * 0.75 and clk()["dark"] > 0.4, (round(noon), round(night)))
    pg.screenshot(path=os.path.join(DEMO, "..", "t_night.png"))
    ev("PRISM_DEMO.warp('Inn',3,6)"); W(200)
    check("indoors stays lit at night", clk()["dark"] == 0)

    # the menu clock
    ev("PRISM_DEMO.warp('world',%d,%d)" % (gx, gy)); W(200); ev("PRISM_DEMO.setClock(3, 21 * 60 + 5)")
    bot.press("start", 300)
    check("the field menu is open with the clock (D3 21:05)", ev("PRISM_DEMO.clock()")["text"] == "D3 21:05" and ev("PRISM_DEMO.menu()") is not None)
    bot.press("b", 200); bot.clear()

    # fish at night
    ev("PRISM_DEMO.setClock(1, 720)"); day = ev("PRISM_DEMO.fishOdds(20000)")
    ev("PRISM_DEMO.setClock(1, 1380)"); nightodds = ev("PRISM_DEMO.fishOdds(20000)")
    check("at night the rare fish feed: carp and koi bite far more often", nightodds.get("Sunscale Carp", 0) > 2 * day.get("Sunscale Carp", 0)
          and nightodds.get("Prismscale Koi", 0) > 2 * day.get("Prismscale Koi", 0), {"day": day, "night": nightodds})

    # the inn
    ev("PRISM_DEMO.setClock(4, 22 * 60)")
    bot.rest()
    c = clk()
    check("a night at the inn wakes you at 07:00 the next day", (c["day"], c["minute"]) == (5, 420), c)
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); bot.press("down", 150); bot.press("a", 300); W(1200); bot.clear()
    c = clk()
    check("the clock is saved and back on CONTINUE", (c["day"], c["minute"]) == (5, 420), c)
    sv = json.loads(ev("localStorage.getItem('prism.demo.save.v1') || localStorage.getItem(Object.keys(localStorage).find(k => k.includes('save')))"))
    sv.pop("day", None); sv.pop("minute", None)
    key = ev("Object.keys(localStorage).find(k => { try { return JSON.parse(localStorage.getItem(k)).v === 1 } catch (e) { return false } })")
    ev("localStorage.setItem(%s, %s)" % (json.dumps(key), json.dumps(json.dumps(sv))))
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); bot.press("down", 150); bot.press("a", 300); W(1200); bot.clear()
    c = clk()
    check("a save from before the clock still loads (day 1, 07:00)", (c["day"], c["minute"]) == (1, 420) and st()["mode"] == "field", c)
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); new_game()
    c = clk()
    check("NEW GAME resets the clock", (c["day"], c["minute"]) == (1, 480), c)
    check("no page errors", not errs, errs[:3])
    b.close()

k = sum(res)
print("CLOCK %d/%d %s" % (k, len(res), "PASS" if k == len(res) else "FAIL"))
sys.exit(0 if k == len(res) else 1)
