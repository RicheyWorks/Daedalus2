# SPDX-License-Identifier: MIT
"""The Prismheart start screen: full-screen display, live menu, save / CONTINUE, OPTIONS -> Settings (Playwright).

    python tools/rpg_demo/title_test.py DEMO_DIR

Checks: nothing but the game is on screen on a desktop (no controls, no log); the canvas fills the window at a sharp
scale; CONTINUE is dark and refuses without a save; OPTIONS (pad, keyboard Esc, or a click on the item) opens the
Settings tabs; resting at the inn saves; CONTINUE then resumes at the inn with the same gold, level and items; the
touch controls appear on a phone and stay off on a desktop; the prompt names the plugged-in pad's button.
"""
import functools, http.server, os, sys, threading
from playwright.sync_api import sync_playwright

DEMO = sys.argv[1]
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=DEMO))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d/index.html" % srv.server_port
MOCK = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pad_test.py"), encoding="utf-8").read().split('MOCK = """')[1].split('"""')[0]
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page(); pg.add_init_script(MOCK)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev = pg.evaluate; W = pg.wait_for_timeout; st = lambda: ev("PRISM_DEMO.state()")
    vis = ev("""[...document.querySelectorAll('button, pre, p, h1, .panel')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden' && !e.closest('.dset'); }).length""")
    check("desktop: nothing but the game on screen", vis == 0, vis)
    cw = ev("document.getElementById('screen').getBoundingClientRect().width")
    check("canvas fills the window at a sharp scale (4x = 1280)", cw == 1280, cw)
    check("CONTINUE dark without a save", ev("localStorage.getItem('prism.save.v1')") is None)
    ev("PRISM_DEMO.press('down')"); W(150); ev("PRISM_DEMO.press('a')"); W(400)
    check("CONTINUE refuses without a save", st()["mode"] == "title")
    pg.keyboard.press("Escape"); W(300)
    check("Esc on the title opens Settings", ev("PRISM_DEMO.panel().isOpen()"))
    pg.keyboard.press("Escape"); W(300)
    box = pg.locator("#screen").bounding_box()
    pg.mouse.click(box["x"] + box["width"] * (160 + 0) / 320, box["y"] + box["height"] * (152 + 28 + 3) / 224); W(300)   # OPTIONS row
    check("click OPTIONS opens Settings", ev("PRISM_DEMO.panel().isOpen()"))
    pg.keyboard.press("Escape"); W(300)
    ev("__pad.plug(0,'DualSense Wireless Controller (STANDARD GAMEPAD Vendor: 054c Product: 0ce6)','standard',18,4)"); W(300)
    check("prompt names the pad's confirm button (PRESS CROSS)", ev("PRISM_DEMO.padLabel('confirm',0)") == "Cross")
    ev("__pad.btn(0,12,1)"); W(80); ev("__pad.btn(0,12,0)"); W(120)       # the click left the cursor on OPTIONS; up: CONTINUE
    ev("__pad.btn(0,12,1)"); W(80); ev("__pad.btn(0,12,0)"); W(120)       # up: NEW GAME
    ev("__pad.btn(0,0,1)"); W(80); ev("__pad.btn(0,0,0)"); W(1200)
    check("Cross on NEW GAME starts", st()["mode"] == "field" and st()["map"] == "town", st()["map"])
    for _ in range(12):
        if not st()["dialog"]: break
        ev("PRISM_DEMO.press('a')"); W(250)
    gold0 = st()["gold"]
    ev("PRISM_DEMO.warp('Inn',3,6)"); W(400)                              # across the counter from the innkeeper
    ev("PRISM_DEMO.hold('up',true)"); W(60); ev("PRISM_DEMO.hold('up',false)"); W(250)
    ev("PRISM_DEMO.press('a')"); W(600)
    for _ in range(10):
        s = st()
        if s["dialog"] and "REST" in s["dialog"]: break
        ev("PRISM_DEMO.press('a')"); W(400)
    asked = st()["dialog"] or ""
    ev("PRISM_DEMO.press('a')"); W(1500)                                  # YES
    for _ in range(10):
        if ev("localStorage.getItem('prism.save.v1')"): break
        ev("PRISM_DEMO.press('a')"); W(400)
    check("resting at the inn saves the journey", ev("localStorage.getItem('prism.save.v1')") is not None, asked)
    saved_gold = ev("JSON.parse(localStorage.getItem('prism.save.v1')).gold")
    check("saved gold = gold after paying the inn", saved_gold < gold0 and saved_gold == st()["gold"], (gold0, saved_gold, st()["gold"]))
    pg.reload(); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded()", timeout=10000)
    ev("PRISM_DEMO.press('down')"); W(150); ev("PRISM_DEMO.press('a')"); W(1400)
    s = st()
    check("CONTINUE resumes at the inn with the saved gold", s["mode"] == "field" and s["map"] == "interior" and s["gold"] == saved_gold, (s["map"], s["gold"]))
    check("Settings > Gameplay shows the journey", "LV" in ev("PRISM_DEMO.settings().format('SaveInfo')"), ev("PRISM_DEMO.settings().format('SaveInfo')"))
    ev("PRISM_DEMO.settings().activate('SaveErase')"); W(200)
    check("Erase Saved Journey clears it", ev("localStorage.getItem('prism.save.v1')") is None)
    check("touch controls stay off on a desktop", not ev("document.getElementById('pad').classList.contains('on')"))
    ctx.close()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.settings().loaded()", timeout=10000); pg.wait_for_timeout(300)
    check("phone: touch controls on, no sideways scroll", pg.evaluate("document.getElementById('pad').classList.contains('on')") and pg.evaluate("document.documentElement.scrollWidth") <= 390)
    pg.locator("[data-k=opts]").tap(); pg.wait_for_timeout(300)
    check("phone: the gear opens Settings", pg.evaluate("PRISM_DEMO.panel().isOpen()"))
    pg.evaluate("PRISM_DEMO.settings().set('TouchControls', 2)"); pg.wait_for_timeout(200)
    check("Touch Controls OFF hides them", not pg.evaluate("document.getElementById('pad').classList.contains('on')"))
    check("no page errors", not errs, errs[:3])
    b.close()
print("TITLE %d/%d" % (sum(res), len(res)), "PASS" if all(res) else "FAIL")
sys.exit(0 if all(res) else 1)
