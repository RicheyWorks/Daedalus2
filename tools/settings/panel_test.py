# SPDX-License-Identifier: MIT
"""The Halo Infinite-style settings panel, driven by a simulated pad, the keyboard and touch (Playwright).

    python tools/settings/panel_test.py DEMO_DIR      (a folder built by tools/rpg_demo/build_demo.py)

Opens the panel from the pad's View button, walks the tabs with RB / LB, changes Audio rows and checks the jukebox
chain's gains follow, resets a tab with Y, flips Menu Confirm Button with A and checks the pad's prompts follow,
drags a slider by touch, switches Text Size, closes with B, and checks the panel fits a phone screen.
"""
import functools, http.server, os, sys, threading
from playwright.sync_api import sync_playwright

DEMO = sys.argv[1]
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=DEMO))
threading.Thread(target=srv.serve_forever, daemon=True).start()
MOCK = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rpg_demo", "pad_test.py"), encoding="utf-8").read().split('MOCK = """')[1].split('"""')[0]
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""))

with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(viewport={"width": 1280, "height": 860}, has_touch=True)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(MOCK)
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port); pg.wait_for_timeout(1800)
    ev = pg.evaluate; W = pg.wait_for_timeout
    def tap(bt, ms=90): ev("__pad.btn(0,%d,1)" % bt); W(ms); ev("__pad.btn(0,%d,0)" % bt); W(160)
    state = lambda: ev("PRISM_DEMO.panel().state()")
    get = lambda i: ev("PRISM_DEMO.settings().get('%s')" % i)
    ev("__pad.plug(0,'Razer Wolverine V3 Pro (STANDARD GAMEPAD Vendor: 1532 Product: 0a3f)','standard',17,4)"); W(200)
    tap(0); W(300)                                                  # A on the title: unlocks audio like a real first press
    tap(8); W(300)
    check("View opens Settings", ev("PRISM_DEMO.panel().isOpen()"))
    check("tabs in Halo Infinite order", pg.eval_on_selector_all(".dset .tab", "e => e.map(x => x.textContent)") == ["CONTROLLER", "KEYBOARD/MOUSE", "VIDEO", "AUDIO", "GAMEPLAY", "ACCESSIBILITY"])
    pg.screenshot(path=os.path.join(DEMO, "..", "t_settings_controller.png"))
    for _ in range(3): tap(5)
    check("RB x3 -> AUDIO, first row Main", state() == {"tab": "AUDIO", "row": "MainVolume"}, state())
    for _ in range(4): tap(14)
    check("d-pad left x4: Main 80 -> 60", get("MainVolume") == 60, get("MainVolume"))
    W(300); a = ev("PRISM_DEMO.audio()")
    check("master gain follows Main (0.60)", a and abs(a["master"] - 0.6) < 0.02, a)
    tap(13); tap(13)
    check("down x2 -> Music", state()["row"] == "MusicVolume")
    for _ in range(6): tap(14)
    W(300); a = ev("PRISM_DEMO.audio()")
    check("Music 60 -> 30 (the title plays Menu Music, so its gain is unchanged)", get("MusicVolume") == 30 and a is not None, (get("MusicVolume"), a))
    pg.screenshot(path=os.path.join(DEMO, "..", "t_settings_audio.png"))
    tap(13); tap(13); tap(13); tap(13)                               # Music -> Menu Music -> Effects -> Inactive Mute -> Dynamic Range
    check("down to Dynamic Range", state()["row"] == "DynamicRange", state())
    tap(0); W(300)
    check("A: Dynamic Range -> COMPRESSED, limiter threshold drops", ev("PRISM_DEMO.settings().choice('DynamicRange')") == "COMPRESSED" and ev("PRISM_DEMO.audio()")["threshold"] < -20, ev("PRISM_DEMO.audio()"))
    tap(3); W(200)
    check("Y resets the Audio tab", get("MainVolume") == 80 and get("MusicVolume") == 60 and get("DynamicRange") == 0)
    for _ in range(3): tap(4)
    check("LB x3 -> CONTROLLER", state()["tab"] == "CONTROLLER", state())
    check("Controller tab opens on Devices (connected pad, Teach Buttons)", state()["row"] == "PadDevices" and "Razer" in pg.inner_text(".dset .row"), pg.inner_text(".dset .row")[:60])
    tap(13); tap(0); W(300)
    check("A on Teach Buttons shows the bind prompt over the tabs", "Press the button for UP" in pg.inner_text(".dset .bindbox"), pg.inner_text(".dset .bindbox")[:60])
    pg.keyboard.press("Escape"); W(300)
    check("Esc cancels the bind, the panel stays", not ev("PRISM_DEMO.pads()[0].custom") and ev("PRISM_DEMO.panel().isOpen()") and not ev("document.querySelector('.dset .bindbox').classList.contains('on')"))
    for _ in range(6): tap(13)
    check("down to Menu Confirm Button", state()["row"] == "ConfirmButton", state())
    tap(0)
    check("A: BOTTOM", ev("PRISM_DEMO.settings().choice('ConfirmButton')") == "BOTTOM")
    tap(1); W(300)
    check("B closes", not ev("PRISM_DEMO.panel().isOpen()"))
    ev("__pad.unplug(0)"); W(100)
    ev("__pad.plug(1,'Pro Controller (STANDARD GAMEPAD Vendor: 057e Product: 2009)','standard',18,4)"); W(200)
    check("Switch prompts follow the row: confirm = B (bottom)", ev("PRISM_DEMO.padLabel('confirm',1)") == "B")
    ev("PRISM_DEMO.settings().set('ConfirmButton', 0)")
    # keyboard
    pg.keyboard.press("F1"); W(250)
    check("F1 opens", ev("PRISM_DEMO.panel().isOpen()"))
    pg.keyboard.press("KeyE"); pg.keyboard.press("KeyE"); W(150)
    check("E E -> VIDEO", state()["tab"] == "VIDEO", state())
    # touch: tap the ACCESSIBILITY tab, tap Text Size twice
    pg.locator(".dset .tab", has_text="ACCESSIBILITY").tap(); W(150)
    rows = pg.locator(".dset .row")
    rows.nth(0).tap(); W(150)                                     # the selected row: one tap changes it
    check("touch: Text Size -> LARGE, panel text grows", ev("PRISM_DEMO.settings().choice('TextSize')") == "LARGE" and ev("document.querySelector('.dset').classList.contains('t1')"))
    pg.locator(".dset .tab", has_text="AUDIO").tap(); W(150)
    tr = pg.locator(".dset .row .track").first.bounding_box()
    pg.mouse.click(tr["x"] + tr["width"] * 0.25, tr["y"] + tr["height"] / 2); W(200)
    check("slider click at 25% sets Main ~25", abs(get("MainVolume") - 25) <= 5, get("MainVolume"))
    hit = pg.locator(".dset .row").first.bounding_box()
    check("rows are touch-sized (>= 44 px)", hit["height"] >= 44, hit["height"])
    pg.keyboard.press("Escape"); W(200)
    check("Esc closes", not ev("PRISM_DEMO.panel().isOpen()"))
    check("settings persist in the native flat format", '"MainVolume"' in ev("localStorage.getItem('daedalus.settings')"))
    check("app-local rows stay out of the Unreal export", "TouchControls" not in ev("JSON.stringify(PRISM_DEMO.settings().export())") and "ButtonLayout" in ev("JSON.stringify(PRISM_DEMO.settings().export())"))
    pg.set_viewport_size({"width": 390, "height": 844}); W(200)
    pg.keyboard.press("F1"); W(250)
    sw = ev("document.documentElement.scrollWidth")
    check("phone width: no horizontal scroll", sw <= 390, sw)
    pg.screenshot(path=os.path.join(DEMO, "..", "t_settings_phone.png"))
    pg.keyboard.press("Escape")
    check("no page errors", not errs, errs[:3])
    b.close()
print("PANEL %d/%d" % (sum(res), len(res)), "PASS" if all(res) else "FAIL")
sys.exit(0 if all(res) else 1)
