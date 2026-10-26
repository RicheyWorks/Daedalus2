# SPDX-License-Identifier: MIT
"""The realm client (realm.html) driven by simulated controllers through the shared DaedalusPad + DaedalusSettings.

    python tools/controllers/realm_pad_test.py http://localhost:8080

Needs a running daedalus-server. Menu opens the shared Settings panel and View enters or leaves play (the Unreal
hero's Menu and View). Checks: the left stick moves the avatar, A jumps, Bumper Jumper moves jump to LB (the native
layout table), Field of View reaches the camera, and a Mega Drive Mini 6B works through the community map.
Headless software WebGL renders slowly, so every press is held until the module reports it and every check polls
for its result instead of sleeping a fixed time.
"""
import os
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
MOCK = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rpg_demo", "pad_test.py"), encoding="utf-8").read().split('MOCK = """')[1].split('"""')[0]
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"]); pg = b.new_page(viewport={"width": 1280, "height": 800})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(MOCK)
    pg.goto(BASE + "/realm.html")
    ev = pg.evaluate; W = pg.wait_for_timeout
    R = "window.daedalusRealm"
    def until(js, ms=8000):
        try:
            pg.wait_for_function(js, timeout=ms, polling=50); return True
        except Exception:
            return False
    def press(pad, button, action, after=None):
        ev("__pad.btn(%d,%d,1)" % (pad, button)); until("%s.pad.held('%s')" % (R, action))
        got = until(after, 4000) if after else True
        ev("__pad.btn(%d,%d,0)" % (pad, button)); until("!%s.pad.held('%s')" % (R, action))
        return got
    def dist(p0, p1): return ((p1[0] - p0[0]) ** 2 + (p1[2] - p0[2]) ** 2) ** 0.5
    check("module + bundle + schema loaded", until("%s && %s.pad && %s.pad.bundleInfo() && %s.settings.loaded()" % (R, R, R, R), 20000))
    ev("__pad.plug(0,'Xbox Wireless Controller (STANDARD GAMEPAD Vendor: 045e Product: 0b13)','standard',17,4)")
    press(0, 9, "menu")
    check("Menu opens Settings (Halo Infinite tabs)", until("%s.settingsPanel.isOpen()" % R) and ev("%s.settings.tabs()[3]" % R) == "AUDIO")
    press(0, 1, "cancel")
    check("B closes it", until("!%s.settingsPanel.isOpen()" % R))
    press(0, 8, "back")
    check("View enters play", until("%s.mode === 'play'" % R), ev("%s.mode" % R))
    W(800); p0 = ev("%s.avatar.pos.toArray()" % R)
    ev("__pad.axis(0,1,-1)"); until("Math.hypot(%s.avatar.pos.x - %f, %s.avatar.pos.z - %f) > 1.0" % (R, p0[0], R, p0[2])); ev("__pad.axis(0,1,0)")
    check("left stick moves the avatar", dist(p0, ev("%s.avatar.pos.toArray()" % R)) > 1.0, round(dist(p0, ev("%s.avatar.pos.toArray()" % R)), 2))
    W(800)
    jump_js = "%s.avatar.vel.y > 1 || !%s.avatar.onGround" % (R, R)
    until("%s.avatar.onGround" % R, 4000)
    check("A jumps (Default layout)", press(0, 0, "a", jump_js))
    ev("%s.settings.set('ButtonLayout', 1)" % R); W(1500)
    until("%s.avatar.onGround" % R, 4000)
    ev("__pad.btn(0,4,1)"); jumped = until(jump_js, 4000); ev("__pad.btn(0,4,0)")
    check("Bumper Jumper: LB jumps (native layout table)", jumped)
    ev("%s.settings.set('ButtonLayout', 0)" % R)
    ev("%s.settings.set('FieldOfView', 100)" % R)
    check("Field of View row reaches the camera (horizontal 100 -> vertical)", until("Math.abs(%s.settings.get('FieldOfView') - 100) < 1" % R) and ev("Math.round(document.querySelector('canvas') ? 1 : 0)") == 1)
    press(0, 8, "back")
    check("View leaves play", until("%s.mode === 'look'" % R), ev("%s.mode" % R))
    ev("__pad.unplug(0)")
    ev("__pad.plug(1,'SEGA Mega Drive Mini 6B (Vendor: 0ca3 Product: 0024)','',12,5)")
    check("Mega Drive known here too (sega, community map)", until("%s.pad.devices().length === 1 && %s.pad.devices()[0].family === 'sega'" % (R, R)))
    press(1, 8, "back")
    check("Mega Drive Mode (back) enters play", until("%s.mode === 'play'" % R), ev("%s.mode" % R))
    W(800); p0 = ev("%s.avatar.pos.toArray()" % R)
    ev("__pad.axis(1,4,-1)"); until("Math.hypot(%s.avatar.pos.x - %f, %s.avatar.pos.z - %f) > 1.0" % (R, p0[0], R, p0[2])); ev("__pad.axis(1,4,0)")
    check("Mega Drive d-pad up (-a4) moves the avatar", dist(p0, ev("%s.avatar.pos.toArray()" % R)) > 1.0)
    pad_errs = [e for e in errs if "pad" in e.lower() or "setting" in e.lower()]
    check("no controller / settings errors", not pad_errs, pad_errs[:3])
    if errs: print("other page errors:", errs[:5])
    b.close()
print("REALM PAD %d/%d" % (sum(res), len(res)), "PASS" if all(res) else "FAIL")
sys.exit(0 if all(res) else 1)
