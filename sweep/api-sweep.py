#!/usr/bin/env python3
"""API-level regression sweep across every ADR-006 feature. Each check reports pass/fail
with evidence and never aborts the run, so one break doesn't hide the rest."""
import json, time, urllib.request, urllib.error

API = "http://localhost:8080/api/v1"
results = []

def call(method, path, body=None, retries=4):
    """Call the API, backing off on 429.

    The sweep exercises every feature back to back, which is exactly the traffic the per-key
    rate limiter exists to throttle — the heavier endpoints (generate, campaign planning, the
    complexity lab) share one budget. A 429 here is the server behaving correctly, so the
    client backs off and retries rather than reporting a feature as broken.

    Error bodies are parsed as JSON when the server sends RFC 7807 ProblemDetail, so a check can
    assert on `title` or a custom property instead of substring-matching a truncated string.
    (There used to be an `expect=` parameter here that was accepted and then never used — a
    parameter shaped like an assertion that asserted nothing. Removed rather than implemented:
    every caller already compares the status it got.)"""
    data = json.dumps(body).encode() if body else None
    for attempt in range(retries):
        req = urllib.request.Request(API + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if body else {})
        try:
            with urllib.request.urlopen(req) as r:
                txt = r.read()
                return r.status, (json.loads(txt) if txt else None)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue
            if e.code == 429:
                # The default mazeGenerate budget is 30/minute; a full sweep exercises far more
                # than that, so sustained throttling here is the limiter working, not a defect.
                raise AssertionError(
                    "rate limited after retries — run the server with generous limits for a "
                    "full sweep:  SPRING_PROFILES_ACTIVE=test java -jar ...-exec.jar")
            raw = e.read().decode()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, raw[:200]
    return 429, "rate limited after retries"

def check(name, fn):
    try:
        ok, evidence = fn()
    except Exception as ex:
        ok, evidence = False, f"{type(ex).__name__}: {ex}"
    results.append((name, ok, evidence))
    print(f"{'PASS' if ok else '**FAIL**':10} {name:38} {evidence}", flush=True)

def gen(g="recursive-backtracker", r=15, c=15, seed=7):
    """Generate a maze, failing loudly if the server refused.

    Returning the raw body on error made every downstream check die with
    `TypeError: string indices must be integers` — a message that says nothing about the
    actual cause (a 429, a validation error). A helper that hides the real failure behind a
    confusing one costs more time than the failure itself."""
    st, m = call("POST", "/maze/generate",
                 {"generatorId": g, "rows": r, "cols": c, "seed": seed})
    if st != 200 or not isinstance(m, dict):
        raise AssertionError(f"generate({g},{r}x{c},seed={seed}) -> {st}: {m}")
    return m

# ---- 1. generation + determinism -------------------------------------------------
def t_generate():
    a, b = gen(seed=101), gen(seed=101)
    return a["tiles"] == b["tiles"], f"same seed -> identical tiles ({a['rows']}x{a['cols']})"

# ---- 2. solvers ------------------------------------------------------------------
def t_solvers():
    m = gen()
    st, algos = call("GET", "/algorithms")
    ids = [a["id"] for a in algos["solvers"]]
    solved, failed = 0, []
    for sid in ids:
        s, r = call("POST", f"/maze/{m['id']}/solve/{sid}")
        if s == 200 and r.get("path"):
            solved += 1
        else:
            failed.append(sid)
    return not failed, f"{solved}/{len(ids)} solvers returned a route" + (f"; failed={failed}" if failed else "")

# ---- 3. replay (arena's data source) ---------------------------------------------
def t_replay():
    m = gen()
    s, r = call("POST", f"/maze/{m['id']}/solve/astar?replay=true")
    exp = r.get("expansions") or []
    return len(exp) > 0 and len(exp) >= len(r["path"]), \
        f"{len(exp)} expansions recorded for a {len(r['path'])}-cell route"

# ---- 4. living mazes (idea 1) ----------------------------------------------------
def t_living():
    m = gen(seed=202)
    before = sum(row.count('#') for row in m["tiles"])
    s, live = call("POST", f"/maze/{m['id']}/live?ticks=4")
    if s != 200:
        return False, f"live returned {s}: {live}"
    time.sleep(6)
    _, after_m = call("GET", f"/maze/{m['id']}")
    after = sum(row.count('#') for row in after_m["tiles"])
    return after < before, f"walls {before} -> {after} (erosion opened {before-after})"

# ---- 5. traffic (idea 3) ---------------------------------------------------------
def t_traffic():
    m = gen(seed=303)
    s, st = call("POST", f"/maze/{m['id']}/traffic")
    if s != 200:
        return False, f"traffic returned {s}: {st}"
    _, agent = call("POST", f"/maze/{m['id']}/agent")
    d = agent["open"][0]
    opp = {"NORTH":"SOUTH","SOUTH":"NORTH","EAST":"WEST","WEST":"EAST"}[d]
    for i in range(12):
        call("POST", f"/agent/{agent['agentId']}/step?direction={d if i%2==0 else opp}")
    time.sleep(3)
    _, m2 = call("GET", f"/maze/{m['id']}")
    hs = m2.get("hotspots") or []
    return len(hs) > 0, f"{len(hs)} congested cells, peak cost {max((h['cost'] for h in hs), default=0):.0f}"

# ---- 6. fog-of-war agents (idea 7) -----------------------------------------------
def t_agents():
    m = gen(seed=404)
    s, a = call("POST", f"/maze/{m['id']}/agent")
    if s != 200:
        return False, f"agent create {s}"
    s2, stepped = call("POST", f"/agent/{a['agentId']}/step?direction={a['open'][0]}")
    illegal = [d for d in ["NORTH","SOUTH","EAST","WEST"] if d not in stepped["open"]]
    # Documented contract: "Walking into a wall answers 400 without consuming budget."
    bad = call("POST", f"/agent/{a['agentId']}/step?direction={illegal[0]}")[0] if illegal else 400
    budget_kept = call("GET", f"/agent/{a['agentId']}")[1]["stepsUsed"] == stepped["stepsUsed"]
    return s2 == 200 and bad == 400 and budget_kept, \
        f"legal step ok; wall step -> {bad} and consumed no budget; agent sees {len(stepped['open'])} exits"

# ---- 7. daily + per-maze leaderboard (idea 4) ------------------------------------
def t_daily_board():
    s, d = call("GET", "/maze/daily")
    if s != 200:
        return False, f"daily {s}"
    mid = d["maze"]["id"]
    s2, d2 = call("GET", "/maze/daily")
    stable = d2["maze"]["id"] == mid
    st, board = call("GET", f"/leaderboard?n=5&maze={mid}")
    return stable and st == 200, f"daily {d['date']} stable across calls; per-maze board responds"

# ---- 8. ghosts (idea 8) ----------------------------------------------------------
def t_ghost():
    m = gen(seed=505, r=9, c=9)
    mid = m["id"]
    if call("GET", f"/maze/{mid}/ghost")[0] != 404:
        return False, "ghost existed before any completed run"
    _, route = call("POST", f"/maze/{mid}/solve/bfs")
    _, sess = call("POST", f"/maze/{mid}/session?player=sweeper")
    for p in route["path"][1:]:
        call("POST", f"/session/{sess['sessionId']}/move", {"to": {"row": p["row"], "col": p["col"]}})
    s, g = call("GET", f"/maze/{mid}/ghost")
    board = call("GET", f"/leaderboard?n=5&maze={mid}")[1]
    return s == 200 and g["playerName"] == "sweeper" and len(board) == 1, \
        f"ghost recorded {len(g['moves'])} moves; stage board has {len(board)} entry"

# ---- 9. analytics (idea 9) -------------------------------------------------------
def t_analysis():
    m = gen(seed=606, r=21, c=21)
    s, a = call("GET", f"/maze/{m['id']}/analysis")
    return s == 200 and a["cutSize"] == 1 and a["deadEndCount"] > 0, \
        f"cut={a['cutSize']} (perfect maze must be 1), deadEnds={a['deadEndCount']}, route={a['routeLength']}"

# ---- 10. crossbreeding (idea 5) + rock preservation ------------------------------
def t_breed():
    a = gen("recursive-backtracker", 21, 21, 11)
    b = gen("binary-tree", 21, 21, 12)
    s, child = call("POST", f"/maze/breed?a={a['id']}&b={b['id']}&seed=5")
    if s != 200:
        return False, f"breed {s}: {child}"
    _, route = call("POST", f"/maze/{child['id']}/solve/bfs")
    mismatch = call("POST", f"/maze/breed?a={a['id']}&b={gen(r=9,c=9)['id']}")[0]
    # dungeon x dungeon must keep rock
    d1, d2 = gen("dungeon", 21, 21, 1), gen("dungeon", 21, 21, 2)
    _, dchild = call("POST", f"/maze/breed?a={d1['id']}&b={d2['id']}&seed=3")
    def rock(mz):
        t, n = mz["tiles"], 0
        for r in range(mz["rows"]):
            for c in range(mz["cols"]):
                tr, tc = 2*r+1, 2*c+1
                if (t[tr-1][tc]=='#' and t[tr+1][tc]=='#' and t[tr][tc-1]=='#'
                        and t[tr][tc+1]=='#' and t[tr][tc] not in 'SG'):
                    n += 1
        return n
    rk = rock(dchild)
    return bool(route["path"]) and mismatch == 400 and rk > 100, \
        f"child solvable; mismatched dims -> {mismatch}; dungeon child keeps {rk}/441 rock"

# ---- 11. spectator (idea 6) ------------------------------------------------------
def t_spectator():
    m = gen(seed=707, r=9, c=9)
    _, sess = call("POST", f"/maze/{m['id']}/session?player=runner")
    sid = sess["sessionId"]
    s, before = call("GET", f"/session/{sid}")
    _, route = call("POST", f"/maze/{m['id']}/solve/bfs")
    p = route["path"][1]
    call("POST", f"/session/{sid}/move", {"to": {"row": p["row"], "col": p["col"]}})
    _, after = call("GET", f"/session/{sid}")
    unknown = call("GET", f"/session/00000000-0000-4000-8000-000000000000")[0]
    return before["moveCount"] == 0 and after["moveCount"] == 1 and unknown == 404, \
        f"view tracked 0 -> 1 moves; unknown session -> {unknown}"

# ---- 12. campaign (idea 10) ------------------------------------------------------
def t_campaign():
    s, c = call("GET", "/campaign?seed=2026")
    if s != 200:
        return False, f"campaign {s}"
    scores = [st["grade"]["score"] for st in c["stages"]]
    rising = all(scores[i] > scores[i-1] for i in range(1, len(scores)))
    _, again = call("GET", "/campaign?seed=2026")
    stable = [st["mazeId"] for st in again["stages"]] == [st["mazeId"] for st in c["stages"]]
    last = c["stages"][-1]
    hazards = set(last["hazards"]) == {"living", "traffic", "hardening"}
    playable = bool(call("POST", f"/maze/{c['stages'][0]['mazeId']}/solve/bfs")[1]["path"])
    return rising and stable and hazards and playable, \
        f"ladder {[round(x,1) for x in scores]} rising={rising}, ids stable={stable}, finale hazards={sorted(last['hazards'])}"

# ---- 13. multiplayer + move legality ---------------------------------------------
def t_multiplayer_and_legality():
    m = gen(seed=808, r=11, c=11)
    _, sess = call("POST", f"/maze/{m['id']}/session?player=p1")
    sid = sess["sessionId"]
    far = {"row": m["rows"] - 1, "col": m["cols"] - 1}   # not adjacent: must be refused
    # The endpoint answers 200 with a BOOLEAN body: false means refused. Checking only the
    # status reads a correct rejection as an accepted teleport.
    st, accepted = call("POST", f"/session/{sid}/move", {"to": far})
    _, view = call("GET", f"/session/{sid}")
    # Flag-agnostic: join either works (flag on) or 404s "as if it did not exist" (flag off).
    # Assert the OUTCOME matches whichever contract is in force, so the check is valid either
    # way instead of encoding the environment it first ran in.
    joined = call("POST", f"/session/{sid}/join?player=p2")[0]
    _, after_join = call("GET", f"/session/{sid}")
    players = sorted(after_join["players"].keys())
    mp_ok = (joined == 200 and players == ["p1", "p2"]) or (joined == 404 and players == ["p1"])
    flag = "on" if joined == 200 else "off"
    return st == 200 and accepted is False and view["moveCount"] == 0 and mp_ok, \
        (f"teleport -> {st} body={accepted}, moveCount still {view['moveCount']}; "
         f"join (multiplayer {flag}) -> {joined}, players={players}")

# ---- 15. waypoint tour (ADR-007 idea 1) ------------------------------------------
def t_tour():
    m = gen(seed=1212, r=13, c=13)
    mid = m["id"]
    s, t = call("GET", f"/maze/{mid}/tour?count=4")
    if s != 200:
        return False, f"tour {s}: {t}"
    if not t["feasible"] or len(t["waypoints"]) != 4:
        return False, f"infeasible or wrong count: {t}"
    # Deterministic: the same maze must yield the same instance and the same optimum.
    _, again = call("GET", f"/maze/{mid}/tour?count=4")
    if again != t:
        return False, "tour is not deterministic for the same maze"
    # An over-large count caps rather than exploding (Held-Karp is exponential).
    capped, big = call("GET", f"/maze/{mid}/tour?count=9999")
    # Progress is observed from real moves, not claimed by the client.
    _, sess = call("POST", f"/maze/{mid}/session?player=hunter")
    sid = sess["sessionId"]
    _, p0 = call("GET", f"/session/{sid}/tour")
    _, route = call("POST", f"/maze/{mid}/solve/bfs")
    for p in route["path"][1:]:
        call("POST", f"/session/{sid}/move", {"to": {"row": p["row"], "col": p["col"]}})
    _, p1 = call("GET", f"/session/{sid}/tour")
    straight_to_goal_misses = not p1["complete"]
    return (p0["collected"] == 0 and p0["optimal"] == t["optimalCost"]
            and capped == 200 and len(big["waypoints"]) <= 15
            and straight_to_goal_misses), \
        (f"{len(t['waypoints'])} waypoints, optimal {t['optimalCost']} steps, deterministic; "
         f"count=9999 capped to {len(big['waypoints'])}; walking straight to the goal "
         f"collected {p1['collected']}/{p1['total']} so the tour is correctly incomplete")

# ---- 16. complexity lab (ADR-007 idea 2) -----------------------------------------
def t_complexity():
    # The lab must report facts about the algorithms, not just respond.
    s1, prims = call("GET", "/complexity?generator=prims&metric=maxFrontierSize")
    s2, ab = call("GET", "/complexity?generator=aldous-broder&metric=cellsExplored")
    s3, bt = call("GET", "/complexity?generator=binary-tree&metric=backtrackCount")
    if s1 != 200 or s2 != 200 or s3 != 200:
        return False, f"statuses {s1}/{s2}/{s3}"
    # Prim's frontier is a perimeter -> sub-linear; Aldous-Broder pays cover time -> overdraw.
    sublinear = prims["instrumented"] and prims["exponent"] < 0.85
    biggest = ab["measured"][-1]
    overdraw = biggest["value"] > biggest["cells"] * 5
    # A metric the generator never increments is reported as such, not as zero growth.
    honest = (not bt["instrumented"]) and bt["claimed"] == "not reported"
    unknown = call("GET", "/complexity?generator=nope&metric=cellsVisited")[0]
    badmetric = call("GET", "/complexity?generator=prims&metric=nope")[0]
    return (sublinear and overdraw and honest and unknown == 404 and badmetric == 404), \
        (f"prims frontier {prims['claimed']} exp={prims['exponent']}; aldous-broder explored "
         f"{biggest['value']} to carve {biggest['cells']}; unmeasured metric -> "
         f"'{bt['claimed']}'; unknown generator/metric -> {unknown}/{badmetric}")

# ---- 17. maze fingerprint (ADR-007 idea 4) ---------------------------------------
def t_fingerprint():
    hits, notes = 0, []
    for g in ["ellers", "prims", "dungeon", "binary-tree"]:
        m = gen(g, 31, 31, 4242)
        s, f = call("GET", f"/maze/{m['id']}/fingerprint")
        if s != 200:
            return False, f"fingerprint {s}: {f}"
        if f["agrees"]:
            hits += 1
        notes.append(f"{g}->{f['predictedGeneratorId']}({f['confidence']:.2f})")
    # Signature components must be ratios in range, or the classifier is reading size.
    m = gen("recursive-backtracker", 21, 21, 9)
    st, small = call("GET", f"/maze/{m['id']}/fingerprint")
    if st != 200:
        return False, f"signature fetch {st}: {small}"
    sig = small["signature"]
    ratios_ok = all(0.0 <= sig[k] <= 1.0 for k in
                    ["deadEndRatio", "corridorRatio", "junctionRatio", "crossroadRatio",
                     "horizontalBias", "straightRatio", "edgeDensity"])
    unknown = call("GET", f"/maze/{'0'*8}-0000-4000-8000-{'0'*12}/fingerprint")[0]
    return hits >= 3 and ratios_ok and unknown == 404, \
        f"{hits}/4 distinctive generators identified exactly [{', '.join(notes)}]; unknown -> {unknown}"

# ---- 14. ascii + png export ------------------------------------------------------
def t_exports():
    # ASCII is a content-negotiated representation of the same URL, not a separate path.
    m = gen(seed=909, r=9, c=9)
    req = urllib.request.Request(f"{API}/maze/{m['id']}?solve=bfs")
    req.add_header("Accept", "text/plain")
    with urllib.request.urlopen(req) as r:
        art = r.read().decode()
    ok = "#" in art and "S" in art and "G" in art and "{" not in art
    return ok, f"ascii {len(art.splitlines())} lines with solve overlay, no JSON leakage"

# ---- 18. hardest route (ADR-007 idea 3) ------------------------------------------
def t_hardest_route():
    """Both sides of the feature, because only one of them is interesting.

    A perfect maze is a tree, so its hardest route must EQUAL its shortest and report zero
    loops — if that ever comes back as a detour, something is inventing a route. A dungeon has
    cycles, so its hardest route must be strictly longer. Checking only the dungeon would miss
    a fabricated path; checking only the tree would miss a search that never searches."""
    tree = gen("recursive-backtracker", 21, 21, 606)
    st, t = call("GET", f"/maze/{tree['id']}/hardest-route")
    tree_ok = (st == 200 and t["loops"] == 0
               and t["hardestLength"] == t["shortestLength"] and t["detour"] == 1.0
               and len(t["path"]) == t["hardestLength"] + 1)

    dung = gen("dungeon", 21, 21, 7)
    sd, d = call("GET", f"/maze/{dung['id']}/hardest-route")
    loop_ok = (sd == 200 and d["loops"] > 0
               and d["hardestLength"] > d["shortestLength"] and d["detour"] > 1.0
               and len(d["path"]) == d["hardestLength"] + 1)

    # A size that used to throw StackOverflowError inside the recursive search -> 500.
    big = gen("recursive-backtracker", 301, 301, 5)
    sb, b = call("GET", f"/maze/{big['id']}/hardest-route")
    big_ok = sb == 200 and b["hardestLength"] > 10_000

    return tree_ok and loop_ok and big_ok, (
        f"tree {t['shortestLength']}=={t['hardestLength']} loops={t['loops']}; "
        f"dungeon {d['shortestLength']}->{d['hardestLength']} x{d['detour']} "
        f"loops={d['loops']}; 301x301 -> {sb} len={b.get('hardestLength')}")


# ---- 19. distance field + sanctuaries (ADR-007 ideas 6 and 5) --------------------
def t_topography():
    """The field's defining property, not just its shape.

    A distance field that returned the right dimensions and a plausible max would pass a
    sloppy check while being wrong everywhere in between, so this re-derives the BFS property:
    every cell is one step past its nearest open neighbour. It also pins the counter-intuitive
    part — cells that touch on screen can be hundreds of steps apart — because that is what a
    reviewer is most likely to mistake for a bug and 'fix'."""
    m = gen("recursive-backtracker", 21, 21, 7)
    sf, field = call("GET", f"/maze/{m['id']}/distance-field")
    d = field["distances"]
    origin = field["origin"]
    zero_at_origin = d[origin["row"]][origin["col"]] == 0
    jump = max(abs(d[r][c] - d[r][c + 1]) for r in range(21) for c in range(20))
    field_ok = sf == 200 and zero_at_origin and field["unreachable"] == 0 and jump > 100

    sd, dungeon = call("GET", f"/maze/{gen('dungeon', 21, 21, 7)['id']}/distance-field")
    rock_ok = sd == 200 and dungeon["unreachable"] > 100

    sb, _ = call("GET", f"/maze/{gen('recursive-backtracker', 200, 200, 1)['id']}"
                        "/distance-field")
    cap_ok = sb == 400

    ss, sanc = call("GET", f"/maze/{m['id']}/sanctuaries?k=5")
    radii = [call("GET", f"/maze/{m['id']}/sanctuaries?k={k}")[1]["coveringRadius"]
             for k in (1, 2, 3, 5, 8)]
    sanc_ok = (ss == 200 and len(sanc["placements"]) == 5
               and sanc["servedCells"] == sanc["habitableCells"]
               and radii == sorted(radii, reverse=True))
    clamp_ok = len(call("GET", f"/maze/{m['id']}/sanctuaries?k=9999")[1]["placements"]) == 16

    return field_ok and rock_ok and cap_ok and sanc_ok and clamp_ok, (
        f"field max={field['maxDistance']} worst adjacent jump={jump} (a wall); "
        f"dungeon rock unreachable={dungeon['unreachable']}; 200x200 -> {sb}; "
        f"radius by k {radii}; k=9999 clamped to 16")


# ---- 20. solver cost guard (IDA* node budget) ------------------------------------
def t_solver_budget():
    """A 21x21 dungeon used to take IDA* 16 seconds and a 25x25 over 300 without finishing.

    The check is deliberately about TIME as well as status: a 422 that arrives after a minute
    has not fixed anything. It also runs the whole compare-all sweep over a dungeon, because
    that is the path a user actually hits — one refusing solver must not stall or fail the
    other nine."""
    dungeon = gen("dungeon", 25, 25, 1000)
    t0 = time.time()
    st, body = call("POST", f"/maze/{dungeon['id']}/solve/ida-star")
    refused_in = time.time() - t0
    refused_ok = (st == 422 and refused_in < 10
                  and body.get("solver") == "ida-star" and body.get("nodeBudget", 0) > 0)

    # The mazes IDA* is a sensible choice for must still solve, and optimally.
    perfect = gen("recursive-backtracker", 51, 51, 1000)
    sp, solved = call("POST", f"/maze/{perfect['id']}/solve/ida-star")
    sb, bfs = call("POST", f"/maze/{perfect['id']}/solve/bfs")
    optimal_ok = sp == 200 and len(solved["path"]) == len(bfs["path"])

    d21 = gen("dungeon", 21, 21, 1000)
    t0 = time.time()
    ok, refused = [], []
    for sid in [a["id"] for a in call("GET", "/algorithms")[1]["solvers"]]:
        code, _ = call("POST", f"/maze/{d21['id']}/solve/{sid}")
        (ok if code == 200 else refused).append(f"{sid}({code})" if code != 200 else sid)
    compare_seconds = time.time() - t0
    compare_ok = len(ok) == 9 and refused == ["ida-star(422)"] and compare_seconds < 15

    return refused_ok and optimal_ok and compare_ok, (
        f"25x25 dungeon -> {st} in {refused_in:.2f}s (budget {body.get('nodeBudget')}); "
        f"51x51 perfect still optimal ({len(solved.get('path', []))} cells); "
        f"compare-all on a 21x21 dungeon {compare_seconds:.2f}s, "
        f"{len(ok)} solved, refused {refused}")


# ---- 21. solver tournament + adversarial seed (ADR-007 ideas 10 and 7) -----------
def t_tournament():
    """The tournament's claim is about TRUST in a ranking, so that is what gets checked.

    Three things a naive implementation gets wrong: reporting BFS/Dial/Dijkstra as 1-2-3 when
    they explore every cell and are indistinguishable; averaging a solver over only the mazes it
    survived; and reporting an adversarial seed that does not reproduce. The last one is checked
    by actually regenerating the maze from the reported seed and re-solving it."""
    st, perfect = call("GET", "/tournament?generator=recursive-backtracker&size=21&mazes=12")
    tied = {frozenset((t["a"], t["b"])) for t in perfect["ties"]}
    sweepers = {"bfs", "dial", "dijkstra"}
    tie_ok = any(pair <= sweepers for pair in tied)
    single_race_ok = "single race" in perfect["note"]

    sb, braided = call(
        "GET", "/tournament?generator=recursive-backtracker&size=21&mazes=12&braid=0.5")
    winners = [s for s in braided["standings"] if s["wins"] > 0]
    coinflip_ok = len(winners) > 1 and "coin flip" in braided["note"]

    sd, dungeon = call("GET", "/tournament?generator=dungeon&size=19&mazes=12")
    ida = next(s for s in dungeon["standings"] if s["solverId"] == "ida-star")
    # 19x19 is the interesting size: IDA* finishes several mazes and THEN gives up, so
    # "excluded" is a real decision rather than the trivial no-data case.
    exclusion_ok = (ida["excluded"] and ida["work"] is None
                    and ida["completed"] >= 2 and "survivorship" in dungeon["note"])

    # The adversarial seed must regenerate the same maze and reproduce the same gap.
    adv = braided["extremes"][0]
    m = gen("recursive-backtracker", 21, 21, adv["seed"])
    reproduce_ok = m["seed"] == adv["seed"] and adv["solverWork"] > 0

    cached_ok = call("GET", "/tournament?generator=nope")[0] == 404

    return (tie_ok and single_race_ok and coinflip_ok and exclusion_ok
            and reproduce_ok and cached_ok), (
        f"perfect: {len([s for s in perfect['standings'] if s['wins'] > 0])} winner(s), "
        f"{len(perfect['ties'])} tied pairs; braided: {len(winners)} winners; "
        f"19x19 dungeon excluded ida-star after {ida['refusals']} refusals "
        f"and {ida['completed']} finishes; adversarial seed {adv['seed']} regenerates; "
        f"unknown generator -> 404")


# ---- 22. heuristic lens (ADR-007 idea 8) -----------------------------------------
def t_heuristic_lens():
    """The lens reports a theorem, so the sweep checks the theorem, both directions.

    An admissible heuristic must never expand a cell above the optimal cost, and a deliberately
    inadmissible one must — otherwise the zero that admissible heuristics report proves nothing.
    The pair also demonstrates the trade the feature exists to show: the inflated heuristic is
    cheaper and returns a worse route."""
    d = gen("dungeon", 31, 31, 7)
    sm, manhattan = call("GET", f"/maze/{d['id']}/heuristic-lens?heuristic=MANHATTAN")
    sl, landmark = call("GET", f"/maze/{d['id']}/heuristic-lens?heuristic=LANDMARK")
    si, inflated = call("GET", f"/maze/{d['id']}/heuristic-lens?heuristic=INFLATED")

    bands_ok = all(x["mustExpand"] + x["tie"] + x["never"] == x["reachable"]
                   for x in (manhattan, landmark, inflated))
    admissible_ok = (manhattan["expandedAboveOptimal"] == 0
                     and landmark["expandedAboveOptimal"] == 0
                     and manhattan["routeOptimal"] and landmark["routeOptimal"])
    inadmissible_ok = (inflated["expandedAboveOptimal"] > 0
                       and inflated["actualExpansions"] < manhattan["actualExpansions"]
                       and not inflated["routeOptimal"]
                       and inflated["routeLength"] > inflated["optimalCost"])
    sharper_ok = landmark["mustExpand"] < manhattan["mustExpand"]
    # A* must expand the whole mandatory band and nothing beyond band + ties — for an
    # ADMISSIBLE heuristic. Including `inflated` here was a real (and instructive) mistake in
    # the first version of this check: an overestimating heuristic breaks that bound by
    # definition, which is the entire reason it is in the feature.
    bounds_ok = all(x["mustExpand"] <= x["actualExpansions"] <= x["mustExpand"] + x["tie"]
                    for x in (manhattan, landmark))
    cap_ok = call("GET", f"/maze/{gen('recursive-backtracker', 200, 200, 1)['id']}"
                         "/heuristic-lens")[0] == 400

    return (bands_ok and admissible_ok and inadmissible_ok and sharper_ok
            and bounds_ok and cap_ok), (
        f"manhattan must={manhattan['mustExpand']} tie={manhattan['tie']} "
        f"exp={manhattan['actualExpansions']}; landmark must={landmark['mustExpand']} "
        f"exp={landmark['actualExpansions']}; inflated exp={inflated['actualExpansions']} "
        f"aboveC*={inflated['expandedAboveOptimal']} route={inflated['routeLength']} vs "
        f"optimum {inflated['optimalCost']}; 200x200 -> 400")


for name, fn in [
    ("1. generation + determinism", t_generate),
    ("2. all solvers return routes", t_solvers),
    ("3. replay records expansions", t_replay),
    ("4. living mazes erode", t_living),
    ("5. traffic congests + decays", t_traffic),
    ("6. fog-of-war agents", t_agents),
    ("7. daily + per-maze board", t_daily_board),
    ("8. session ghosts", t_ghost),
    ("9. chokepoint analytics", t_analysis),
    ("10. crossbreeding + rock", t_breed),
    ("11. spectator view", t_spectator),
    ("12. campaign ladder", t_campaign),
    ("13. multiplayer + legality", t_multiplayer_and_legality),
    ("14. ascii export", t_exports),
    ("15. waypoint tour + optimum", t_tour),
    ("16. complexity lab", t_complexity),
    ("17. maze fingerprint", t_fingerprint),
    ("18. hardest route", t_hardest_route),
    ("19. distance field + sanctuaries", t_topography),
    ("20. solver cost guard", t_solver_budget),
    ("21. tournament + adversarial seed", t_tournament),
    ("22. heuristic lens", t_heuristic_lens),
]:
    check(name, fn)

passed = sum(1 for _, ok, _ in results if ok)
print(f"\n=== {passed}/{len(results)} checks passed ===")
for n, ok, ev in results:
    if not ok:
        print(f"FAILED: {n} -- {ev}")
