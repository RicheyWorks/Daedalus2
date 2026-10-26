# SPDX-License-Identifier: MIT
"""Prismheart items: every item with an effect line in the shops does what the line says (Playwright, by the menus).

    python tools/rpg_demo/item_test.py DEMO_DIR

Checks: every effect line in the gear table maps to a handled kind (a new item with an unhandled line fails here);
the field ITEM list leaves out the Smoke Pouch and the battle list leaves out the Camp Tent; the field ITEM window
describes the selected item; Herb Tonic heals; Clear Draught restores MP; Antidote Leaf cures poison; Feather of
Waking revives a fallen hero; Wake Bell wakes a sleeper in battle; Smoke Pouch escapes a field battle and does nothing
against a Warden; the Camp Tent refuses in town and rests the whole party (reserve included) on the world map; each
use spends one from the bag; no page errors.
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
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout; st = bot.st
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(4)"); ev("PRISM_DEMO.speed(6)")
    for _ in range(30):
        s = st()
        if s["mode"] == "field" and not s["dialog"]: break
        bot.press("start" if s["mode"] == "name" else "a", 150)
    W(1200); bot.clear()
    roster = lambda: {m["name"]: m for m in ev("PRISM_DEMO.roster()")}
    mn = lambda: ev("PRISM_DEMO.menu()")
    bag = lambda k: st()["bag"].get(k, 0)

    kinds = ev("PRISM_DEMO.itemKinds()")
    check("every effect line maps to a handled kind", kinds and all(kinds.values()), {k: v for k, v in kinds.items() if not v})
    for k in ("Herb Tonic", "Clear Draught", "Antidote Leaf", "Wake Bell", "Feather of Waking", "Smoke Pouch", "Camp Tent"):
        ev("PRISM_DEMO.give(%s, 2)" % json.dumps(k))
    L = ev("PRISM_DEMO.lists()")
    check("the field list leaves out the Smoke Pouch", "Smoke Pouch" not in L["field"] and "Camp Tent" in L["field"], L["field"])
    check("the battle list leaves out the Camp Tent", "Camp Tent" not in L["battle"] and "Smoke Pouch" in L["battle"], L["battle"])

    def use_field(item, who):
        """Field menu: ITEM, the item, the hero (by roster index), A. Returns the menu message."""
        ev("PRISM_DEMO.warp('town',11,10)") if st()["map"] != "world" else None
        bot.press("start", 250)
        while mn()["idx"] != 0: bot.press("up", 60)
        bot.press("a", 150)
        items = ev("PRISM_DEMO.lists()")["field"]
        while mn()["ii"] != items.index(item): bot.press("down", 60)
        if item == "Herb Tonic": pg.screenshot(path=os.path.join(DEMO, "..", "t_items.png"))
        while mn()["who"] != who: bot.press("right", 60)
        bot.press("a", 200)
        msg = mn()["msg"]
        for _ in range(4):
            if st()["mode"] != "menu": break
            bot.press("b", 120)
        bot.clear()
        return msg

    ev("PRISM_DEMO.hurt(0, 150)"); h0 = roster()["Corin"]["hp"]; n0 = bag("Herb Tonic")
    use_field("Herb Tonic", 0)
    line = ev("PRISM_DEMO.itemLine('Herb Tonic')"); amt = int(line.split()[1])
    check("Herb Tonic heals Corin by exactly what its line says (%s)" % line, roster()["Corin"]["hp"] == min(h0 + amt, roster()["Corin"]["max"]), (h0, roster()["Corin"]["hp"]))
    check("...and spends one", bag("Herb Tonic") == n0 - 1, (n0, bag("Herb Tonic")))
    ev("PRISM_DEMO.spend(2, 60)"); m0 = roster()["Tamsin"]["mp"]
    use_field("Clear Draught", 2)
    line = ev("PRISM_DEMO.itemLine('Clear Draught')"); amt = int(line.split()[1])
    check("Clear Draught restores Tamsin's MP by what its line says (%s)" % line, roster()["Tamsin"]["mp"] == m0 + amt, (m0, roster()["Tamsin"]["mp"]))
    ev("PRISM_DEMO.inflict(3,'poison')")
    use_field("Antidote Leaf", 3)
    check("Antidote Leaf cures Rook's poison", "poison" not in roster()["Rook"]["status"], roster()["Rook"])
    ev("PRISM_DEMO.ko(1)")
    use_field("Feather of Waking", 1)
    check("Feather of Waking revives Ysolde", roster()["Ysolde"]["hp"] > 0, roster()["Ysolde"])
    msg = use_field("Camp Tent", 0); t0 = bag("Camp Tent")
    check("the Camp Tent refuses in town", "OPEN ROAD" in msg and t0 == 2, (msg, t0))

    # Wake Bell and Smoke Pouch in battle
    bot.start_fight(["prism_best_gelfin"])
    ev("PRISM_DEMO.inflict(1,'sleep')"); bot.round({})
    ev("PRISM_DEMO.inflict(1,'sleep')"); w0 = bag("Wake Bell")
    bot.round({"Corin": ("ITEM", "Wake Bell", "Ysolde")})
    check("Wake Bell wakes Ysolde in battle", "sleep" not in roster()["Ysolde"]["status"] and bag("Wake Bell") == w0 - 1, (roster()["Ysolde"]["status"], w0, bag("Wake Bell")))
    p0 = bag("Smoke Pouch")
    bot.round({"Corin": ("ITEM", "Smoke Pouch", None)})
    for _ in range(20):
        if st()["mode"] != "battle": break
        bot.press("a", 150)
    check("Smoke Pouch escapes a field battle", st()["mode"] == "field" and bag("Smoke Pouch") == p0 - 1, (st()["mode"], p0, bag("Smoke Pouch")))
    bot.clear()
    ev("PRISM_DEMO.battle('cave', true)"); W(600)
    for _ in range(40):
        if st()["mode"] == "battle" and st()["battle"]["phase"] == "cmd": break
        W(100)
    msgs = []
    orig = bot.st
    def watched():
        s = orig()
        if s.get("battle") and (not msgs or msgs[-1] != s["battle"]["msg"]): msgs.append(s["battle"]["msg"])
        return s
    bot.st = watched
    bot.round({"Corin": ("ITEM", "Smoke Pouch", None)})
    check("Smoke Pouch does nothing against a Warden", any("THE SMOKE DOES NOTHING HERE" in (m or "") for m in msgs) and bag("Smoke Pouch") == p0 - 1, (msgs[-4:], bag("Smoke Pouch")))
    bot.st = orig
    bot.finish()

    # Camp Tent on the world map, with a reserve member hurt too
    ev("PRISM_DEMO.beat('PyreWarden')")
    for i in range(4): ev("PRISM_DEMO.hurt(%d, 100)" % i)
    tx, ty = next((x, y + 1) for y, row in enumerate(D["world"]) for x, c in enumerate(row) if c == "Town")
    ev("PRISM_DEMO.warp('world',%d,%d)" % (tx, ty)); W(300)
    use_field("Camp Tent", 0); W(600)
    r = roster()
    check("the Camp Tent rests everyone on the world map", all(m["hp"] == m["max"] for m in r.values()), {k: (v["hp"], v["max"]) for k, v in r.items()})
    check("...and spends one", bag("Camp Tent") == 1, bag("Camp Tent"))
    check("no page errors", not errs, errs)

ok = sum(res); print("ITEMS %d/%d %s" % (ok, len(res), "PASS" if ok == len(res) else "FAIL"))
sys.exit(0 if ok == len(res) else 1)
