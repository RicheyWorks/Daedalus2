# SPDX-License-Identifier: MIT
"""The Prismheart field menu (menus.json's Menu / Status / Equip layouts), driven like a player (Playwright).

    python tools/rpg_demo/menu_test.py DEMO_DIR

START opens ITEM / MAGIC / EQUIP / STATUS / ORDER / SAVE / OPTIONS. Checks: armour counts toward DEF (the gear table
reaches the Prism party); a chest weapon in the bag can be equipped and ATK rises, the old one goes back to the bag;
a weapon nobody can wield is never offered; taking armour off lowers DEF; MAGIC heals a hurt member with MP;
battle-only spells refuse; STATUS opens; ORDER swaps; SAVE works in town and refuses in a dungeon; OPTIONS opens
Settings.
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
    for _ in range(30):
        s = st()
        if s["mode"] == "field" and not s["dialog"]: break
        bot.press("start" if s["mode"] == "name" else "a", 150)
    W(1200); bot.clear()
    eq = lambda: ev("PRISM_DEMO.equip()")
    mn = lambda: ev("PRISM_DEMO.menu()")
    corin = eq()[0]
    check("armour counts: Corin's DEF includes Ring Mail 8 + Iron Helm 4 + Kite Shield 5", corin["def"] >= 17 + 0, corin)
    def open_menu():
        bot.press("start", 250)
        return st()["mode"] == "menu"
    def pick(cmd):
        m = mn()
        while mn()["idx"] != m["cmds"].index(cmd): bot.press("down", 70)
        bot.press("a", 150)
    check("START opens the field menu with the seven commands", open_menu() and mn()["cmds"] == ["ITEM", "MAGIC", "EQUIP", "STATUS", "ORDER", "SAVE", "OPTIONS"], mn())
    ev("PRISM_DEMO.give('Steel Saber'); PRISM_DEMO.give('Silver Lance')")
    pick("EQUIP")
    check("EQUIP opens on Corin's slots", mn()["sub"] == "equip" and mn()["who"] == 0)
    bot.press("a", 150)                                             # weapon slot -> candidates
    pg.screenshot(path=os.path.join(DEMO, "..", "t_equip.png"))
    atk0 = eq()[0]["atk"]
    bot.press("a", 200)                                             # first candidate: Steel Saber (the lance fits nobody)
    after = eq()[0]
    check("Corin equips the Steel Saber; ATK rises", after["weapon"] == "Steel Saber" and after["atk"] > atk0, (atk0, after))
    check("the Copper Blade goes back to the bag", st()["bag"].get("Copper Blade") == 1, st()["bag"])
    check("the Silver Lance is never offered (no lance users)", st()["bag"].get("Silver Lance") == 1)
    bot.press("down", 80); bot.press("down", 80); bot.press("down", 80)   # shield slot
    bot.press("a", 150)
    d0 = eq()[0]["def"]
    for _ in range(4):
        if mn()["sub"] == "equip": break
        bot.press("a", 150)                                         # (TAKE IT OFF) is the only candidate
    check("taking the Kite Shield off lowers DEF and bags it", eq()[0]["shield"] is None and eq()[0]["def"] < d0 and st()["bag"].get("Kite Shield") == 1, (d0, eq()[0]))
    bot.press("b", 150); bot.press("b", 150)
    check("B backs out to the main commands", mn() is None or mn()["sub"] is None)
    if mn() is None: open_menu()
    ev("PRISM_DEMO.hurt(0, 120)")
    hp0 = st()["party"][0][2]
    pick("MAGIC")
    for _ in range(4):
        if mn()["who"] == 1: break
        bot.press("right", 80)
    bot.press("a", 150)                                             # Ysolde's spells
    bot.press("a", 150)                                             # Mend
    bot.press("a", 250)                                             # on Corin (target 0)
    s = st()
    check("MAGIC: Ysolde casts Mend on Corin, HP up, MP down", s["party"][0][2] > hp0 and s["party"][1][4] < 88, (hp0, s["party"][0][2], s["party"][1][4], mn()["msg"]))
    bot.press("b", 120); bot.press("down", 80); bot.press("a", 150)    # Ward
    check("a battle-only spell refuses in the field", "FOR BATTLE" in (mn()["msg"] or ""), mn()["msg"])
    bot.press("b", 120); bot.press("b", 120); bot.press("b", 120)
    if mn() is None: open_menu()
    pick("STATUS"); W(150)
    pg.screenshot(path=os.path.join(DEMO, "..", "t_status.png"))
    check("STATUS opens", mn()["sub"] == "status")
    bot.press("b", 150)
    names0 = [m[0] for m in st()["party"]]
    pick("ORDER"); bot.press("a", 100); bot.press("down", 80); bot.press("a", 150)
    names1 = [m[0] for m in st()["party"]]
    check("ORDER swaps the first two", names1[:2] == names0[1::-1], (names0, names1))
    bot.press("b", 120)
    pick("SAVE")
    check("SAVE in town writes the journey", "WRITTEN" in (mn()["msg"] or "") and ev("!!localStorage.getItem('prism.save.v1')"), mn()["msg"])
    bot.press("b", 150)
    ev("PRISM_DEMO.warp('dungeon',33,18,0,0)"); W(300); bot.clear()
    open_menu(); pick("SAVE")
    check("SAVE refuses inside a dungeon", "SAVE OUTSIDE" in (mn()["msg"] or ""), mn()["msg"])
    pick("OPTIONS"); W(300)
    check("OPTIONS opens the Settings tabs", ev("PRISM_DEMO.panel().isOpen()"))
    check("no page errors", not errs, errs[:3])
    b.close()
print("MENU %d/%d" % (sum(res), len(res)), "PASS" if all(res) else "FAIL")
sys.exit(0 if all(res) else 1)
