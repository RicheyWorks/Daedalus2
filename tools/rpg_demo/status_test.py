# SPDX-License-Identifier: MIT
"""Prismheart battle statuses (spells.json's status field, foes' status_* behaviours), played by the menus (Playwright).

    python tools/rpg_demo/status_test.py DEMO_DIR

Checks: Drowse puts a field foe to sleep and does no damage; a sleeping foe loses its turn; a blow wakes it; a Warden
does not sleep; Lull slows; Blight poisons a foe and poison bites it at the end of the round; Ward and Quicken land on
an ally and show a tag; Siphon heals its caster; a sleeping hero is skipped by the command menu and a Wake Bell wakes
them; poison never takes the party below 1 HP in battle; poison outlasts the battle, every other status ends with
it; poison nips on the field every 4 steps (never below 1 HP); an Antidote Leaf from the field menu cures it; the inn
cures it too; a Drinkbloom (status_poison) can poison the party; no page errors.
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
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(3)"); ev("PRISM_DEMO.speed(6)")
    for _ in range(30):
        s = st()
        if s["mode"] == "field" and not s["dialog"]: break
        bot.press("start" if s["mode"] == "name" else "a", 150)
    W(1200); bot.clear()
    roster = lambda: {m["name"]: m for m in ev("PRISM_DEMO.roster()")}
    foes = lambda: ev("PRISM_DEMO.foeStatus()")
    msgs = []
    orig = bot.st
    def watched():
        s = orig()
        if s.get("battle") and (not msgs or msgs[-1] != s["battle"]["msg"]): msgs.append(s["battle"]["msg"])
        return s
    bot.st = watched; st = watched
    fight = bot.start_fight; finish = bot.finish
    for sp in ("Drowse", "Lull", "Blight", "Siphon"): ev("PRISM_DEMO.teach(2,'%s')" % sp)
    for sp in ("Quicken",): ev("PRISM_DEMO.teach(1,'%s')" % sp)

    # --- sleep on a foe
    check("a fight with a Gloomspore starts", fight(["prism_best_gloomspore"]))
    hp0 = foes()[0]["hp"]
    for _ in range(6):
        bot.round({"Tamsin": ("MAGIC", "Drowse", 0)})
        if "sleep" in foes()[0]["status"]: break
    check("Drowse puts the foe to sleep", "sleep" in foes()[0]["status"], (foes(), msgs[-4:]))
    check("...and does no damage", foes()[0]["hp"] == hp0, (hp0, foes()[0]["hp"]))
    pg.screenshot(path=os.path.join(DEMO, "..", "t_status.png"))
    msgs.clear(); bot.round({})
    check("a sleeping foe loses its turn", any("IS ASLEEP" in (m or "") for m in msgs), msgs)
    bot.round({"Corin": ("ATTACK", None, 0)})
    check("a blow wakes it", "sleep" not in foes()[0]["status"] or foes()[0]["hp"] == 0, foes())
    # Lull, Blight
    for _ in range(6):
        bot.round({"Tamsin": ("MAGIC", "Lull", 0)})
        if "slow" in foes()[0]["status"]: break
    check("Lull slows the foe", "slow" in foes()[0]["status"], foes())
    for _ in range(6):
        hp1 = foes()[0]["hp"]
        bot.round({"Tamsin": ("MAGIC", "Blight", 0)})
        if "poison" in foes()[0]["status"]: break
    check("Blight poisons the foe", "poison" in foes()[0]["status"], foes())
    hp1 = foes()[0]["hp"]; bot.round({})
    check("poison bites the foe at the end of the round", foes()[0]["hp"] < hp1, (hp1, foes()[0]["hp"]))
    finish()
    # ally statuses and drain, against a sturdy Star Shell
    check("a fight with a Star Shell starts", fight(["prism_best_star_shell"]))
    ev("PRISM_DEMO.hurt(2, 60)"); t0 = roster()["Tamsin"]["hp"]
    bot.round({"Ysolde": ("MAGIC", "Ward", "Corin"), "Rook": ("DEFEND", None, None), "Tamsin": ("MAGIC", "Siphon", 0)})
    check("Ward lands on Corin", "protect" in roster()["Corin"]["status"], roster()["Corin"])
    check("Siphon heals its caster", roster()["Tamsin"]["hp"] > t0, (t0, roster()["Tamsin"]["hp"], msgs[-6:]))
    bot.round({"Ysolde": ("MAGIC", "Quicken", "Rook")})
    check("Quicken lands on Rook", "haste" in roster()["Rook"]["status"], roster()["Rook"])
    # a sleeping hero: skipped, then woken by a Wake Bell
    ev("PRISM_DEMO.give('Wake Bell')"); ev("PRISM_DEMO.inflict(1,'sleep')")
    bot.round({})                                                  # Ysolde may already be choosing this round
    ev("PRISM_DEMO.inflict(1,'sleep')"); bot.round({})
    check("a sleeping Ysolde is skipped by the command menu", "Ysolde" not in bot.choosers, bot.choosers)
    ev("PRISM_DEMO.inflict(1,'sleep')"); msgs.clear()
    bot.round({"Corin": ("ITEM", "Wake Bell", "Ysolde")})
    check("a Wake Bell wakes Ysolde", "sleep" not in roster()["Ysolde"]["status"] and any("WAKE BELL ON YSOLDE" in (m or "").upper() for m in msgs), msgs[-6:])
    # poison in battle never takes a hero below 1
    ev("PRISM_DEMO.inflict(3,'poison')"); ev("PRISM_DEMO.hurt(3, 9999)")
    bot.round({})
    check("battle poison leaves Rook at 1 HP, not 0", roster()["Rook"]["hp"] >= 1 or "IS DOWN" in " ".join(m or "" for m in msgs[-6:]), roster()["Rook"])
    finish()
    r = roster()
    check("after the battle: poison stays", "poison" in r["Rook"]["status"], r["Rook"])
    check("...every other status ends with it", not any(k in m["status"] for m in r.values() for k in ("protect", "haste", "sleep", "slow")), {k: v["status"] for k, v in r.items()})

    # --- field poison and the cures
    ev("PRISM_DEMO.inflict(0,'poison')"); c0 = roster()["Corin"]["hp"]
    ev("PRISM_DEMO.warp('town',11,10)"); W(300)                # town streets: no encounters to muddy the count
    for i in range(8):
        d = "down" if i % 2 == 0 else "up"
        ev("PRISM_DEMO.hold('%s',true)" % d); W(260); ev("PRISM_DEMO.hold('%s',false)" % d); W(120)
        if st()["mode"] == "battle": finish()
    check("field poison nips Corin as he walks", roster()["Corin"]["hp"] < c0, (c0, roster()["Corin"]["hp"]))
    ev("PRISM_DEMO.hurt(0, 99999)")
    for i in range(8):
        d = "down" if i % 2 == 0 else "up"
        ev("PRISM_DEMO.hold('%s',true)" % d); W(260); ev("PRISM_DEMO.hold('%s',false)" % d); W(120)
        if st()["mode"] == "battle": finish()
    check("...but never below 1 HP", roster()["Corin"]["hp"] == 1, roster()["Corin"])
    ev("PRISM_DEMO.warp('town',11,10)"); W(250)
    ev("PRISM_DEMO.give('Antidote Leaf')")
    bot.press("start", 250)
    mn = lambda: ev("PRISM_DEMO.menu()")
    while mn()["idx"] != 0: bot.press("up", 60)
    bot.press("a", 150)                                          # ITEM
    items = ev("PRISM_DEMO.lists()")["field"]
    for _ in range(items.index("Antidote Leaf")): bot.press("down", 60)
    bot.press("a", 200)                                          # on Corin (who = 0)
    check("an Antidote Leaf from the field menu cures Corin", "poison" not in roster()["Corin"]["status"], (roster()["Corin"], mn()["msg"]))
    bot.press("b", 120); bot.press("b", 120); bot.clear()
    check("Rook is still poisoned", "poison" in roster()["Rook"]["status"])
    bot.rest()
    check("the inn cures poison", not any("poison" in m["status"] for m in roster().values()), {k: v["status"] for k, v in roster().items()})

    # --- a status_poison foe can poison the party
    check("a fight with a Drinkbloom starts", fight(["prism_best_drinkbloom"]))
    poisoned = False
    for _ in range(25):
        bot.round({})
        if any("poison" in m["status"] for m in roster().values()): poisoned = True; break
        if st()["mode"] != "battle": break
    check("the Drinkbloom's bite poisons someone", poisoned, [m for m in msgs if m and "POISON" in m][-2:])
    if st()["mode"] == "battle": finish()

    # --- a Warden does not sleep
    ev("PRISM_DEMO.warp('town',11,10)"); W(250)
    ev("PRISM_DEMO.battle('cave', true)"); W(600)
    for _ in range(40):
        s = st()
        if s["mode"] == "battle" and s["battle"]["phase"] == "cmd": break
        W(100)
    msgs.clear(); bot.round({"Tamsin": ("MAGIC", "Drowse", 0)})
    check("a Warden does not sleep", "sleep" not in foes()[0]["status"] and any("A WARDEN DOES NOT SLEEP" in (m or "") for m in msgs), msgs)
    check("no page errors", not errs, errs)

ok = sum(res); print("STATUS %d/%d %s" % (ok, len(res), "PASS" if ok == len(res) else "FAIL"))
sys.exit(0 if ok == len(res) else 1)
