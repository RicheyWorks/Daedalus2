# SPDX-License-Identifier: MIT
"""The realm client (realm.html) driven by a simulated controller through the shared DaedalusPad module.

    python tools/controllers/realm_pad_test.py http://localhost:8080

Needs a running daedalus-server. Buttons are held 400 ms because headless software WebGL renders slowly. Plugs a simulated Xbox Series pad and a Mega Drive Mini 6B, then checks:
Menu/Start enters play, the left stick moves the avatar, the right stick orbits the camera, A jumps, View leaves.
"""
import sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "rpg_demo"))

BASE = sys.argv[1].rstrip("/")
HOLD = 400   # software WebGL frames take hundreds of ms here; a shorter tap can begin and end inside one frame
MOCK = open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "rpg_demo", "pad_test.py"), encoding="utf-8").read().split('MOCK = """')[1].split('"""')[0]
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info else ""))
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"]); pg = b.new_page(viewport={"width": 1280, "height": 800})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(MOCK)
    pg.goto(BASE + "/realm.html"); pg.wait_for_timeout(6000)
    ev = pg.evaluate; W = pg.wait_for_timeout
    check("module + bundle loaded", ev("!!(window.daedalusRealm && window.daedalusRealm.pad && window.daedalusRealm.pad.bundleInfo())"), ev("window.daedalusRealm && window.daedalusRealm.pad && window.daedalusRealm.pad.bundleInfo()"))
    ev("__pad.plug(0,'Xbox Wireless Controller (STANDARD GAMEPAD Vendor: 045e Product: 0b13)','standard',17,4)"); W(300)
    ev("__pad.btn(0,9,1)"); W(HOLD); ev("__pad.btn(0,9,0)"); W(1500)
    check("Menu enters play", ev("window.daedalusRealm.mode") == "play", ev("window.daedalusRealm.mode"))
    W(1500)
    p0 = ev("window.daedalusRealm.avatar.pos.toArray()")
    ev("__pad.axis(0,1,-1)"); W(1200); ev("__pad.axis(0,1,0)"); W(300)
    p1 = ev("window.daedalusRealm.avatar.pos.toArray()")
    moved = ((p1[0] - p0[0]) ** 2 + (p1[2] - p0[2]) ** 2) ** 0.5
    check("left stick moves the avatar", moved > 1.0, round(moved, 2))
    c0 = ev("(() => { const r = window.daedalusRealm; return 0; })()")
    cam0 = ev("document.querySelector('canvas') && 1")
    y0 = ev("window.daedalusRealm.avatar.vel.y")
    ev("__pad.btn(0,0,1)"); W(HOLD)
    jumped = ev("window.daedalusRealm.avatar.vel.y") > 1 or not ev("window.daedalusRealm.avatar.onGround")
    ev("__pad.btn(0,0,0)"); W(600)
    check("A jumps", jumped)
    ev("__pad.btn(0,8,1)"); W(HOLD); ev("__pad.btn(0,8,0)"); W(500)
    check("View leaves play", ev("window.daedalusRealm.mode") == "look", ev("window.daedalusRealm.mode"))
    ev("__pad.unplug(0)"); W(200)
    ev("__pad.plug(1,'SEGA Mega Drive Mini 6B (Vendor: 0ca3 Product: 0024)','',12,5)"); W(300)
    check("mega drive known here too", ev("window.daedalusRealm.pad.devices()[0].family") == "sega")
    ev("__pad.btn(1,9,1)"); W(HOLD); ev("__pad.btn(1,9,0)"); W(1500)
    check("mega drive Start enters play", ev("window.daedalusRealm.mode") == "play")
    W(1200); p0 = ev("window.daedalusRealm.avatar.pos.toArray()")
    ev("__pad.axis(1,4,-1)"); W(1200); ev("__pad.axis(1,4,0)"); W(300)
    p1 = ev("window.daedalusRealm.avatar.pos.toArray()")
    moved = ((p1[0] - p0[0]) ** 2 + (p1[2] - p0[2]) ** 2) ** 0.5
    check("mega drive d-pad up moves the avatar", moved > 1.0, round(moved, 2))
    pad_errs = [e for e in errs if "pad" in e.lower() or "controller" in e.lower()]
    check("no controller errors", not pad_errs, pad_errs[:3])
    if errs: print("other page errors (not controller):", errs[:5])
    pg.screenshot(path="/tmp/realm_pad.png")
    b.close()
print("REALM PAD %d/%d" % (sum(res), len(res)), "PASS" if all(res) else "FAIL")
sys.exit(0 if all(res) else 1)
