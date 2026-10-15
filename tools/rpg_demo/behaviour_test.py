# SPDX-License-Identifier: MIT
"""Prismheart foe behaviours: every `behaviour` in foes.json does something you can see in a fight (Playwright).

    python tools/rpg_demo/behaviour_test.py DEMO_DIR

One check per behaviour, each by fighting a real foe that has it, through the menus:
simple, heavy, multi_hit, charge (telegraphed, then unleashed), pack (stronger together), caster, caster_drain,
breath_ice, erratic, steal (and the gold comes back), ambush (opens the fight), armored, undead (no sleep, light hurts,
may rise once), and the seven status_* behaviours (poison, sleep, confuse, bind, blind, burn, paralyze). Also: every
behaviour in the data is covered here; a confused hero swings on their own; a bound hero is skipped; no page errors.
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
KEY = {}
for k, v in sorted(D["foes"].items(), key=lambda kv: kv[1]["level"]):
    KEY.setdefault(v["behaviour"], k)                      # the gentlest foe with each behaviour

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(9)"); ev("PRISM_DEMO.speed(6)")
    for _ in range(30):
        s = bot.st()
        if s["mode"] == "field" and not s["dialog"]: break
        bot.press("start" if s["mode"] == "name" else "a", 150)
    W(1200); bot.clear()
    msgs = []
    orig = bot.st
    def watched():
        s = orig()
        if s.get("battle") and (not msgs or msgs[-1] != s["battle"]["msg"]): msgs.append(s["battle"]["msg"])
        return s
    bot.st = watched; st = watched
    foes = lambda: ev("PRISM_DEMO.foeStatus()")
    seen = lambda text: any(text in (m or "") for m in msgs)
    covered = set()
    def until(beh, text, plans=None, rounds=30, keys=None, before=None):
        """Fight the gentlest foe with this behaviour until `text` shows in the battle log; True if it did."""
        covered.add(beh)
        bot.rest() if any(m[2] < m[3] / 2 for m in st()["party"]) else None
        msgs.clear()
        if not bot.start_fight(keys or [KEY[beh]]): return False
        if before: before()
        for _ in range(rounds):
            if seen(text) or st()["mode"] != "battle": break
            bot.round(plans or {})
        hit = seen(text)
        if st()["mode"] == "battle": bot.finish()
        return hit

    ev("PRISM_DEMO.give('Feather of Waking', 9)"); ev("PRISM_DEMO.give('Herb Tonic', 20)")
    check("simple: a plain hit", until("simple", " HITS "))
    check("heavy: swings hard", until("heavy", "SWINGS HARD AT"))
    check("multi_hit: strikes twice", until("multi_hit", "STRIKES TWICE"))
    ok = until("charge", "UNLEASHES ITSELF ON")
    gi = next((i for i, m in enumerate(msgs) if m and "GATHERING ITSELF" in m), None); ui = next((i for i, m in enumerate(msgs) if m and "UNLEASHES" in m), None)
    check("charge: telegraphs, then unleashes", ok and gi is not None and ui is not None and gi < ui, msgs[-6:])
    covered.add("pack")
    bot.start_fight([KEY["pack"]] * 3); f3 = foes()
    bot.finish()
    bot.start_fight([KEY["pack"]]); f1 = foes()
    bot.finish()
    check("pack: three together hit harder (+15% per packmate)", f3[0]["power"] == round(f3[0]["atk"] * 1.3) and f1[0]["power"] == f1[0]["atk"], (f3[0], f1[0]))
    check("caster: an elemental bolt", until("caster", " BOLT AT "))
    check("caster_drain: the bolt feeds it", until("caster_drain", "IT DRINKS", before=lambda: ev("PRISM_DEMO.foes(10)")))
    check("breath_ice: frost on everyone", until("breath_ice", "BREATHES FROST ON EVERYONE"))
    check("erratic: sometimes flits about", until("erratic", "FLITS ABOUT"))
    g = []
    stole = until("steal", "IT SNATCHES", before=lambda: g.append(st()["gold"]))
    g0 = g[0] if g else None
    won = next((int(m.split()[4]) for m in msgs if m and m.startswith("VICTORY!")), None)
    check("steal: it snatches gold", stole, msgs[-4:])
    check("...and the gold comes back when it falls", seen("STOLEN GOLD") and won is not None and st()["gold"] == g0 + won, (g0, won, st()["gold"], msgs[-4:]))
    covered.add("ambush"); msgs.clear()
    bot.start_fight([KEY["ambush"]]); bot.round({})
    amb = D["foes"][KEY["ambush"]]["name"]
    first = next((m for m in msgs[1:] if m), "")
    check("ambush: it bursts out and acts first", seen("AMBUSH!") and amb.upper() in first.upper(), msgs[:3])
    bot.finish()
    check("armored: the shell takes most of a blow", until("armored", "THE SHELL TAKES MOST OF IT", plans={"Corin": ("ATTACK", None, 0)}))
    ev("PRISM_DEMO.teach(2,'Drowse')"); ev("PRISM_DEMO.teach(2,'Radiance')")
    check("undead: it does not sleep", until("undead", "IT DOES NOT TAKE", plans={"Tamsin": ("MAGIC", "Drowse", 0)}))
    check("undead: light finds a weak spot", until("undead", "A WEAK SPOT!", plans={"Tamsin": ("MAGIC", "Radiance", 0)}))
    rose = False
    for _ in range(10):
        if until("undead", "RISES AGAIN", plans={"Corin": ("ATTACK", None, 0), "Rook": ("ATTACK", None, 0)}, rounds=4, before=lambda: ev("PRISM_DEMO.foes(1)")): rose = True; break
    check("undead: it can rise once", rose)
    for beh, word in (("status_poison", "POISONED"), ("status_sleep", "ASLEEP"), ("status_confuse", "CONFUSED"), ("status_bind", "BOUND"),
                      ("status_blind", "BLINDED"), ("status_burn", "BURNING"), ("status_paralyze", "PARALYZED")):
        check("%s: its hits can leave someone %s" % (beh, word), until(beh, " IS %s!" % word, rounds=40))
    # a confused hero swings on their own; a bound one is skipped
    bot.rest(); bot.start_fight([KEY["simple"]])
    ev("PRISM_DEMO.inflict(3,'confuse')"); msgs.clear(); bot.round({}); bot.round({})
    check("a confused hero swings on their own", seen("Rook IS CONFUSED AND HITS"), msgs)
    ev("PRISM_DEMO.inflict(0,'bind')"); bot.round({})        # Corin may already hold the command menu this round
    ev("PRISM_DEMO.inflict(0,'bind')"); bot.round({})
    check("a bound hero is skipped by the command menu", "Corin" not in bot.choosers, bot.choosers)
    bot.finish()
    every = set(v["behaviour"] for v in D["foes"].values())
    check("every behaviour in foes.json is covered here", every <= covered, sorted(every - covered))
    check("no page errors", not errs, errs)

ok = sum(res); print("BEHAVIOURS %d/%d %s" % (ok, len(res), "PASS" if ok == len(res) else "FAIL"))
sys.exit(0 if ok == len(res) else 1)
