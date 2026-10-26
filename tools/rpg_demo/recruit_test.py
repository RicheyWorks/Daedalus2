# SPDX-License-Identifier: MIT
"""Prismheart recruits: members.json's "joins after <dungeon>" played like a player would see it (Playwright).

    python tools/rpg_demo/recruit_test.py DEMO_DIR

Checks: a new journey starts with four and no reserve; beating the Pyre Warden brings Fennick the Beastcaller in,
at the party's average level, into the reserve, and the battle says so and says how to field him; the reserve earns
half EXP from the next fight; the field menu lists five (compact rows) and STATUS pages through all five; ORDER
swaps Fennick into the front four and he fights; ORDER refuses a swap that would leave no one standing up front;
the inn heals the reserve too; the reserve is saved and comes back on CONTINUE; a save written before recruits
existed gets Fennick on CONTINUE; Brannoc (whose dungeon is not in this demo) never appears; no page errors.
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
    url = "http://127.0.0.1:%d/index.html" % srv.server_port
    pg.goto(url)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout; st = bot.st
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(5)"); ev("PRISM_DEMO.speed(6)")
    def title_pick(i):                                  # the title cursor starts on NEW GAME
        pg.wait_for_function("PRISM_DEMO.settings().loaded()", timeout=10000)
        for _ in range(i): bot.press("down", 150)
        bot.press("a", 300)
    def new_game():
        for _ in range(30):
            s = st()
            if s["mode"] == "field" and not s["dialog"]: break
            bot.press("start" if s["mode"] == "name" else "a", 150)
        W(1200); bot.clear()
    roster = lambda: ev("PRISM_DEMO.roster()")
    mn = lambda: ev("PRISM_DEMO.menu()")
    msgs = []
    def watch():
        orig = bot.st
        def wrapped():
            s = orig()
            if s.get("battle") and (not msgs or msgs[-1] != s["battle"]["msg"]): msgs.append(s["battle"]["msg"])
            return s
        return wrapped
    bot.st = watch()

    new_game()
    r = roster()
    check("a new journey: four in front, no reserve", len(r) == 4 and all(m["front"] for m in r) and st()["reserve"] == [], [m["name"] for m in r])

    # beat the Pyre Warden (its HP knocked to 1 so the test is about the recruit, not the fight)
    check("the Forge gate starts the Warden fight", bot.to_boss(0))
    ev("PRISM_DEMO.foes(1)")
    bot.fight()
    s = st(); r = roster()
    joined = [m for m in r if m["name"] == "Fennick"]
    check("the Pyre Warden falls", "PyreWarden" in s["beaten"], s["beaten"])
    check("Fennick the Beastcaller joins, into the reserve", len(joined) == 1 and not joined[0]["front"] and s["reserve"][0][0] == "Fennick", s["reserve"])
    avg = round(sum(m["lv"] for m in r[:4]) / 4)
    check("...at the party's average level", joined and joined[0]["lv"] == avg, (joined and joined[0]["lv"], avg))
    check("the battle says he joins", any("FENNICK THE BEASTCALLER JOINS YOU!" in (m or "") for m in msgs), msgs[-6:])
    check("...and how to field him", any("USE ORDER IN THE MENU" in (m or "") for m in msgs), msgs[-6:])
    bot.clear()

    # a field fight: the reserve learns by watching (half EXP)
    exp0 = {m["name"]: m["exp"] for m in roster()}; lv0 = {m["name"]: m["lv"] for m in roster()}
    ev("PRISM_DEMO.warp('town',11,10)"); W(300)
    bot.start_fight(["prism_best_gelfin"]); ev("PRISM_DEMO.foes(1)")      # one plain Gelfin: a small, fixed EXP
    msgs.clear(); bot.fight(); bot.clear()
    won = next((int(m.split()[1]) for m in msgs if m and m.startswith("VICTORY!")), None)
    r = {m["name"]: m for m in roster()}
    check("a field fight is won", won is not None, msgs[-3:])
    check("the front four earn the full EXP", won and r["Corin"]["lv"] == lv0["Corin"] and r["Corin"]["exp"] - exp0["Corin"] == won, (won, exp0["Corin"], r["Corin"]))
    check("the reserve earns half", won and r["Fennick"]["lv"] == lv0["Fennick"] and r["Fennick"]["exp"] - exp0["Fennick"] == won // 2, (won, exp0["Fennick"], r["Fennick"]))

    # the menu: five rows, STATUS pages through all five
    def open_menu(): bot.press("start", 250); return st()["mode"] == "menu"
    def pick(cmd):
        m = mn()
        while mn()["idx"] != m["cmds"].index(cmd): bot.press("down", 70)
        bot.press("a", 150)
    check("START opens the field menu", open_menu())
    pg.screenshot(path=os.path.join(DEMO, "..", "t_reserve.png"))
    pick("STATUS")
    seen = []
    for _ in range(5): seen.append(mn()["who"]); bot.press("right", 90)
    check("STATUS pages through all five, then wraps", seen == [0, 1, 2, 3, 4] and mn()["who"] == 0, seen)
    bot.press("b", 120)

    # ORDER: Fennick to the front
    pick("ORDER")
    bot.press("a", 120)                                  # Corin
    for _ in range(4): bot.press("down", 70)
    bot.press("a", 150)                                  # Fennick
    s = st()
    check("ORDER swaps Fennick into the front four", s["party"][0][0] == "Fennick" and s["reserve"][0][0] == "Corin", ([m[0] for m in s["party"]], [m[0] for m in s["reserve"]]))
    bot.press("b", 120); bot.press("b", 120); bot.clear()
    bot.start_fight(["prism_best_gelfin"])
    check("...and he fights", [m[0] for m in st()["party"]][0] == "Fennick" and st()["battle"] is not None)
    ev("PRISM_DEMO.foes(1)"); bot.fight(); bot.clear()

    # ORDER refuses to leave no one standing in front
    for i in range(4): ev("PRISM_DEMO.ko(%d)" % i)      # front four down; Corin (reserve) still standing
    open_menu(); pick("ORDER")
    bot.press("a", 120); [bot.press("down", 70) for _ in range(4)]; bot.press("a", 150)   # Fennick (down) <-> Corin (up): fine
    ok_swap = st()["party"][0][0] == "Corin"
    while mn()["ii"] != 0: bot.press("up", 70)
    bot.press("a", 120); [bot.press("down", 70) for _ in range(4)]; bot.press("a", 150)   # and back: would leave none standing
    check("ORDER: bringing a standing friend forward is allowed", ok_swap)
    check("ORDER refuses a swap that leaves no one standing in front", st()["party"][0][0] == "Corin" and mn()["msg"] == "SOMEONE STANDING MUST LEAD.", (mn()["msg"], st()["party"][0][0]))
    bot.press("b", 120); bot.press("b", 120); bot.clear()

    # the inn heals everyone, and saves the reserve
    bot.rest()
    check("the inn heals the reserve too", all(m["hp"] == m["max"] for m in roster()), [(m["name"], m["hp"], m["max"]) for m in roster()])
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); title_pick(1); W(1200); bot.clear()
    check("CONTINUE brings the reserve back", [m["name"] for m in roster()] == ["Corin", "Ysolde", "Tamsin", "Rook", "Fennick"], [m["name"] for m in roster()])

    # a save from before recruits existed: Fennick is owed and arrives
    sv = json.loads(ev("localStorage.getItem('prism.save.v1')"))
    sv["party"] = [m for m in sv["party"] + sv.pop("reserve") if m["name"] != "Fennick"][:4]
    ev("localStorage.setItem('prism.save.v1', %s)" % json.dumps(json.dumps(sv)))
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); title_pick(1); W(1200); bot.clear()
    names = [m["name"] for m in roster()]
    check("an old save (no reserve) gets Fennick on CONTINUE", names.count("Fennick") == 1 and len(names) == 5, names)
    check("Brannoc (Gearwright's Folly is not in this demo) never appears", "Brannoc" not in names)
    check("no page errors", not errs, errs)

ok = sum(res); print("RECRUITS %d/%d %s" % (ok, len(res), "PASS" if ok == len(res) else "FAIL"))
sys.exit(0 if ok == len(res) else 1)
