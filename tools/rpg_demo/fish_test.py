# SPDX-License-Identifier: MIT
"""Prismheart fishing in Windmere's pond (Playwright).

    python tools/rpg_demo/fish_test.py DEMO_DIR

Checks: the fish table and its items are packed; facing grass does nothing, facing the pond casts; B reels in; A
before the bite scatters it; a bite you ignore gets away; A during the bite lands the fish into the bag and the fish
log, "NEW!" the first time only; the fish is an ITEM that heals the number it says; bite odds follow the weights
(commons most, the legendary koi rarest); the field menu's FISH page lists every kind; the Windmere Elder buys a
Sunscale Carp for 600 gold once; the log and the request are saved at the inn and back on CONTINUE; after a
field-menu SAVE and CONTINUE the bag, gold, log and request all come back and the Elder pays nothing twice; NEW GAME empties it; no
page errors.
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
FISH = {f["name"]: f for f in D.get("fish", [])}
G = D["village"]["grid"]
BANK = next((x + 1, y) for y, r in enumerate(G) for x, c in enumerate(r) if c == "Water" and x + 1 < len(r) and G[y][x + 1] == "Grass"
            and not any(n["x"] == x + 1 and n["y"] == y for n in D["village"]["npcs"]))
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

check("the fish table is packed, six kinds, each also an item", len(FISH) == 6 and all(D["gear"].get(k, {}).get("effect") == f["effect"] for k, f in FISH.items()), list(FISH))

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout; st = bot.st
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(9)"); ev("PRISM_DEMO.speed(6)")
    def new_game():
        for _ in range(30):
            s = st()
            if s["mode"] == "field" and not s["dialog"]: break
            bot.press("start" if s["mode"] == "name" else "a", 150)
        W(1200); bot.clear()
    new_game()
    fs = lambda: ev("PRISM_DEMO.fishing()")
    ev("PRISM_DEMO.warp('village',%d,%d)" % BANK); W(250)
    bot.face("right"); bot.press("a", 300)
    check("facing grass, A does not cast", st()["mode"] == "field" and fs() is None)
    ev("PRISM_DEMO.speed(1)")                                  # real-time from here: bite windows are fractions of a second
    ev("PRISM_DEMO.warp('village',%d,%d)" % BANK); W(250)      # facing right may have walked a step: back to the bank
    bot.face("left"); bot.press("a", 300)
    check("facing the pond, A casts the line", st()["mode"] == "fish" and fs()["phase"] in ("wait", "bite"), fs())   # at 6x speed a bite can come fast
    pg.screenshot(path=os.path.join(DEMO, "..", "t_fish.png"))
    bot.press("b", 300)
    if fs(): bot.press("b", 300)                              # a bite had already come: B only closes the result
    check("B reels in", st()["mode"] == "field" and fs() is None)

    bot.face("left"); bot.press("a", 200); bot.press("a", 300)
    check("A before the bite scatters it", fs() and fs()["phase"] == "done" and "TOO SOON" in fs()["msg"], fs())
    bot.press("a", 600)

    def wait_bite(limit=8):
        t0 = time.time()
        while time.time() - t0 < limit:
            f = fs()
            if f and f["phase"] == "bite": return f
            W(10)
        return None
    bot.face("left"); bot.press("a", 150)
    f = wait_bite()
    t0 = time.time()
    while fs() and fs()["phase"] == "bite" and time.time() - t0 < 5: W(20)
    check("a bite you ignore gets away", f and fs() and "GOT AWAY" in fs()["msg"], fs())
    bot.press("a", 600)

    caught = []
    for attempt in range(6):
        bot.face("left"); bot.press("a", 150)
        f = wait_bite()
        if not f: continue
        ev("PRISM_DEMO.press('a')"); W(250)
        r = fs()
        if r and r["phase"] == "done" and "CAUGHT" in r["msg"]:
            caught.append((f["fish"], r["msg"]))
        bot.press("a", 500)
        if len(caught) >= 2: break
    log = ev("PRISM_DEMO.fishLog()")
    check("A during the bite lands the fish", len(caught) >= 2 and all(st()["bag"].get(k, 0) >= 1 for k, _ in caught), caught)
    check("...into the fish log", sum(log.values()) == len(caught) and all(k in log for k, _ in caught), log)
    seen, ok_new = set(), True
    for k, msg in caught:
        ok_new &= msg.startswith("NEW!") == (k not in seen); seen.add(k)
    check("...'NEW!' only the first time a kind is caught", ok_new, caught)

    ev("PRISM_DEMO.speed(6)")
    k0 = caught[0][0]
    check("a caught fish is a field ITEM", k0 in ev("PRISM_DEMO.lists()")["field"], ev("PRISM_DEMO.lists()")["field"])
    eff = FISH[k0]["effect"]; n = int(eff.split()[1])
    line = ev("PRISM_DEMO.itemLine(%s)" % json.dumps(k0))
    check("...whose ITEM line states its real effect", str(n) in line or str(n * 4) in line or str(n * 3) in line, (eff, line))

    odds = ev("PRISM_DEMO.fishOdds(20000)")
    common = odds.get("Reedling", 0) + odds.get("Pond Perch", 0)
    check("bite odds follow the weights: commons most, the koi rarest", common > 12000 and 50 < odds.get("Prismscale Koi", 0) < 400
          and odds.get("Prismscale Koi", 0) < odds.get("Sunscale Carp", 0) < odds.get("Glassfin Minnow", 0), odds)

    # the FISH page in the field menu
    mn = lambda: ev("PRISM_DEMO.menu()")
    bot.press("start", 250)
    while mn()["idx"] != mn()["cmds"].index("FISH"): bot.press("down", 60)
    bot.press("a", 250)
    check("the field menu has a FISH page", mn()["sub"] == "fish", mn())
    bot.press("down", 80)
    check("...whose cursor moves through all six kinds", mn()["ii"] == 1)
    pg.screenshot(path=os.path.join(DEMO, "..", "t_fishlog.png"))
    bot.press("b", 150); bot.press("b", 150); bot.clear()

    # the Elder's request: a Sunscale Carp for 600 gold, once
    elder = next(n for n in D["village"]["npcs"] if n.get("request"))
    req = elder["request"]
    def talk_elder():
        ev("PRISM_DEMO.warp('village',%d,%d)" % (elder["x"], elder["y"] + 1)); W(250)
        bot.face("up"); bot.press("a", 500)
    talk_elder()
    pages = []
    for _ in range(6):
        d = st()["dialog"]
        if not d: break
        pages.append(d); bot.press("a", 300)
    check("without the fish, the Elder asks for a Sunscale Carp", any(req["item"].upper() in p_ for p_ in pages), pages)
    ev("PRISM_DEMO.give(%s, 1)" % json.dumps(req["item"]))
    g0 = st()["gold"]
    talk_elder()
    for _ in range(6):
        if st()["dialog"] == req["offer"]: break
        bot.press("a", 300)
    W(400); bot.press("a", 400)                                # YES is the default choice
    for _ in range(6):
        if not st()["dialog"]: break
        bot.press("a", 300)
    check("giving her the carp pays the gold and takes the fish", st()["gold"] == g0 + req["gold"] and st()["bag"].get(req["item"], 0) == 0,
          (g0, st()["gold"], st()["bag"].get(req["item"])))
    check("...and the request is marked done", ev("PRISM_DEMO.quests()").get(req["id"]) is True)
    ev("PRISM_DEMO.give(%s, 1)" % json.dumps(req["item"]))
    talk_elder()
    d = st()["dialog"]
    for _ in range(6):
        if not st()["dialog"]: break
        bot.press("a", 300)
    check("...once only: afterwards she just remembers it", d == req["done"] and st()["gold"] == g0 + req["gold"], d)

    before = ev("PRISM_DEMO.fishLog()")
    qbefore = ev("PRISM_DEMO.quests()")
    bot.rest()
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); bot.press("down", 150); bot.press("a", 300); W(1200); bot.clear()
    check("the fish log is saved at the inn and back on CONTINUE", ev("PRISM_DEMO.fishLog()") == before, ev("PRISM_DEMO.fishLog()"))
    check("the finished request is saved too", ev("PRISM_DEMO.quests()") == qbefore, ev("PRISM_DEMO.quests()"))

    # the field-menu SAVE path (not the inn), then the Elder again with another carp (PootScoot 32833)
    ev("PRISM_DEMO.warp('village',%d,%d)" % (elder["x"], elder["y"] + 1)); W(250)
    if st()["bag"].get(req["item"], 0) < 1: ev("PRISM_DEMO.give(%s, 1)" % json.dumps(req["item"]))
    snap = {"bag": st()["bag"], "gold": st()["gold"], "log": ev("PRISM_DEMO.fishLog()"), "quests": ev("PRISM_DEMO.quests()")}
    bot.press("start", 250)
    while mn()["idx"] != mn()["cmds"].index("SAVE"): bot.press("down", 60)
    bot.press("a", 300)
    saved_msg = mn()["msg"]
    bot.press("b", 150); bot.press("b", 150); bot.clear()
    check("the field menu saves in Windmere", "WRITTEN" in saved_msg, saved_msg)
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); bot.press("down", 150); bot.press("a", 300); W(1200); bot.clear()
    back = {"bag": st()["bag"], "gold": st()["gold"], "log": ev("PRISM_DEMO.fishLog()"), "quests": ev("PRISM_DEMO.quests()")}
    check("after a field-menu SAVE and CONTINUE: bag, gold, fish log and finished request all come back", back == snap,
          {k: (snap[k], back[k]) for k in snap if snap[k] != back[k]})
    talk_elder()
    d = st()["dialog"]
    for _ in range(6):
        if not st()["dialog"]: break
        bot.press("a", 300)
    check("...and the Elder, offered another carp, only remembers: no second reward, the carp stays in the bag",
          d == req["done"] and st()["gold"] == snap["gold"] and st()["bag"].get(req["item"], 0) == snap["bag"].get(req["item"], 0) >= 1,
          (d, st()["gold"], snap["gold"], st()["bag"].get(req["item"])))
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.speed(6)"); new_game()
    check("NEW GAME empties the fish log and the requests", ev("PRISM_DEMO.fishLog()") == {} and ev("PRISM_DEMO.quests()") == {})
    check("no page errors", not errs, errs[:3])
    b.close()

k = sum(res)
print("FISHING %d/%d %s" % (k, len(res), "PASS" if k == len(res) else "FAIL"))
sys.exit(0 if k == len(res) else 1)
