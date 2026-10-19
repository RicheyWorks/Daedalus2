# SPDX-License-Identifier: MIT
"""Prismheart PRISM03 summon spirits (tools/rpg_demo/summons.js), played by the menus (Playwright).

    python tools/rpg_demo/summons_test.py DEMO_DIR

Checks: the demo's Wardens give exactly their "<Spirit> summon" drops as spirits; every spirit chord is three soft
notes from the low D pentatonic bells (146.832-349.227 Hz, gain <= 0.3, rolled 110 ms) and the shards' chords
differ; weak spot x2 and same element x0.5; no SUMMON command before a Warden falls; after PyreWarden falls the
command appears, Emberforge Titan strikes every foe, costs its MP and is marked used; a second call in the same
battle is refused with no MP spent; not enough MP is refused; a new battle lets the spirit answer again; beating
a Warden in battle announces its spirit; ATTACK/MAGIC/ITEM/DEFEND/RUN keep their places; no page errors.
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
BELLS = {146.832, 174.614, 195.997, 219.999, 261.625, 293.664, 349.227}
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout; st = bot.st
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(5)"); ev("PRISM_DEMO.speed(6)")
    for _ in range(30):
        s = st()
        if s["mode"] == "field" and not s["dialog"]: break
        bot.press("start" if s["mode"] == "name" else "a", 150)
    W(1200); bot.clear()

    # --- rules (summons.js on its own)
    want = [d["boss_data"]["drops"][1].replace(" summon", "") for d in D["dungeons"] if any(x.endswith(" summon") for x in d["boss_data"]["drops"])]
    sm = ev("PRISM_DEMO.summons()")
    names = [s["name"] for s in sm["all"]]
    check("spirits come from the Wardens' summon drops", names == want and len(names) >= 3, names)
    chords = [tuple(n["hz"] for n in s["chord"]) for s in sm["all"]]
    soft = all(len(c) == 3 and set(c) <= BELLS for c in chords) and all(n["gain"] <= 0.3 and n["at_ms"] == i * 110 for s in sm["all"] for i, n in enumerate(s["chord"]))
    check("every chord is three soft low pentatonic bells", soft, chords)
    check("each shard's chord is its own", len(set(chords)) == len(chords), chords)
    rz = ev("""(() => { const s = PrismSummons.table(%s)[0];
        return [PrismSummons.resist(s, { weak: 'fire' }), PrismSummons.resist(s, { el: 'fire' }), PrismSummons.resist(s, { el: 'air' }),
                PrismSummons.damage(s, { def: 0 }, { int: 0 }, 1), PrismSummons.damage(s, { weak: 'fire', def: 0 }, { int: 0 }, 1)]; })()""" % json.dumps([D["dungeons"][0]["boss_data"]]))
    check("weak spot x2, same element x0.5, damage doubles on a weak spot", rz[:3] == [2, 0.5, 1] and abs(rz[4] - 2 * rz[3]) <= 1, rz)

    guard = ev("""[PrismSummons.realmAllowed('Prismheart'), PrismSummons.realmAllowed('prism'), PrismSummons.realmAllowed(undefined),
        PrismSummons.realmAllowed('Portal'), PrismSummons.table(%s, 'Portal').length, PrismSummons.table(%s, 'Prismheart').length]""" % (json.dumps([D["dungeons"][0]["boss_data"]]), json.dumps([D["dungeons"][0]["boss_data"]])))
    check("realm guard: Prism builds get spirits, Portal and other realms get none", guard == [True, True, True, False, 0, 1], guard)

    # --- before any Warden falls
    check("a fight with a Gloomspore starts", bot.start_fight(["prism_best_gloomspore"]))
    check("no SUMMON before a Warden falls", ev("PRISM_DEMO.summons()")["cmds"] == ["ATTACK", "MAGIC", "ITEM", "DEFEND", "RUN"])
    bot.finish(); W(600); bot.clear()

    # --- after PyreWarden
    first = D["dungeons"][0]["boss_data"]["name"]; spirit = sm["all"][0]
    ev("PRISM_DEMO.beat('%s')" % first)
    check("the first fight after a Warden falls starts", bot.start_fight(["prism_best_gloomspore", "prism_best_gloomspore"]))
    s = ev("PRISM_DEMO.summons()")
    check("SUMMON appears last, other commands keep their places", s["cmds"] == ["ATTACK", "MAGIC", "ITEM", "DEFEND", "RUN", "SUMMON"] and s["unlocked"] == [spirit["name"]], s["cmds"])
    tam = lambda: next(m for m in ev("PRISM_DEMO.roster()") if m["name"] == "Tamsin")
    mp0 = tam()["mp"]; hp0 = [f["hp"] for f in ev("PRISM_DEMO.foeStatus()")]
    after = bot.round({"Tamsin": ("SUMMON", spirit["name"], None)})
    hp1 = [f["hp"] for f in ev("PRISM_DEMO.foeStatus()")]
    s = ev("PRISM_DEMO.summons()")
    check("the spirit strikes every foe", all(a < b for a, b in zip(hp1, hp0)), (hp0, hp1))
    check("...costs its MP and is marked used", tam()["mp"] == mp0 - spirit["mp"] and s["used"] == [spirit["name"]], (mp0, tam()["mp"], s["used"]))
    ev("PRISM_DEMO.foes(9999)")
    mp1 = tam()["mp"]
    bot.round({"Tamsin": ("SUMMON", spirit["name"], None)}, limit=80)
    W(300)
    check("a second call in the same battle is refused, no MP spent", tam()["mp"] == mp1 and ev("PRISM_DEMO.summons()")["used"] == [spirit["name"]], (mp1, tam()["mp"]))
    bot.press("b", 120)                                   # back out of the spirit list
    bot.finish(); W(600); bot.clear()

    check("a new battle starts", bot.start_fight(["prism_best_gloomspore"]))
    check("...and the spirit may answer again", ev("PRISM_DEMO.summons()")["used"] == [])
    ev("PRISM_DEMO.spend(2, 999)")
    bot.round({"Tamsin": ("SUMMON", spirit["name"], None)}, limit=80)
    check("not enough MP: the spirit does not answer", ev("PRISM_DEMO.summons()")["used"] == [], ev("PRISM_DEMO.summons()")["used"])
    bot.press("b", 120)
    bot.finish(); W(600); bot.clear()

    # --- winning a Warden fight announces its spirit
    second = D["dungeons"][1]["boss_data"]["name"]; sp2 = sm["all"][1]["name"]
    seen = []
    ev("PRISM_DEMO.warp('town',11,10)"); W(250); ev("PRISM_DEMO.battle('plains', %s, null)" % json.dumps(D["dungeons"][1]["boss_data"])); W(500)
    ev("PRISM_DEMO.foes(1)")
    for _ in range(200):
        s = st()
        if s["mode"] != "battle": break
        if s["battle"]["msg"] and (not seen or seen[-1] != s["battle"]["msg"]): seen.append(s["battle"]["msg"])
        if s["battle"]["phase"] == "cmd": bot.round({}, default=("ATTACK", None, 0)); continue
        bot.press("a", 120)
    check("beating a Warden announces its spirit", any(sp2.upper() + " WILL ANSWER A SUMMON" in m for m in seen), seen[-4:])
    check("...and it joins the summons", sp2 in ev("PRISM_DEMO.summons()")["unlocked"])
    check("no page errors", not errs, errs[:3])
    b.close()
print("summons: %d/%d" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
