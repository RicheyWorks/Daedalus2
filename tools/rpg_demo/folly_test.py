# SPDX-License-Identifier: MIT
"""Prepared integration route; SOURCE ONLY, never executed as part of this handoff.

Provenance: authenticated producer caf1b103f6cf5a3a66a3c718c139a7091b727b9d,
docs/production/PRISMHEART-ULTRA-POLISH.md (v11-ultra-folly-r1), preserved by
CONTROLLER-CONSUMER-ULTRA-R2.md; producer source baseline 9175723ad200b05558a2ea12470763c3b9432152.
Prepared against continuation 4c89b11359f2b6501343254984a587af04cf57d3.
Uses the existing Bot/Playwright patterns and PRISM_DEMO public hooks only.

Future authorized invocation against an explicitly served LOCAL build:
  python tools/rpg_demo/folly_test.py --url http://127.0.0.1:8000/index.html --demo-dir PATH

Placement warps and one-HP foes are deliberate harness setup. The Folly floors,
stairs, gate, recruitment, ORDER, Inn conversation, drill, SAVE and CONTINUE run
through actual input/game handlers. This is NOT balance, physical-controller,
asset-quality, native integration or published-release acceptance. No server is
started, no dependencies are installed, and imports/browser work occur only in main.
"""


def main():
    import argparse
    from collections import deque
    import json
    from pathlib import Path
    import sys
    import time
    from urllib.parse import urljoin, urlparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Explicit local demo URL, including its port")
    parser.add_argument("--demo-dir", required=True, type=Path, help="Matching local build directory containing data.json")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--timeout", type=int, default=240, help="Route budget in seconds, checked between bounded helpers")
    args = parser.parse_args()
    base = urlparse(args.url)
    if base.scheme not in {"http", "https"} or base.hostname not in {"localhost", "127.0.0.1", "::1"} or base.port is None or base.username or base.password:
        parser.error("--url must explicitly name a loopback host and port; live/published targets are unsupported")
    if not (base.path.endswith("/") or base.path.endswith("/index.html")) or base.query or base.fragment:
        parser.error("--url must end in / or /index.html without a query or fragment")
    if args.timeout < 30 or args.timeout > 900:
        parser.error("--timeout must be between 30 and 900 seconds")
    D = json.loads((args.demo_dir / "data.json").read_text(encoding="utf-8"))
    names = [d["name"] for d in D["dungeons"]]
    expected = ["Cinder Forge", "Windcut Aerie", "Sunwell Sanctum", "The Shattered Heart", "Gearwright's Folly"]
    if D.get("realm_key") != "prism" or names != expected or not D["dungeons"][4].get("optional"):
        parser.error("the local data.json must contain the preserved four Prism routes followed by optional Folly")
    from playwright.sync_api import sync_playwright
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from bot import Bot

    checked, errors, speed = [], [], 6
    deadline = time.monotonic() + args.timeout

    def check(label, ok, info=""):
        if not ok:
            raise AssertionError(label + (": " + str(info) if info else ""))
        checked.append(label)
        print("ok   " + label, flush=True)

    def budget():
        if time.monotonic() > deadline:
            raise TimeoutError("Folly integration route exceeded its explicit time budget")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()  # Isolated storage: never clear or alter an existing user profile.
        def local_only(route):
            target = urlparse(route.request.url)
            if (target.scheme, target.hostname, target.port) == (base.scheme, base.hostname, base.port):
                route.continue_()
            else:
                route.abort()
        context.route("**/*", local_only)
        pg = context.new_page()
        pg.set_default_timeout(5000)
        pg.on("pageerror", lambda error: errors.append(str(error)))
        try:
            response = pg.request.get(urljoin(args.url, "data.json"), max_redirects=0)
            check("explicit local URL serves the supplied build data", response.ok and response.json() == D)
            pg.goto(args.url)
            pg.bring_to_front()
            pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'")
            pg.wait_for_function("!PRISM_DEMO.settings() || PRISM_DEMO.settings().loaded()")
            bot = Bot(pg, D)
            ev, st, wait = bot.ev, bot.st, pg.wait_for_timeout
            ev("PRISM_DEMO.seed(%d); PRISM_DEMO.speed(%d)" % (args.seed, speed))
            directions = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

            def reveal():
                text = st()["dialog"] or ""
                wait(min(900, len(text) * 1000 / (45 * speed) + 100))

            def clear_plain(stop=None):
                for _ in range(24):
                    budget()
                    text = st()["dialog"]
                    if not text or stop and stop in text:
                        return
                    reveal()
                    bot.press("a", 90)
                raise AssertionError("plain dialogue did not finish at the expected boundary")

            def finish_encounter():
                budget()
                if st()["mode"] == "battle":
                    print("info harness encounter: existing foes(1), not balance acceptance", flush=True)
                    ev("PRISM_DEMO.foes(1)")
                    bot.fight(limit=500)
                    check("encounter returns to the field", st()["mode"] == "field", st()["mode"])
                    clear_plain()

            def move(direction):
                budget()
                # Observe/release in the same browser RAF as the first coordinate change.
                # A Python round trip must not leave a direction held for extra accelerated steps.
                pg.evaluate("""async direction => {
                  const start = PRISM_DEMO.state();
                  await new Promise((resolve, reject) => {
                    let done = false;
                    const finish = error => { if (done) return; done = true; clearTimeout(timer); PRISM_DEMO.hold(direction, false); error ? reject(error) : resolve(); };
                    const timer = setTimeout(() => finish(new Error('bounded movement timed out')), 3000);
                    PRISM_DEMO.hold(direction, true);
                    const observe = () => { if (done) return; const s = PRISM_DEMO.state();
                      if (s.x !== start.x || s.y !== start.y || s.map !== start.map || s.floor !== start.floor || s.mode === 'battle') finish();
                      else requestAnimationFrame(observe); };
                    requestAnimationFrame(observe);
                  });
                }""", direction)
                wait(150)
                finish_encounter()

            def path_to(grid, start, goal, walkable, blocked=()):
                blocked, previous, queue = set(blocked), {start: None}, deque([start])
                while queue and len(previous) <= sum(map(len, grid)):
                    at = queue.popleft()
                    if at == goal:
                        result = []
                        while previous[at] is not None:
                            result.append(at)
                            at = previous[at]
                        return list(reversed(result))
                    for dx, dy in directions.values():
                        point = (at[0] + dx, at[1] + dy)
                        if point in previous or point in blocked or not (0 <= point[1] < len(grid) and 0 <= point[0] < len(grid[point[1]])):
                            continue
                        tile = grid[point[1]][point[0]]
                        if tile not in walkable or tile in {"StairsUp", "StairsDown", "ExitMat", "BossGate"} and point != goal:
                            continue
                        previous[point] = at
                        queue.append(point)
                return None

            def walk_to(grid, goal, walkable, blocked=(), transition=False):
                s = st()
                route = path_to(grid, (s["x"], s["y"]), goal, walkable, blocked)
                check("authored tiles provide a bounded walkable route", route is not None, goal)
                for point in route:
                    before = st()
                    delta = (point[0] - before["x"], point[1] - before["y"])
                    direction = next(d for d, step in directions.items() if step == delta)
                    move(direction)
                    after = st()
                    changed = (after["map"], after["dungeon"], after["floor"]) != (before["map"], before["dungeon"], before["floor"])
                    check("walking follows actual map collision/stair handlers", changed and transition and point == goal or not changed and (after["x"], after["y"]) == point, after)
                    if changed:
                        return

            def warp(kind, x, y):
                ev("PRISM_DEMO.warp(%s,%d,%d)" % (json.dumps(kind), x, y))
                wait(180)

            def dock():
                pad = next((x, y) for y, row in enumerate(D["world"]) for x, tile in enumerate(row) if tile == "AirshipPad")
                walkable = {name for name, tile in D["world_tiles"].items() if tile.get("walkable") and tile.get("kind") != "landmark"}
                for direction, (dx, dy) in directions.items():
                    before = (pad[0] - 2 * dx, pad[1] - 2 * dy)
                    stand = (pad[0] - dx, pad[1] - dy)
                    if all(0 <= y < len(D["world"]) and 0 <= x < len(D["world"][y]) and D["world"][y][x] in walkable for x, y in [before, stand]):
                        warp("world", *before)
                        move(direction)
                        check("dock approach stops adjacent without boarding", (st()["x"], st()["y"]) == stand and not ev("PRISM_DEMO.airship().flying"))
                        bot.press("a", 180)
                        return
                raise AssertionError("authored dock has no two-tile approach; do not invent a facing hook")

            def menu_pick(command):
                bot.press("start", 150)
                check("field menu opens", st()["mode"] == "menu")
                for _ in range(12):
                    menu = ev("PRISM_DEMO.menu()")
                    if menu["cmds"][menu["idx"]] == command:
                        bot.press("a", 150)
                        return
                    bot.press("down", 70)
                raise AssertionError("requested existing menu command was not found")

            def save_field():
                menu_pick("SAVE")
                raw = ev("localStorage.getItem(PRISM_DEMO.state().saveKey)")
                check("field SAVE writes a v1 journey", bool(raw) and json.loads(raw)["v"] == 1)
                bot.press("b", 120)
                return raw, json.loads(raw)

            def approach(grid, point, walkable, blocked):
                s = st()
                for direction, (dx, dy) in directions.items():
                    goal = (point[0] - dx, point[1] - dy)
                    if path_to(grid, (s["x"], s["y"]), goal, walkable, blocked) is not None:
                        walk_to(grid, goal, walkable, blocked)
                        bot.face(direction)  # Target is an NPC or closed gate, so this faces without walking into it.
                        check("interaction approach stays on its adjacent tile", (st()["x"], st()["y"]) == goal)
                        bot.press("a", 180)
                        return
                raise AssertionError("no authored route to the interaction point")

            def bench():
                room = D["interiors"]["Inn"]
                tiles = {**D["town_tiles"], **D["interior_tiles"]}
                walkable = {name for name, tile in tiles.items() if tile.get("walkable")}
                blocked = {(n["x"], n["y"]) for n in room["npcs"]} | {(11, 6)}
                approach(room["grid"], (11, 6), walkable, blocked)
                check("actual Inn Brannoc starts his workshop conversation", "BRANNOC:" in (st()["dialog"] or ""))
                clear_plain("TRY A CALIBRATION")
                check("workshop asks before starting", "TRY A CALIBRATION" in (st()["dialog"] or ""))
                reveal()
                bot.press("a", 150)

            def drill(run):
                seen = set()
                for turn in range(3):
                    budget()
                    text = st()["dialog"] or ""
                    check("actual drill presents its next reading", text.startswith("READING %d/3:" % (turn + 1)), text)
                    key = next((key for key in ["RED GAUGE", "CRYSTAL PULSE", "TAIL GEAR"] if key in text), None)
                    check("reading is one of the authored pressure/timing/heat clues", key is not None)
                    seen.add(key)
                    # These are the authored answers/rotated positions, not a new application hook.
                    answer = 1 if key == "CRYSTAL PULSE" else 0
                    if (turn + run) % 2:
                        answer = 1 - answer
                    reveal()
                    if answer:
                        bot.press("down", 80)
                    bot.press("a", 120)
                    check("the actual answer produces explanatory feedback", any(good in (st()["dialog"] or "") for good in ["THE PRESSURE FALLS", "THE TIMING MARKS MEET", "A TIDE TRICKLE"]))
                    reveal()
                    bot.press("a", 120)
                check("all three readings completed with a perfect score", len(seen) == 3 and "3/3" in (st()["dialog"] or ""))
                clear_plain()

            bot.press("a", 150)
            pg.wait_for_function("PRISM_DEMO.state().mode === 'name'")
            bot.press("start", 180)
            pg.wait_for_function("PRISM_DEMO.state().mode === 'field'")
            wait(700)
            clear_plain()
            dock()
            check("optional works reject fewer than three shards", st()["map"] == "world" and "THREE" in (st()["dialog"] or "") and st()["shards"] == 0)
            clear_plain()
            for di in range(3):
                budget()
                print("info harness setup: original boss %d uses placement warp and foes(1); not balance acceptance" % di, flush=True)
                check("existing original boss gate starts its fight", bot.to_boss(di))
                ev("PRISM_DEMO.foes(1)")
                bot.fight(limit=500)
                check("original boss grants its shard through victory handlers", D["dungeons"][di]["boss_data"]["name"] in st()["beaten"])
                clear_plain()
            check("three original shards earned", st()["shards"] == 3)
            bot.rest()
            dock()
            clear_plain()
            pg.wait_for_function("PRISM_DEMO.state().map === 'dungeon' && PRISM_DEMO.state().dungeon === 4")
            folly = D["dungeons"][4]
            check("optional entry starts Folly floor zero", st()["floor"] == 0 and len(folly["floors"]) == 3)
            walkable = set(D["dungeon_walkable"]) | {"Hazard", "StairsUp", "StairsDown"}
            for floor in range(2):
                fl = folly["floors"][floor]
                walk_to(fl["grid"], (fl["stairs_down"]["x"], fl["stairs_down"]["y"]), walkable, transition=True)
                check("actual stairs descend to Folly floor %d" % (floor + 1), st()["floor"] == floor + 1)
            fl = folly["floors"][2]
            gate = fl["boss"]["gate"]
            approach(fl["grid"], (gate["x"], gate["y"]), walkable, {(gate["x"], gate["y"])})
            check("actual third-floor gate asks about the Colossus", "COLOSSUS" in (st()["dialog"] or ""))
            reveal()
            bot.press("a", 180)
            pg.wait_for_function("PRISM_DEMO.state().mode === 'battle'")
            print("info harness Colossus: foes(1); canonical balance remains untested", flush=True)
            ev("PRISM_DEMO.foes(1)")
            bot.fight(limit=500)
            clear_plain()
            check("Colossus victory recruits Brannoc without a fourth shard", folly["boss_data"]["name"] in st()["beaten"] and st()["shards"] == 3 and any(m["job"] == "Gearwright" for m in ev("PRISM_DEMO.roster()")))
            menu_pick("ORDER")
            roster = ev("PRISM_DEMO.roster()")
            brannoc = next(i for i, m in enumerate(roster) if m["job"] == "Gearwright")
            for target in [3, brannoc]:
                for _ in range(len(roster) + 1):
                    if ev("PRISM_DEMO.menu().ii") == target:
                        break
                    bot.press("down", 70)
                bot.press("a", 90)
            check("ORDER fields the earned Gearwright among eight companions", len(roster) == 8 and any(m["job"] == "Gearwright" and m["front"] for m in ev("PRISM_DEMO.roster()")))
            bot.press("b", 90)
            bot.press("b", 90)
            for floor in [2, 1, 0]:
                fl = folly["floors"][floor]
                walk_to(fl["grid"], (fl["stairs_up"]["x"], fl["stairs_up"]["y"]), walkable, transition=True)
                check("actual stairs return through Folly floor %d" % floor, st()["floor"] == floor - 1 if floor else st()["map"] == "world")
            spawn = D["interiors"]["Inn"]["spawn"]
            warp("Inn", spawn["x"], spawn["y"])
            bench()
            reveal()
            before = st()["bag"].copy()
            ev("PRISM_DEMO.press('a'); PRISM_DEMO.press('b')")
            wait(120)
            check("Back plus Confirm cancels the real drill without reward", st()["bag"] == before and "NO SCORE OR REWARD" in (st()["dialog"] or ""))
            clear_plain()
            _, cancelled = save_field()
            check("cancelled drill records no completed run", not any(k.startswith("workshop/folly/runs/") for k in cancelled["opened"]))
            bench()
            drill(0)
            check("first perfect grants exactly two existing Herb Tonics", st()["bag"].get("Herb Tonic", 0) == before.get("Herb Tonic", 0) + 2)
            bench()
            drill(1)
            check("replay does not farm another item reward", st()["bag"].get("Herb Tonic", 0) == before.get("Herb Tonic", 0) + 2)
            raw, record = save_field()
            check("SAVE retains workshop records and one-time reward flag", {"workshop/folly/runs/2", "workshop/folly/best/3", "workshop/folly/first-perfect"}.issubset(record["opened"]))
            pg.reload()
            pg.bring_to_front()
            pg.wait_for_function("PRISM_DEMO.state().mode === 'title'")
            pg.wait_for_function("!PRISM_DEMO.settings() || PRISM_DEMO.settings().loaded()")
            ev("PRISM_DEMO.speed(%d)" % speed)
            bot.press("down", 100)
            bot.press("a", 180)
            pg.wait_for_function("PRISM_DEMO.state().mode === 'field'")
            wait(700)
            clear_plain()
            check("CONTINUE restores eight companions and the earned reward", len(ev("PRISM_DEMO.roster()")) == 8 and st()["bag"] == record["bag"])
            check("CONTINUE preserves the original stored record", ev("localStorage.getItem(PRISM_DEMO.state().saveKey)") == raw)
            bench()  # No warp: this verifies the Inn NPC prepared by CONTINUE itself.
            check("restored Inn Brannoc offers the actual drill again", (st()["dialog"] or "").startswith("READING 1/3:"))
            check("no browser page errors during this integration route", not errors, errors[:3])
            print("FOLLY integration %d/%d PASS; accelerated/harness combat, not balance acceptance" % (len(checked), len(checked)), flush=True)
            return 0
        except Exception as error:
            print("FOLLY integration FAIL: " + str(error), file=sys.stderr, flush=True)
            return 1
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
