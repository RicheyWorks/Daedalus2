# SPDX-License-Identifier: MIT
"""Scripted play-through of the Prismheart demo built by build_demo.py (Playwright + Chromium).

    python tools/rpg_demo/play_test.py DEMO_DIR [SHOT_DIR]

Title -> town -> item shop (buy) -> magic shop (Tamsin learns Splash) -> a field battle to the end -> Cinder Forge
floor 1 chest -> the boss gate -> the Pyre Warden fought with a simple policy (heal under half, the water weakness,
attack otherwise) -> the gate falls. Fails on any page error, an unbeaten Warden, or a jukebox that never posted.
"""
import functools, http.server, json, sys, threading
from playwright.sync_api import sync_playwright
DEMO = sys.argv[1]; S = sys.argv[2] if len(sys.argv) > 2 else DEMO
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=DEMO))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d/index.html" % srv.server_port
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(viewport={"width": 1100, "height": 900})
    pg.on("console", lambda m: m.type in ("error", "warning") and errs.append(m.text))
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("PRISM_DEMO.seed(20261015)")          # repeatable rolls: the boss bot's result can't depend on luck
    st = lambda: pg.evaluate("PRISM_DEMO.state()")
    def press(k, n=1, wait=120):
        for _ in range(n):
            pg.evaluate("k=>PRISM_DEMO.press(k)", k); pg.wait_for_timeout(wait)
    pg.screenshot(path=S + "/t_title.png")
    for _ in range(40):
        if st()["mode"] == "field" and not st()["dialog"]: break
        press("start"); press("a")
    print("after title", {k: st()[k] for k in ("mode", "map", "x", "y", "cue")})
    pg.screenshot(path=S + "/t_town.png")
    # shop
    pg.evaluate("PRISM_DEMO.warp('Item',5,5)"); pg.wait_for_timeout(300)
    pg.evaluate("PRISM_DEMO.hold('up',true)"); pg.wait_for_timeout(60); pg.evaluate("PRISM_DEMO.hold('up',false)"); pg.wait_for_timeout(400)
    g0 = st()["gold"]
    for i in range(12):
        s = st(); 
        if s["mode"] == "shop": break
        press("a", wait=250)
    print("shop mode", st()["mode"], st()["dialog"])
    pg.screenshot(path=S + "/t_shop.png")
    press("a", 3, 300); 
    print("gold", g0, "->", st()["gold"], st()["bag"])
    for _ in range(8):
        if st()["mode"] == "field" and not st()["dialog"]: break
        press("b", wait=200)
    pg.evaluate("PRISM_DEMO.warp('Magic',5,5)"); pg.wait_for_timeout(300)
    pg.evaluate("PRISM_DEMO.hold('up',true)"); pg.wait_for_timeout(60); pg.evaluate("PRISM_DEMO.hold('up',false)"); pg.wait_for_timeout(400)
    for i in range(12):
        if st()["mode"] == "shop": break
        press("a", wait=250)
    press("down", 6, 150); pg.screenshot(path=S + "/t_magic.png"); press("a", wait=300)
    press("down", 3, 150); pg.screenshot(path=S + "/t_magic2.png")
    print("magic shop", st()["party"][2][6], st()["gold"])
    for _ in range(8):
        if st()["mode"] == "field" and not st()["dialog"]: break
        press("b", wait=200)
    # battle
    pg.evaluate("PRISM_DEMO.warp('world',%d,%d)" % (0, 0)); pg.wait_for_timeout(300)
    pg.evaluate("PRISM_DEMO.battle('plains')"); pg.wait_for_timeout(1500)
    pg.screenshot(path=S + "/t_battle.png")
    print("battle", st()["battle"], st()["cue"])
    for i in range(300):
        s = st()
        if s["mode"] != "battle": break
        press("a", wait=150)
    print("after battle", st()["mode"], st()["party"][:2], st()["cue"])
    D = json.load(open(DEMO + "/data.json"))
    walk = set(D["dungeon_walkable"])
    fl0 = D["dungeon"]["floors"][0]; c = fl0["chests"][0]
    for dx, dy, dn in ((0, 1, "up"), (0, -1, "down"), (1, 0, "left"), (-1, 0, "right")):
        if fl0["grid"][c["y"] + dy][c["x"] + dx] in walk: break
    pg.evaluate("PRISM_DEMO.warp('dungeon',%d,%d,0)" % (c["x"] + dx, c["y"] + dy)); pg.wait_for_timeout(400)
    pg.evaluate("PRISM_DEMO.hold('%s',true)" % dn); pg.wait_for_timeout(50); pg.evaluate("PRISM_DEMO.hold('%s',false)" % dn); pg.wait_for_timeout(300)
    g0 = st()["gold"]; press("a", wait=400)
    print("chest", st()["dialog"], g0, "->", st()["gold"], st()["cue"])
    pg.screenshot(path=S + "/t_dungeon.png")
    press("a", 3, 300)
    gate = D["dungeon"]["floors"][2]["boss"]["gate"]
    pg.evaluate("PRISM_DEMO.warp('dungeon',%d,%d,2)" % (gate["x"], gate["y"] + 1)); pg.wait_for_timeout(400)
    pg.evaluate("PRISM_DEMO.hold('up',true)"); pg.wait_for_timeout(50); pg.evaluate("PRISM_DEMO.hold('up',false)"); pg.wait_for_timeout(300)
    press("a", wait=900); print("gate ask", st()["dialog"], st()["mode"])
    pg.screenshot(path=S + "/t_gate.png")
    for _ in range(6):
        if st()["mode"] == "battle": break
        press("a", wait=700)
    pg.wait_for_timeout(800)
    pg.screenshot(path=S + "/t_boss.png")
    print("boss", st()["battle"], st()["cue"])
    CM = ["ATTACK", "MAGIC", "ITEM", "DEFEND", "RUN"]
    shot = False; plan = None
    for i in range(3000):
        s = st()
        if s["mode"] != "battle": break
        b_ = s["battle"]; lastb = b_
        if b_["phase"] == "act" and not shot and "WEAK" in (b_["msg"] or ""): pg.screenshot(path=S + "/t_boss2.png"); shot = True
        if b_["phase"] != "cmd": press("a", wait=90); plan = None; continue
        pt = s["party"]; me = pt[b_["who"]]
        if b_["sub"] is None:
            low = min((m for m in pt if m[2] > 0), key=lambda m: m[2] / m[3])
            if me[1] and me[0] == "Ysolde" and low[2] / low[3] < 0.5 and me[4] >= 5: plan = ("MAGIC", "Mend", low[0])
            elif me[0] == "Tamsin" and me[4] >= 4 and "Splash" in me[6]: plan = ("MAGIC", "Splash", None)
            elif low[2] / low[3] < 0.3 and s["bag"].get("Herb Tonic"): plan = ("ITEM", "Herb Tonic", low[0])
            else: plan = ("ATTACK", None, None)
            want = CM.index(plan[0])
            if b_["cmd"] != want: press("down", wait=60); continue
            press("a", wait=80); continue
        if b_["sub"] in ("magic", "item"):
            opts = me[6] if b_["sub"] == "magic" else None
            if opts is not None:
                want = opts.index(plan[1])
                if b_["oi"] != want: press("down", wait=60); continue
            else:
                pg.evaluate("1")  # item list order unknown to the bot: walk until the name shows in state? fall back to first item
            press("a", wait=80); continue
        if b_["sub"] == "target":
            if plan and plan[2] and plan[2] in b_["list"] and b_["list"][b_["target"]] != plan[2]: press("down", wait=60); continue
            press("a", wait=80); continue
    print("last boss state", lastb)
    print("after boss", st()["mode"], st()["bossBeaten"], st()["dialog"], [m[:4] for m in st()["party"]], st()["cue"])
    pg.screenshot(path=S + "/t_after.png")
    print("posts", st()["posts"])
    final = st()
    print("ERRORS", len(errs)); [print(" ", e) for e in errs[:20]]
    b.close()
ok = not errs and final["bossBeaten"] and final["posts"] > 50
print("PLAYTHROUGH", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
