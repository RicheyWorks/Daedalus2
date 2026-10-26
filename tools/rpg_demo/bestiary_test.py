# SPDX-License-Identifier: MIT
"""Prismheart bestiary: every foe you meet is written down, with what its behaviour means (Playwright, by the menus).

    python tools/rpg_demo/bestiary_test.py DEMO_DIR

Checks: every behaviour in foes.json (and the Wardens) has bestiary words; a new journey has met nothing; the field
menu has BESTIARY and it opens on "NOTHING MET YET"; a fight records the foe as met, a win as felled; three Ash
Hounds count as three met and three felled; a Warden goes in by name with its weakness; entries list by level; the
cursor moves through them; the bestiary is saved at the inn and back on CONTINUE; NEW GAME starts it empty; no page
errors.
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
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(6)"); ev("PRISM_DEMO.speed(6)")
    def new_game():
        for _ in range(30):
            s = st()
            if s["mode"] == "field" and not s["dialog"]: break
            bot.press("start" if s["mode"] == "name" else "a", 150)
        W(1200); bot.clear()
    new_game()
    beasts = lambda: {e["key"]: e for e in ev("PRISM_DEMO.bestiary()")}
    mn = lambda: ev("PRISM_DEMO.menu()")

    words = ev("PRISM_DEMO.behaviourText()")
    every = set(v["behaviour"] for v in D["foes"].values())
    check("every behaviour (and the Wardens) has bestiary words", every <= set(words) and "warden" in words, sorted(every - set(words)))
    check("a new journey has met nothing", beasts() == {})
    bot.press("start", 250)
    check("the field menu has BESTIARY", "BESTIARY" in mn()["cmds"], mn()["cmds"])
    while mn()["idx"] != mn()["cmds"].index("BESTIARY"): bot.press("down", 60)
    bot.press("a", 200)
    check("BESTIARY opens (nothing met yet)", mn()["sub"] == "bestiary")
    bot.press("b", 150); bot.press("b", 150); bot.clear()

    bot.start_fight(["prism_best_gelfin"])
    check("a fight records the foe as met", beasts().get("prism_best_gelfin", {}).get("seen") == 1, beasts())
    bot.finish()
    g = beasts().get("prism_best_gelfin", {})
    check("...and a win as felled", g.get("felled") == 1, g)
    check("...with its stats and behaviour words from the data", g.get("hp") == D["foes"]["prism_best_gelfin"]["hp"] and g.get("text") == words[D["foes"]["prism_best_gelfin"]["behaviour"]], g)
    bot.start_fight(["prism_best_ash_hound"] * 3); bot.finish()
    h = beasts().get("prism_best_ash_hound", {})
    check("three Ash Hounds: three met, three felled", h.get("seen") == 3 and h.get("felled") == 3, h)
    bot.to_boss(0); bot.finish()
    w = beasts().get("warden:PyreWarden", {})
    check("a Warden goes in by name, with its weakness", w.get("name", "").upper() == "PYRE WARDEN" and w.get("weak") not in (None, "none") and w.get("felled") == 1, w)
    lv = [e["lv"] for e in ev("PRISM_DEMO.bestiary()")]
    check("entries list by level", lv == sorted(lv), lv)

    bot.press("start", 250)
    while mn()["idx"] != mn()["cmds"].index("BESTIARY"): bot.press("down", 60)
    bot.press("a", 200)
    bot.press("down", 80); bot.press("down", 80)
    check("the cursor moves through the entries", mn()["ii"] == 2, mn())
    pg.screenshot(path=os.path.join(DEMO, "..", "t_bestiary.png"))
    bot.press("b", 150); bot.press("b", 150); bot.clear()

    before = beasts()
    bot.rest()
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); bot.press("down", 150); bot.press("a", 300); W(1200); bot.clear()
    after = beasts()
    check("the bestiary is saved at the inn and back on CONTINUE", after == before and len(after) == 3, (len(before), len(after)))
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); new_game()
    check("NEW GAME starts the bestiary empty", beasts() == {})
    check("no page errors", not errs, errs)

ok = sum(res); print("BESTIARY %d/%d %s" % (ok, len(res), "PASS" if ok == len(res) else "FAIL"))
sys.exit(0 if ok == len(res) else 1)
