# SPDX-License-Identifier: MIT
"""The Prismheart shard quest, played start to finish by the careful bot (bot.py), at 6x clock speed.

    python tools/rpg_demo/quest_test.py DEMO_DIR [SEED]

Checks: the Crystal Shrine is sealed with no shards; the Tower and the Ruins lead into their own dungeons; NEW GAME
starts the dungeons fresh (a chest opened in one journey is closed again in the next); the bot buys each Warden's
weakness at the magic shop, buys better weapons when gold allows, stocks Feathers and Tonics, fields its strongest four by ORDER (recruits included), rests at the inn between dungeons, beats the Pyre, Gale and Light Wardens in order;
the shard count and the Ruler's words follow; the shrine opens at three shards; the half-formed Prism Devourer
falls; the ending rolls and returns to the title. Seeded rolls, so a result never depends on luck.
"""
import functools, http.server, json, os, sys, threading
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot import Bot  # noqa: E402

DEMO = sys.argv[1]; SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 7
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=DEMO))
threading.Thread(target=srv.serve_forever, daemon=True).start()
D = json.load(open(os.path.join(DEMO, "data.json"), encoding="utf-8"))
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout; st = bot.st
    ev("PRISM_DEMO.seed(%d)" % SEED); ev("PRISM_DEMO.speed(6)")
    def new_game():
        for _ in range(30):
            s = st()
            if s["mode"] == "field" and not s["dialog"]: break
            bot.press("start" if s["mode"] == "name" else "a", 150)
        W(1200); bot.clear()                                    # the welcome arrives on a short timer
    def walk_onto(landmark):                              # stand south of it on the world map and step north
        lm = next((x, y) for y, r in enumerate(D["world"]) for x, c in enumerate(r) if c == landmark)
        ev("PRISM_DEMO.warp('world',%d,%d)" % (lm[0], lm[1] + 1)); W(300)
        ev("PRISM_DEMO.hold('up',true)"); pg.wait_for_function("PRISM_DEMO.state().y !== %d || PRISM_DEMO.state().map !== 'world'" % (lm[1] + 1), timeout=4000)
        ev("PRISM_DEMO.hold('up',false)"); W(700)
    new_game(); bot.clear()
    names = [d["name"] for d in D["dungeons"]]
    check("four quest dungeons in the build", names == ["Cinder Forge", "Windcut Aerie", "Sunwell Sanctum", "The Shattered Heart"], names)
    check("the final boss is scaled for three shards, in the open", D["dungeons"][3]["boss_data"].get("demo_scale", {}).get("why", "").startswith("three of six"))
    walk_onto("CrystalShrine")
    check("Crystal Shrine sealed with 0 shards", st()["map"] == "world" and "SEALED" in (st()["dialog"] or ""), st()["dialog"])
    bot.clear()
    walk_onto("Tower")
    check("the Tower leads into the Windcut Aerie", st()["map"] == "dungeon" and st()["dungeon"] == 1, (st()["map"], st()["dungeon"]))
    walk_onto("Ruins")
    check("the Ruins lead into the Sunwell Sanctum", st()["map"] == "dungeon" and st()["dungeon"] == 2, (st()["map"], st()["dungeon"]))
    # chests reset per journey
    walk = set(D["dungeon_walkable"]); fl0 = D["dungeons"][0]["floors"][0]; c = fl0["chests"][0]
    for dx, dy, dn in ((0, 1, "up"), (0, -1, "down"), (1, 0, "left"), (-1, 0, "right")):
        if fl0["grid"][c["y"] + dy][c["x"] + dx] in walk: break
    def open_chest():
        ev("PRISM_DEMO.warp('dungeon',%d,%d,0,0)" % (c["x"] + dx, c["y"] + dy)); W(300); bot.face(dn); bot.press("a", 400)
        t = st()["dialog"]; bot.clear(); return t
    first = open_chest()
    check("a Forge chest opens", "FOUND" in (first or ""), first)
    check("...and stays empty this journey", "EMPTY" in (open_chest() or ""))
    ev("PRISM_DEMO.warp('town',11,10)"); W(300)
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    ev("PRISM_DEMO.seed(%d)" % SEED); ev("PRISM_DEMO.speed(6)")
    new_game(); bot.clear()
    check("NEW GAME: the same chest is full again", "FOUND" in (open_chest() or ""))
    # the quest, in order
    plan = [(0, ["Splash"]), (1, ["Tremor"]), (2, ["Gloom"])]
    fronts = []
    for i, (di, spells) in enumerate(plan):
        for sp in spells: bot.buy_spell(sp)
        bot.gear_up(); bag0 = st()["bag"]; bought = bot.stock_up(); bag1 = st()["bag"]
        if i == 0:
            check("the bot stocks up at the item shop", bought and all(bag1.get(k, 0) - bag0.get(k, 0) == bought.count(k) for k in set(bought)), (bought, bag1))
        bot.rest()
        fronts.append(bot.lineup())
        check("%s: the gate asks, the battle starts" % D["dungeons"][di]["name"], bot.to_boss(di))
        last = bot.fight()
        s = st()
        check("%s: the %s falls" % (D["dungeons"][di]["name"], D["dungeons"][di]["boss_data"]["name"]), s["mode"] == "field" and D["dungeons"][di]["boss_data"]["name"] in s["beaten"],
              (s["mode"], last and last["foes"], [m[1] for m in s["party"]]))
        check("shards: %d" % (i + 1), s["shards"] == i + 1, s["shards"])
        bot.clear()
    ev("PRISM_DEMO.warp('Castle',7,6)"); W(300); bot.face("up"); bot.press("a", 500)
    check("the Ruler sends you to the shrine", "CRYSTAL SHRINE" in (st()["dialog"] or ""), st()["dialog"])
    bot.clear(); bot.gear_up(); bot.stock_up(); bot.rest(); fronts.append(bot.lineup())
    check("recruits fight: Aveline (Silver Lance) is in the front four against the Light Warden and the Devourer",
          "Aveline" in fronts[2] and "Aveline" in fronts[3], fronts)
    eq = {e["name"]: e["weapon"] for e in ev("PRISM_DEMO.equip()")}
    check("boss gold bought the front swordsman a better blade (not the benched one)", eq["Corin"] != "Copper Blade", eq)
    walk_onto("CrystalShrine")
    check("three shards open the Crystal Shrine", st()["map"] == "dungeon" and st()["dungeon"] == 3, (st()["map"], st()["dialog"]))
    check("The Shattered Heart: the gate asks, the battle starts", bot.to_boss(3))
    pg.screenshot(path=os.path.join(DEMO, "..", "t_devourer.png"))
    last = bot.fight()
    check("the half-formed Prism Devourer falls; the ending rolls", st()["mode"] == "ending", (st()["mode"], last and last["foes"], [m[1] for m in st()["party"]]))
    W(2500); pg.screenshot(path=os.path.join(DEMO, "..", "t_ending.png"))
    for _ in range(40):
        if st()["mode"] == "title": break
        bot.press("a", 300)
    check("the ending returns to the title", st()["mode"] == "title")
    check("the journey was saved with all four Wardens", len(json.loads(ev("localStorage.getItem('prism.save.v1')"))["beaten"]) == 4)
    check("no page errors", not errs, errs[:3])
    b.close()
print("QUEST %d/%d" % (sum(res), len(res)), "PASS" if all(res) else "FAIL")
sys.exit(0 if all(res) else 1)
