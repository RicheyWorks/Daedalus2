# SPDX-License-Identifier: MIT
"""Controller tests for the Prismheart demo and the shared DaedalusPad module, with simulated pads (Playwright).

    python tools/rpg_demo/pad_test.py DEMO_DIR

The browser's Gamepad API is replaced by scripted pads that report real ids and real button numbering:
Xbox Elite Series 2 and Razer Wolverine V3 Pro (standard; a 2 ms tap shorter than a frame), Switch Pro (standard,
confirm follows the A label on the right), Mayflash N64 adapter and Sega Mega Drive Mini 6B and Astro City Mini
(non-standard, read through the community mappings in controller-bundle.json: POV hat and half-axis d-pads),
Atari CX joystick (one button: tap / hold / long hold), an unknown pad (family guess), a GameSir in DirectInput mode
taught with BIND, an arcade keyboard encoder (MAME keys), keyboard + pad held together, hot-unplug mid-walk.
"""
import functools, http.server, sys, threading
from playwright.sync_api import sync_playwright

DEMO = sys.argv[1]
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=DEMO))
threading.Thread(target=srv.serve_forever, daemon=True).start()

MOCK = """
(() => {
  const pads = [null, null, null, null];
  const mk = (index, id, mapping, nb, na, rest) => ({ index, id, mapping, connected: true, timestamp: 0,
    buttons: Array.from({ length: nb }, () => ({ pressed: false, touched: false, value: 0 })), axes: (rest || Array(na).fill(0)).slice(),
    vibrationActuator: { type: "dual-rumble", playEffect: (t, o) => { (window.__rumble = window.__rumble || []).push(o.strongMagnitude); return Promise.resolve("complete"); } } });
  navigator.getGamepads = () => pads.slice();
  window.__pad = {
    plug(index, id, mapping, nb, na, rest) { pads[index] = mk(index, id, mapping, nb, na, rest); const e = new Event("gamepadconnected"); e.gamepad = pads[index]; window.dispatchEvent(e); },
    unplug(index) { const g = pads[index]; pads[index] = null; const e = new Event("gamepaddisconnected"); e.gamepad = g; window.dispatchEvent(e); },
    btn(index, b, v) { const x = pads[index].buttons[b]; x.pressed = !!v; x.value = v ? 1 : 0; },
    axis(index, a, v) { pads[index].axes[a] = v; },
  };
})();
"""
results = []
def check(name, ok, info=""):
    results.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("  " + str(info) if info else ""))

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1100, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(MOCK)
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port); pg.wait_for_timeout(2000)
    st = lambda: pg.evaluate("PRISM_DEMO.state()")
    ev = lambda js: pg.evaluate(js)
    W = pg.wait_for_timeout
    def tap(i, bt, ms=90): ev("__pad.btn(%d,%d,1)" % (i, bt)); W(ms); ev("__pad.btn(%d,%d,0)" % (i, bt)); W(140)
    def clear():                                    # close any dialog (the town greets you on a timer)
        for _ in range(12):
            s = st()
            if s["mode"] == "field" and not s["dialog"]: return
            ev("PRISM_DEMO.press('a')" if s["dialog"] else "PRISM_DEMO.press('b')"); W(220)
    def town(x=11, y=10): ev("PRISM_DEMO.warp('town',%d,%d)" % (x, y)); W(400); clear()
    def pad(i): return next(d for d in ev("PRISM_DEMO.pads()") if d["index"] == i)
    def walks(js_on, js_off, key, ms=650):
        before = st()[key]; ev(js_on); W(ms); ev(js_off); W(400); return before, st()[key]
    pg.wait_for_function("PRISM_DEMO.bundle()", timeout=8000)
    check("bundle loaded", ev("PRISM_DEMO.bundle().devices") > 1000, ev("PRISM_DEMO.bundle()"))

    # Xbox Elite Series 2 (standard)
    ev("__pad.plug(0,'Xbox Elite Series 2 (STANDARD GAMEPAD Vendor: 045e Product: 0b00)','standard',17,4)"); W(200)
    d = pad(0); check("elite: name/family/source", d["family"] == "xbox" and d["source"] == "standard" and "Elite" in d["name"], d)
    check("plug-in notice on screen", "connected" in ev("PRISM_DEMO.toast()"), ev("PRISM_DEMO.toast()"))
    for _ in range(25):
        s = st()
        if s["mode"] == "field" and not s["dialog"]: break
        tap(0, 0)
    check("elite A: title -> town", st()["map"] == "town")
    W(800); town(11, 15)
    a, z = walks("__pad.btn(0,12,1)", "__pad.btn(0,12,0)", "y", 700); check("elite d-pad up walks", z < a, (a, z))
    clear(); tap(0, 9); W(200); check("elite Menu opens the menu", st()["mode"] == "menu", st()["mode"])
    tap(0, 1); W(300); check("elite B closes it", st()["mode"] == "field")
    clear(); x0 = st()["x"]
    ev("__pad.axis(0,0,0.6)"); W(250); ev("__pad.axis(0,0,0.45)"); W(500); ev("__pad.axis(0,0,0.3)"); W(400); x1 = st()["x"]; W(400)
    check("stick: 0.6 walks, 0.45 holds, 0.3 stops", x1 > x0 + 1 and st()["x"] == x1, (x0, x1, st()["x"]))
    check("prompt labels (xbox)", ev("PRISM_DEMO.padLabel('confirm',0)") == "A" and ev("PRISM_DEMO.padLabel('menu',0)") == "Menu")
    town()
    pg.keyboard.down("ArrowDown"); ev("__pad.btn(0,13,1)"); W(150); ev("__pad.btn(0,13,0)"); W(150)
    yk = st()["y"]; W(500); yk2 = st()["y"]; pg.keyboard.up("ArrowDown"); W(300)
    check("pad release keeps a held key walking", yk2 > yk, (yk, yk2))
    ev("__pad.unplug(0)"); W(150)

    # Razer Wolverine V3 Pro (8K): 2 ms tap
    town()
    ev("__pad.plug(1,'Razer Wolverine V3 Pro (STANDARD GAMEPAD Vendor: 1532 Product: 0a3f)','standard',17,4)"); W(150)
    d = pad(1); check("razer: curated model", d["maker"] == "Razer" and "Wolverine V3" in d["name"] and "8000" in d["note"], d["name"])
    tap(1, 9, 2); W(250); check("razer 2 ms tap opens the menu", st()["mode"] == "menu", st()["mode"])
    tap(1, 1); W(300); ev("__pad.unplug(1)"); W(150)

    # Switch Pro (standard, positional): confirm = A label = east
    ev("__pad.plug(2,'Pro Controller (STANDARD GAMEPAD Vendor: 057e Product: 2009)','standard',18,4)"); W(150)
    check("switch: family nintendo, confirm label A, back B", pad(2)["family"] == "nintendo" and ev("PRISM_DEMO.padLabel('confirm',2)") == "A" and ev("PRISM_DEMO.padLabel('cancel',2)") == "B")
    ev("PRISM_DEMO.warp('Item',5,5)"); W(400)
    ev("PRISM_DEMO.hold('up',true)"); W(60); ev("PRISM_DEMO.hold('up',false)"); W(300)
    tap(2, 0); W(300); check("switch bottom (B) does not talk", st()["dialog"] is None and st()["mode"] == "field", st()["dialog"])
    tap(2, 1); W(400); check("switch right (A) talks", st()["dialog"] is not None or st()["mode"] == "shop", st()["dialog"])
    for _ in range(10):
        if st()["mode"] == "shop": break
        tap(2, 1)
    tap(2, 0); W(300); check("switch B leaves the shop", st()["mode"] == "field")
    ev("PRISM_DEMO.settings().set('ConfirmButton', 1)"); W(100)
    check("ConfirmButton = BOTTOM (Controller tab): bottom confirms", ev("PRISM_DEMO.padLabel('confirm',2)") == "B")
    ev("PRISM_DEMO.settings().set('ConfirmButton', 0)"); W(100)
    ev("__pad.unplug(2)"); W(150)

    # Mayflash N64 adapter (community map: a:b1 b:b2 start:b9, d-pad on POV hat, stick a0/a1)
    town()
    ev("__pad.plug(3,'Mayflash N64 Adapter (Vendor: 2f24 Product: 00f4)','',16,10,[0,0,0,0,0,0,0,0,0,1.2857])"); W(150)
    d = pad(3); check("n64: community map", d["family"] == "n64" and d["source"] == "bundle", d)
    a, z = walks("__pad.axis(3,9,-0.4286)", "__pad.axis(3,9,1.2857)", "x"); check("n64 hat right walks right", z > a, (a, z))
    a, z = walks("__pad.axis(3,1,-0.9)", "__pad.axis(3,1,0)", "y", 600); check("n64 stick up walks up", z < a, (a, z))
    tap(3, 9); W(250); check("n64 Start opens the menu", st()["mode"] == "menu", st()["mode"])
    tap(3, 2); W(300); check("n64 B (b2) closes it", st()["mode"] == "field", st()["mode"])
    ev("__pad.axis(3,9,0.7143)"); W(300); ev("__pad.unplug(3)"); W(300)
    xs = st()["x"]; W(600); check("unplug mid-walk releases the direction", st()["x"] == xs, (xs, st()["x"]))

    # Sega Mega Drive Mini 6B (half-axis d-pad) and Astro City Mini (arcade family)
    town()
    ev("__pad.plug(0,'SEGA Mega Drive Mini 6B (Vendor: 0ca3 Product: 0024)','',12,5)"); W(150)
    d = pad(0); check("mega drive: sega family, community map", d["family"] == "sega" and d["source"] == "bundle", d)
    a, z = walks("__pad.axis(0,3,1)", "__pad.axis(0,3,0)", "x"); check("mega drive d-pad right (+a3) walks", z > a, (a, z))
    tap(0, 9); W(250); check("mega drive Start opens the menu", st()["mode"] == "menu")
    tap(0, 1); W(300); check("mega drive back (b1) closes it", st()["mode"] == "field")
    ev("__pad.unplug(0)"); W(100)
    ev("__pad.plug(1,'Astro City Mini (Vendor: 0ca3 Product: 0027)','',12,5)"); W(150)
    check("astro city: arcade labels", pad(1)["family"] == "arcade" and ev("PRISM_DEMO.padLabel('confirm',1)") == "K1", ev("PRISM_DEMO.padLabel('confirm',1)"))
    ev("__pad.unplug(1)"); W(100)

    # Atari CX joystick: one button (tap = confirm, hold = back, long hold = menu)
    town()
    ev("__pad.plug(2,'Atari CX Controller (Vendor: 0e6a Product: 4011)','',1,2)"); W(150)
    d = pad(2); check("atari: one-button rule", d["family"] == "atari" and d["oneButton"] and d["noStart"], d)
    check("atari prompts", ev("PRISM_DEMO.padLabel('cancel',2)") == "hold Fire", ev("PRISM_DEMO.padLabel('cancel',2)"))
    a, z = walks("__pad.axis(2,1,1)", "__pad.axis(2,1,0)", "y", 500); check("atari stick down walks", z > a, (a, z))
    ev("__pad.btn(2,0,1)"); W(1400); ev("__pad.btn(2,0,0)"); W(300); check("atari long hold opens the menu", st()["mode"] == "menu", st()["mode"])
    ev("__pad.btn(2,0,1)"); W(500); ev("__pad.btn(2,0,0)"); W(300); check("atari hold = back closes it", st()["mode"] == "field", st()["mode"])
    ev("PRISM_DEMO.warp('Item',5,4)"); W(400); clear()
    ev("PRISM_DEMO.hold('up',true)"); W(60); ev("PRISM_DEMO.hold('up',false)"); W(300)
    tap(2, 0, 80); W(400); check("atari tap = confirm talks", st()["dialog"] is not None or st()["mode"] == "shop", st()["dialog"])
    for _ in range(8):
        s = st()
        if s["mode"] == "field" and not s["dialog"]: break
        ev("PRISM_DEMO.press('b')" if s["mode"] == "shop" else "PRISM_DEMO.press('a')"); W(250)
    ev("__pad.unplug(2)"); W(100)

    # unknown pad: family guess (DaedalusControllers.json numbering, POV hat found from its resting value)
    town()
    ev("__pad.plug(3,'Mystery USB Pad (Vendor: abcd Product: 1234)','',12,4,[0,0,0,1.2857])"); W(150)
    check("unknown pad: guess", pad(3)["source"] == "guess")
    a, z = walks("__pad.axis(3,3,0.7143)", "__pad.axis(3,3,1.2857)", "x"); check("guess: hat left walks left", z < a, (a, z))
    tap(3, 9); W(250); check("guess: Button10 = Start", st()["mode"] == "menu"); tap(3, 0); W(300)
    ev("__pad.unplug(3)"); W(100)

    # GameSir in DirectInput mode, taught with BIND
    clear()
    ev("__pad.plug(0,'GameSir-T4 Kaleid (Vendor: 3537 Product: 1010)','',14,6)"); W(150)
    ev("PRISM_DEMO.settings().activate('PadTeach')"); W(150)          # Settings > Controller > Devices > Teach Buttons
    for kind, v in [("btn", 10), ("btn", 11), ("axis", (4, -1)), ("axis", (4, 1)), ("btn", 3), ("btn", 2), ("btn", 13)]:
        if kind == "btn": tap(0, v, 120)
        else: ev("__pad.axis(0,%d,%d)" % (v[0], v[1])); W(120); ev("__pad.axis(0,%d,0)" % v[0]); W(140)
    check("bind saved (toast: Buttons taught)", pad(0)["custom"] and "Buttons taught" in ev("PRISM_DEMO.toast()"), ev("PRISM_DEMO.toast()"))
    clear(); a, z = walks("__pad.axis(0,4,1)", "__pad.axis(0,4,0)", "x", 600); check("bound axis 5+ walks right", z > a, (a, z))
    clear(); tap(0, 13); W(250); check("bound Start (button 14) opens the menu", st()["mode"] == "menu")
    tap(0, 2); W(300); check("bound back (button 3) closes it", st()["mode"] == "field")
    ev("PRISM_DEMO.settings().activate('PadForget')"); W(100); check("Forget Taught Buttons clears the binding", not pad(0)["custom"])
    ev("__pad.unplug(0)"); W(100)

    # arcade keyboard encoder (MAME defaults): Ctrl = A, Digit1 = Start
    town()
    pg.keyboard.press("Digit1"); W(250); check("MAME 1 (Start) opens the menu", st()["mode"] == "menu", st()["mode"])
    pg.keyboard.press("AltLeft"); W(300); check("MAME Alt (B) closes it", st()["mode"] == "field", st()["mode"])

    # rumble reaches the pad
    ev("__pad.plug(1,'Xbox Wireless Controller (STANDARD GAMEPAD Vendor: 045e Product: 0b13)','standard',17,4)"); W(150)
    ev("PRISM_DEMO.battle(null, true)"); W(1800)          # the Warden always lands hits, so rumble must fire
    for _ in range(80):
        if ev("(window.__rumble||[]).length"): break
        tap(1, 0, 60)
    check("rumble fires on hits", ev("(window.__rumble||[]).length") > 0)
    check("no page errors", not errs, errs[:3])
    pg.screenshot(path=DEMO + "/../t_pads.png")
    b.close()
ok = all(results)
print("PADS %d/%d" % (sum(results), len(results)), "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
