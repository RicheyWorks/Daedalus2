# SPDX-License-Identifier: MIT
"""Portal + Prism regression smoke test, in one browser context and HTTP origin.

    python tools/rpg_demo/portal_demo_test.py PORTAL_DIR PRISM_DIR EVIDENCE_DIR

Build both folders first. Existing PRISM_DEMO hooks stage a canonical encounter
and map entrances; movement, battle menus and inn saving use the shared engine.
No foe/party stat, inventory, reward or progression injection is used.
"""
import functools
import http.server
import json
import mimetypes
import os
from pathlib import Path
import sys
import threading
from urllib.parse import quote, unquote, urlsplit

from playwright.sync_api import sync_playwright

from bot import Bot


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    portal, prism, evidence = [Path(arg).resolve() for arg in argv]
    if portal == prism:
        raise ValueError("Portal and Prism builds must be distinct")
    root = Path(os.path.commonpath([portal, prism]))
    evidence.mkdir(parents=True, exist_ok=True)
    data = json.loads((portal / "data.json").read_text(encoding="utf-8"))
    results, errors, network = [], [], []

    def check(name, ok, detail=None):
        results.append({"name": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + (" " + str(detail) if detail is not None else ""), flush=True)
        if not ok:
            raise AssertionError(name)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    class AssetServer(http.server.ThreadingHTTPServer):
        request_queue_size = 32  # simultaneous scripts, controller JSON and real atlas images

    server = AssetServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:%d" % server.server_port
    urls = {"portal": origin + "/" + quote(portal.relative_to(root).as_posix()) + "/index.html",
            "prism": origin + "/" + quote(prism.relative_to(root).as_posix()) + "/index.html"}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--renderer-process-limit=1"])
            try:
                context = browser.new_context(viewport={"width": 1024, "height": 896})
                # This fixture validates built-file/game/storage behavior, not host HTTP transport.
                # Use the exact real files over the same HTTP URL origin; never synthesize game assets.
                def built_file(route):
                    path = (root / unquote(urlsplit(route.request.url).path).lstrip("/")).resolve()
                    if not path.is_relative_to(root) or not path.is_file():
                        route.fulfill(status=404, body="Not found")
                        return
                    route.fulfill(path=str(path), content_type=mimetypes.guess_type(str(path))[0] or "application/octet-stream")
                context.route(origin + "/**", built_file)
                context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
                context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
                context.add_init_script("""(() => {
                  const draw = CanvasRenderingContext2D.prototype.drawImage;
                  window.__battleDraws = null;
                  CanvasRenderingContext2D.prototype.drawImage = function(...a) {
                    if (window.__battleDraws && this.canvas.id === 'screen' && a.length === 9 &&
                        String(a[0].src || '').endsWith('/sprites.png') && window.__battleDraws.length < 5000)
                      window.__battleDraws.push(a.slice(1));
                    return draw.apply(this,a);
                  };
                })();""")
                page = context.new_page()
                def request_info(url, **detail):
                    parsed = urlsplit(url)
                    network.append({"host": parsed.hostname, "path": parsed.path, **detail})
                def observe(pg):
                    pg.on("pageerror", lambda error: errors.append(str(error)))
                    pg.on("requestfailed", lambda request: request_info(request.url, failure=request.failure))
                    pg.on("response", lambda response: request_info(response.url, status=response.status))
                observe(page)
                bot = Bot(page, data)
                current_realm = None

                def title(realm):
                    nonlocal page, bot, current_realm
                    if current_realm is not None and realm != current_realm:
                        # Close the old page's in-flight media fetches before changing realms.
                        # Storage remains in this exact context and origin; never create a fresh context.
                        page.close()
                        page = context.new_page()
                        observe(page)
                        bot = Bot(page, data)
                    current_realm = realm
                    page.goto(urls[realm])
                    page.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title' && PRISM_DEMO.settings().loaded() && document.getElementById('status').hidden", timeout=45000)
                    # mode starts as title before boot finishes loading its images.
                    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                    check(realm + " shares the original HTTP origin and browser context", page.context is context
                          and page.evaluate("location.origin") == origin)

                def new_game(realm):
                    title(realm)
                    bot.press("a", 400)
                    page.wait_for_function("PRISM_DEMO.state().mode === 'name'", timeout=5000)
                    check(realm + " name entry", bot.st()["mode"] == "name", bot.st()["mode"])
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1300)
                    bot.clear()
                    return bot.st()

                def walk(direction, until, limit=24):
                    page.evaluate("d => PRISM_DEMO.hold(d,true)", direction)
                    try:
                        for _ in range(limit):
                            page.wait_for_timeout(80)
                            if until(bot.st()):
                                return True
                        return False
                    finally:
                        page.evaluate("d => PRISM_DEMO.hold(d,false)", direction)
                        page.wait_for_timeout(300)

                def rest_and_save(key):
                    # Existing test seam places the player across the actual inn counter.
                    page.evaluate("PRISM_DEMO.warp('Inn',3,6)")
                    page.wait_for_timeout(400)
                    bot.face("up")
                    bot.press("a", 400)
                    asked = False
                    for _ in range(12):
                        if "REST" in (bot.st()["dialog"] or ""):
                            asked = True
                            break
                        bot.press("a", 250)
                    check(key + " actual inn prompt", asked)
                    bot.press("a", 1500)
                    for _ in range(12):
                        raw = page.evaluate("key => localStorage.getItem(key)", key)
                        if raw:
                            bot.clear()
                            return raw
                        bot.press("a", 250)
                    raise AssertionError(key + " inn did not save")

                s = new_game("portal")
                check("Portal identity + native canvas", s["realmKey"] == "portal" and s["realm"] == "Portal Realm"
                      and s["screen"] == [256, 224] and s["saveKey"] == "portal.save.v1"
                      and page.title() == "Portal Realm Playable Demo", s["realm"])
                check("Portal canonical starting party", [m[0] for m in s["party"]] == ["Arden", "Mirel", "Pike"]
                      and all(m[1] == 1 for m in s["party"]) and s["bag"] == data["party"]["start_items"])
                check("Portal has no Prism Warden progression", s["shards"] == 0 and not s["beaten"]
                      and all(d["boss_data"] is None for d in data["dungeons"]))
                check("shared summon + waystone hooks exclude Portal", page.evaluate("PRISM_DEMO.summons().all.length === 0 && PRISM_DEMO.waystones().length === 0")
                      and "waystones" not in data)
                page.evaluate("PRISM_DEMO.seed(808)")
                check("walk south through town gate", walk("down", lambda state: state["map"] == "world"), bot.st()["map"])
                # Canonical cave entrance, one real movement into the landmark.
                cave = next((x, y) for y, row in enumerate(data["world"]) for x, tile in enumerate(row) if tile == "Cave")
                page.evaluate("p => PRISM_DEMO.warp('world',p[0],p[1]-1)", cave)
                page.wait_for_timeout(350)
                check("enter Old Mine through world landmark", walk("down", lambda state: state["map"] == "dungeon"), bot.st()["map"])
                check("Old Mine first exported floor", bot.st()["floor"] == 0 and bot.st()["dungeon"] == 0)
                # Exercise both actual down-stair transitions. Staging skips long walks, not the transition.
                for index, floor in enumerate(data["dungeons"][0]["floors"][:-1]):
                    stair = floor["stairs_down"]
                    approach = next((direction, stair["x"] + dx, stair["y"] + dy)
                                    for direction, dx, dy in (("down", 0, -1), ("up", 0, 1), ("right", -1, 0), ("left", 1, 0))
                                    if 0 <= stair["y"] + dy < len(floor["grid"]) and 0 <= stair["x"] + dx < len(floor["grid"][0])
                                    and floor["grid"][stair["y"] + dy][stair["x"] + dx] in data["dungeon_walkable"])
                    page.evaluate("v => PRISM_DEMO.warp('dungeon',v.x,v.y,v.floor,0)", {"x": approach[1], "y": approach[2], "floor": index})
                    page.wait_for_timeout(350)
                    check("Old Mine descent %d" % (index + 1), walk(approach[0], lambda state: state["floor"] == index + 1))
                check("terminal unexported floor is sealed", data["dungeons"][0]["floors"][-1]["stairs_down"] is None)
                foe = min(data["foes"], key=lambda key: (data["foes"][key]["level"], data["foes"][key]["hp"], key))
                check("canonical encounter opens", bot.start_fight([foe]))
                page.evaluate("window.__battleDraws = []")
                page.wait_for_timeout(150)
                draws = page.evaluate("window.__battleDraws")
                for member in data["party"]["members"]:
                    if member["joins"] != "start":
                        continue
                    rect = data["rects"]["sprites"]["Party_" + member["job"]]
                    visible = [draw for draw in draws if draw[:4] == rect and 0 <= draw[4]
                               and draw[4] + draw[6] <= 256 and 0 <= draw[5] and draw[5] + draw[7] <= 144]
                    check("visible battle sprite: " + member["name"], bool(visible))
                blue_rows = page.evaluate("""() => {
                  const c=document.getElementById('screen').getContext('2d');
                  return [152,169,186].map(y => {
                    const p=c.getImageData(216,y,32,8).data; let n=0;
                    for(let i=0;i<p.length;i+=4) if(p[i]===160&&p[i+1]===200&&p[i+2]===255)n++;
                    return n;
                  });
                }""")
                check("all three MP values are painted inside canvas", all(n > 0 for n in blue_rows), blue_rows)
                bot.press("a", 150)
                check("visible enemy targeting opens", bot.st()["battle"]["sub"] == "target")
                page.screenshot(path=str(evidence / "portal-battle.png"))
                page.evaluate("window.__battleDraws = null")
                last = bot.fight(limit=600)
                bot.clear()
                check("Portal battle played by menus", bot.st()["mode"] == "field" and last is not None
                      and any(m[2] > 0 for m in bot.st()["party"]), foe)
                portal_raw = rest_and_save("portal.save.v1")
                portal_save = json.loads(portal_raw)
                check("Portal save tagged with realm", portal_save["realm_key"] == "portal")
                check("Portal save omits Prism waystone field", "ways" not in portal_save)
                page.screenshot(path=str(evidence / "portal-demo.png"))

                s = new_game("prism")
                check("default Prism identity + party preserved", s["realmKey"] == "prism" and s["realm"] == "Prismheart"
                      and s["screen"] == [320, 224] and s["party"][0][0] == "Corin" and s["party"][0][1] == 15)
                check("Prism summon + waystone hooks remain available", page.evaluate("PRISM_DEMO.summons().all.length > 0 && PRISM_DEMO.waystones().length > 0"))
                prism_raw = rest_and_save("prism.save.v1")
                check("same-origin Prism save preserves Portal bytes", page.evaluate("localStorage.getItem('portal.save.v1')") == portal_raw)
                # Legacy Prism v1 saves did not include realm_key: preserve their compatibility.
                legacy = json.loads(prism_raw)
                legacy.pop("realm_key", None)
                page.evaluate("s => localStorage.setItem('prism.save.v1',s)", json.dumps(legacy))
                title("prism")
                bot.press("down", 150)
                bot.press("a", 1400)
                check("legacy Prism CONTINUE still loads", bot.st()["mode"] == "field" and bot.st()["party"][0][0] == "Corin")
                prism_raw = page.evaluate("localStorage.getItem('prism.save.v1')")

                title("portal")
                bot.press("down", 150)
                bot.press("a", 1400)
                s = bot.st()
                check("Portal CONTINUE restores own journey", s["mode"] == "field" and s["party"][0][0] == "Arden"
                      and s["gold"] == portal_save["gold"] and s["map"] == "interior")
                check("both saves survive same-origin round trip", page.evaluate("localStorage.getItem('portal.save.v1')") == portal_raw
                      and page.evaluate("localStorage.getItem('prism.save.v1')") == prism_raw)
                # Realm-mismatched data at the right key must not become a Portal journey.
                page.evaluate("s => localStorage.setItem('portal.save.v1',s)", prism_raw)
                title("portal")
                bot.press("down", 150)
                bot.press("a", 400)
                check("Portal rejects a Prism save payload", bot.st()["mode"] == "title")
                page.evaluate("s => localStorage.setItem('portal.save.v1',s)", portal_raw)
                check("no browser script errors", not errors, errors)
                context.close()
            except Exception:
                try:
                    page.screenshot(path=str(evidence / "portal-failure.png"))
                    state = page.evaluate("window.PRISM_DEMO ? PRISM_DEMO.state() : null")
                    (evidence / "failure-state.json").write_text(json.dumps({"state": state, "page_errors": errors,
                        "boot_status": page.locator("#status").text_content(), "url": page.url,
                        "boot": page.evaluate("({hidden:document.getElementById('status').hidden,settingsLoaded:!!(window.PRISM_DEMO&&PRISM_DEMO.settings().loaded()),resources:performance.getEntriesByType('resource').map(r=>({path:new URL(r.name).pathname,duration:r.duration,bytes:r.transferSize}))})"),
                        "network": network[-100:]}, indent=2) + "\n", encoding="utf-8")
                except Exception as diagnosis:
                    print("Failure capture: " + str(diagnosis), flush=True)
                raise
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (evidence / "portal-demo-results.json").write_text(json.dumps({"same_origin": True, "asset_fixture": "exact built files via Playwright; host HTTP transport unvalidated", "checks": results, "page_errors": errors}, indent=2) + "\n", encoding="utf-8")
    print("PORTAL DEMO %d/%d PASS" % (len(results), len(results)), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
