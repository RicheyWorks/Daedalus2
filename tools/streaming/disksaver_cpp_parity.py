# SPDX-License-Identifier: MIT
"""Golden outputs for the C++17 ports of the DiskSaver minigame cores (G573 batch 1, G574 batch 2, G575 batch 3).

Each game's Python tool lays out the puzzle (its seeded layout stays in Python: the C++ side
never reimplements Python's random) and then plays a fixed set of move lists through the real
play() path. The layout, the par plan and every result or refusal go into
engines/unreal/core-test/disksaver_<game>_parity.txt, and the header-only
DaedalusDiskSaver<Game>Core.h ports replay every line in disksaver_<game>_core_test.cpp.

Batch 1: G556 Manifest Match, G557 Twin Pilots, G558 Quayside Shove, G559 Sack Chute.
Batch 2: G560 Seal Roll, G561 Channel Dash, G562 Boom Defence, G563 Salvage Sale.
Batch 3: G564 Rope Run, G565 Belfry Changes, G566 Tram Shunt.
Cases cover the real tools/world_census fixtures (several seeds), synthetic censuses, and
hand-laid edge layouts (unsolvable, stuck, disconnected) injected through the tool's own
play() by swapping its layout function for one call.

  python tools/streaming/disksaver_cpp_parity.py            # print every file
  python tools/streaming/disksaver_cpp_parity.py --check    # exit 1 if a checked-in file is stale
  python tools/streaming/disksaver_cpp_parity.py --write    # rewrite the checked-in files
"""
import json
import os
import subprocess
import sys
import tempfile
from collections import deque
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import belfry_changes as bc  # noqa: E402
import boom_defence as bd  # noqa: E402
import census_budget as cb  # noqa: E402
import channel_dash as cd  # noqa: E402
import manifest_match as mm  # noqa: E402
import quayside_shove as qs  # noqa: E402
import rope_run as rr  # noqa: E402
import sack_chute as sc  # noqa: E402
import salvage_sale as ss  # noqa: E402
import seal_roll as sr  # noqa: E402
import tram_shunt as ts  # noqa: E402
import twin_pilots as tp  # noqa: E402

ROOT = cb.ROOT
CORE_TEST = os.path.join(ROOT, "engines", "unreal", "core-test")
FIX = os.path.join(ROOT, "tools", "world_census", "fixtures")
SEEDS = (0, 1, 7, 42)


def real_census():
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, "c")
        subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(FIX, "alpha.json"),
                        os.path.join(FIX, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                        os.path.join(FIX, "bindings.json"), "--output-dir", out], cwd=ROOT, check=True,
                       capture_output=True)
        with open(os.path.join(out, "census.json"), encoding="utf-8") as f:
            return json.load(f)


def census(worlds):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": "2026-10-29",
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]}
                       for w, isl in worlds]}


SYN = {
    "syn5": census([("north", [(1, 3), (2, 40), (5, 7)]), ("south", [(0, 12), (3, 90)])]),
    "syn6": census([("a", [(0, 1), (1, 2), (2, 3)]), ("b", [(0, 4), (1, 5)]), ("c", [(9, 600)])]),
    "syn8": census([("east", [(i, 10 * i + 1) for i in range(5)]), ("west", [(i, 7 * i) for i in range(3)])]),
    "syn14": census([("big", [(i, (i * 37) % 101) for i in range(14)])]),
}


def censuses():
    yield "real", real_census()
    for k, v in SYN.items():
        yield k, v


@contextmanager
def patched(mod, name, fn):
    old = getattr(mod, name)
    setattr(mod, name, fn)
    try:
        yield
    finally:
        setattr(mod, name, old)


def run(fn, kinds):
    try:
        return True, fn()
    except ValueError as e:
        msg = str(e)
        for needle, kind in kinds:
            if needle in msg:
                return False, kind
        raise


def lst(xs, sep=","):
    xs = [str(x) for x in xs]
    return sep.join(xs) if xs else "-"


# ---------------------------------------------------------------- G556 Manifest Match
MM_KINDS = [("not on the table", "range"), ("already matched", "matched"), ("two different", "same"),
            ("already over", "over")]


def mm_cases():
    for cname, doc in censuses():
        if cname == "syn8":
            continue
        for s in SEEDS[:3] if cname == "real" else SEEDS[1:3]:
            yield f"{cname}_seed{s}", doc, s, None
    yield "hand_two_pairs", None, 0, [("x", "ISLAND x"), ("y", "ISLAND y"), ("x", "M x"), ("y", "M y")]
    yield "hand_adjacent", None, 0, [("x", "ISLAND x"), ("x", "M x"), ("y", "ISLAND y"), ("y", "M y")]


def mm_naive(ids):
    n, matched, out = len(ids), set(), []
    while len(matched) < n and len(out) < 200:
        free = [p for p in range(n) if p not in matched]
        a = free[0]
        for b in free[1:]:
            out.append((a + 1, b + 1))
            if ids[a] == ids[b]:
                matched.update((a, b))
                break
    return out


def mm_lines():
    out = ["# disksaver manifest_match parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    for cname, doc, seed, hand in mm_cases():
        doc = doc or SYN["syn5"]
        ctx = patched(mm, "layout", lambda d, s=0, h=hand: list(h)) if hand else patched(mm, "FORMAT", mm.FORMAT)
        with ctx:
            cards = mm.layout(doc, seed)
            labels = sorted({p for p, _ in cards})
            ids = [labels.index(p) for p, _ in cards]
            par, best = mm.perfect_turns(cards)
            plan = [(a + 1, b + 1) for a, b in best]
            out.append(f"C {cname}")
            out.append(f"L {lst(ids)}")
            out.append(f"P {par} {lst(f'{a}-{b}' for a, b in plan)}")
            n = len(cards)
            tries = [plan, [], plan[:len(plan) // 2], plan + [(1, 2)], mm_naive(ids),
                     [(0, 1)], [(1, n + 1)], [(2, 2)], plan[:1] + plan[:1], list(reversed(plan))]
            for turns in tries:
                ok, r = run(lambda t=turns: mm.play(doc, seed, turns=list(t)), MM_KINDS)
                t = lst(f"{a}-{b}" for a, b in turns)
                if ok:
                    hits = "".join("1" if x["match"] else "0" for x in r["turns"]) or "-"
                    out.append(f"T {t} ok {r['matched_pairs']} {hits} {r['verdict']}")
                else:
                    out.append(f"T {t} err {r}")
    return out


# ---------------------------------------------------------------- G557 Twin Pilots
TP_KINDS = [("no such berth", "berth"), ("no channel", "channel"), ("not connected", "disconnected")]


def tp_walk(n, edges):
    adj = tp.adjacency(n, edges)

    def path(a, b):
        prev, q = {a: None}, deque([a])
        while q:
            x = q.popleft()
            for y in adj[x]:
                if y not in prev:
                    prev[y] = x
                    q.append(y)
        p = []
        while b != a:
            p.append(b)
            b = prev[b]
        return p[::-1]
    at, route = 0, []
    for t in list(range(1, n)) + [0]:
        route += path(at, t)
        at = t
    return route


def tp_lines():
    out = ["# disksaver twin_pilots parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        if cname == "syn14":
            continue
        for s in (SEEDS[:3] if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    cases.append(("hand_line", None, 0, (["harbour", "p", "q"], [(0, 1), (1, 2)])))
    cases.append(("hand_star", None, 0, (["harbour", "p", "q", "r"], [(0, 1), (0, 2), (0, 3)])))
    cases.append(("hand_disconnected", None, 0, (["harbour", "p", "q"], [(0, 1)])))
    for cname, doc, seed, hand in cases:
        doc = doc or SYN["syn5"]
        ctx = patched(tp, "chart", lambda d, s=0, h=hand: (list(h[0]), sorted(h[1]))) if hand else \
            patched(tp, "FORMAT", tp.FORMAT)
        with ctx:
            nodes, edges = tp.chart(doc, seed)
            n = len(nodes)
            out.append(f"C {cname}")
            out.append(f"L {n} {lst(f'{a}-{b}' for a, b in edges)}")
            ok, r = run(lambda: tp.play(doc, seed, auto=True), TP_KINDS)
            if not ok:
                out.append(f"P err {r}")
                continue
            ra = [nodes.index(x) for x in r["routes"][0]]
            rb = [nodes.index(x) for x in r["routes"][1]]
            out.append(f"P {r['par']} {r['solo_bells']} {lst(ra, '.')} {lst(rb, '.')}")
            adj = tp.adjacency(n, edges)
            far = [x for x in range(1, n) if x not in adj[0]]
            tries = [(ra, rb), ([], []), (ra, []), (tp_walk(n, edges), []), ([], tp_walk(n, edges)),
                     (ra + [adj[0][1]], rb), (ra + [0, 0], rb), (rb, ra)]
            if far:
                tries.append(([far[0]], []))
                tries.append((ra, [far[-1]]))
            tries.append(([n], [far[0]] if far else []))
            for a, b in tries:
                names = lambda rt: ">".join(nodes[x] if x < n else "nowhere" for x in rt)
                ok, g = run(lambda a=a, b=b: tp.play(doc, seed, plan=names(a) + ";" + names(b)), TP_KINDS)
                head = f"T {lst(a, '.')} {lst(b, '.')}"
                if ok:
                    out.append(f"{head} ok {g['bells']} {len(g['missed'])} {int(g['home'])} {g['verdict']}")
                else:
                    out.append(f"{head} err {g}")
    return out


# ---------------------------------------------------------------- G558 Quayside Shove
QS_KINDS = [("is not U", "letter"), ("already clear", "clear"), ("is blocked", "blocked")]


def qs_grid(y):
    rows = qs.draw(y["walls"], y["marks"], y["player"], y["crates"])
    return "/".join(r.ljust(qs.SIZE).replace(" ", "_") for r in rows)


def qs_hand(rows):
    walls, marks, crates, player = set(), set(), set(), None
    for r, row in enumerate(rows):
        for c, ch in enumerate(row.ljust(qs.SIZE)):
            p = (r, c)
            if ch == "#":
                walls.add(p)
            if ch in ".+*":
                marks.add(p)
            if ch in "$*":
                crates.add(p)
            if ch in "@+":
                player = p
    par, plan = qs.solve(frozenset(walls), frozenset(marks), player, frozenset(crates))
    return {"labels": ["hand"], "walls": frozenset(walls), "marks": frozenset(marks), "player": player,
            "crates": frozenset(crates), "par": par, "plan": plan}


QS_HAND = {
    "hand_corner_dead": ["#######", "#$    #", "#     #", "#  .@ #", "#     #", "#     #", "#######"],
    "hand_one_push": ["#######", "#     #", "#     #", "# @$. #", "#     #", "#     #", "#######"],
}


def qs_lines():
    out = ["# disksaver quayside_shove parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    for k, rows in QS_HAND.items():
        cases.append((k, SYN["syn5"], 0, qs_hand(rows)))
    for cname, doc, seed, hand in cases:
        ctx = patched(qs, "yard", lambda d, s=0, h=hand: h) if hand else patched(qs, "FORMAT", qs.FORMAT)
        with ctx:
            y = qs.yard(doc, seed)
            out.append(f"C {cname}")
            out.append(f"L {qs_grid(y)}")
            par = -1 if y["par"] is None else y["par"]
            plan = y["plan"] or ""
            out.append(f"P {par} {plan or '-'}")
            tries = [plan, "", plan[:-1], plan + "U", "X", "UUUUUU", "DDDDDD", "LLLLLL", "RRRRRR",
                     "LRLR" + plan, plan[::-1]]
            for d in "UDLR":
                if qs.move(y["walls"], y["player"], y["crates"], d) is None:
                    tries.append(d)
                    break
            for mv in tries:
                ok, r = run(lambda m=mv: qs.play(doc, seed, moves=m), QS_KINDS)
                if ok:
                    out.append(f"T {mv or '-'} ok {r['steps']} {r['pushes']} {r['on_marks']} {r['verdict']} "
                               f"{int(r['deadlocked'])}")
                else:
                    out.append(f"T {mv or '-'} err {r}")
    return out


# ---------------------------------------------------------------- G559 Sack Chute
SC_KINDS = [("no bin", "bin"), ("already clear", "clear"), ("is empty", "empty")]


def sc_greedy_moves(s):
    s, out = tuple(s), []
    while any(s):
        i = max(j for j, k in enumerate(s) if k)
        s = sc.sow(s, i)[0]
        out.append(i + 1)
    return out


def sc_lines():
    out = ["# disksaver sack_chute parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        if cname in ("syn8", "syn14"):
            continue
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    for k, sacks in {"hand_one_heap": (12, 0, 0, 0), "hand_last_bin": (0, 0, 0, 1),
                     "hand_six_ones": (1, 1, 1, 1, 1, 1), "hand_wrap": (0, 9, 0, 3)}.items():
        cases.append((k, SYN["syn5"], 0, (["b"] * len(sacks), sacks)))
    for cname, doc, seed, hand in cases:
        ctx = patched(sc, "chute", lambda d, s=0, h=hand: (list(h[0]), tuple(h[1]))) if hand else \
            patched(sc, "FORMAT", sc.FORMAT)
        with ctx:
            labels, sacks = sc.chute(doc, seed)
            par, plan = sc.solve(sacks)
            n = len(sacks)
            out.append(f"C {cname}")
            out.append(f"L {lst(sacks)}")
            out.append(f"P {par} {sc.greedy(sacks)} {lst(i + 1 for i in plan)}")
            p1 = [i + 1 for i in plan]
            g = sc_greedy_moves(sacks)
            empty = next((i + 1 for i in range(n) if sacks[i] == 0), None)
            tries = [p1, [], p1[:-1], p1 + [1], g, [0], [n + 1], [1] * 3, list(range(1, n + 1))]
            if empty:
                tries.append([empty])
            for mv in tries:
                ok, r = run(lambda m=mv: sc.play(doc, seed, moves=",".join(str(x) for x in m)), SC_KINDS)
                if ok:
                    out.append(f"T {lst(mv)} ok {r['in_hold']} {lst(r['left'])} {r['verdict']}")
                else:
                    out.append(f"T {lst(mv)} err {r}")
    return out



# ---------------------------------------------------------------- G560 Seal Roll
SR_KINDS = [("is not N", "letter"), ("runs into a wall", "wall")]


def rc(p):
    return f"{p[0]}.{p[1]}"


def sr_layout(q):
    rows = "/".join("".join("#" if (r, c) in q["walls"] else "_" for c in range(sr.SIZE)) for r in range(sr.SIZE))
    return f"L {rows} {lst(rc(m) for m in q['marks'])} {rc(q['dock'])} {rc(q['start'])}"


def sr_hand(marks, dock, start, extra_walls=()):
    border = {(r, c) for r in range(sr.SIZE) for c in range(sr.SIZE) if r in (0, sr.SIZE - 1) or c in (0, sr.SIZE - 1)}
    walls = frozenset(border | set(extra_walls))
    par, plan = sr.solve(walls, tuple(marks), dock, start)
    return {"labels": ["h"] * len(marks), "walls": walls, "marks": tuple(marks), "dock": dock, "start": start,
            "par": par, "plan": plan}


def sr_lines():
    out = ["# disksaver seal_roll parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    cases.append(("hand_mark_under_start", SYN["syn5"], 0, sr_hand([(3, 3)], (3, 5), (3, 3))))
    cases.append(("hand_dock_walled_off", SYN["syn5"], 0,
                  sr_hand([(2, 2)], (5, 5), (2, 3), extra_walls=[(4, 5), (5, 4), (4, 4)])))
    for cname, doc, seed, hand in cases:
        ctx = patched(sr, "quay", lambda d, s=0, h=hand: h) if hand else patched(sr, "FORMAT", sr.FORMAT)
        with ctx:
            q = sr.quay(doc, seed)
            out.append(f"C {cname}")
            out.append(sr_layout(q))
            plan = q["plan"] or ""
            out.append(f"P {-1 if q['par'] is None else q['par']} {plan or '-'}")
            tries = [plan, "", plan[:-1], plan + "N", plan + "NS", "X", "NNNN", "SSSS", "EEEE", "WWWW",
                     "NESW" * 3, plan[::-1], plan + "EW" * 2]
            for t in tries:
                ok, r = run(lambda m=t: sr.play(doc, seed, tips=m), SR_KINDS)
                if ok:
                    out.append(f"T {t or '-'} ok {r['count']} {''.join(r['stamped']) or '-'} {r['seal']} "
                               f"{int(r['on_dock'])} {r['verdict']}")
                else:
                    out.append(f"T {t or '-'} err {r}")
    return out


# ---------------------------------------------------------------- G561 Channel Dash
CD_KINDS = [("is not U", "letter"), ("already on the dock", "dock"), ("leaves the channel", "leaves")]


def cd_layout(lanes, dock, start):
    ls = ",".join("".join("1" if c in cells else "0" for c in range(cd.WIDTH)) + ":" + str(v) for cells, v in lanes)
    return f"L {ls or '-'} {dock} {start}"


def cd_lines():
    out = ["# disksaver channel_dash parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    hands = {
        "hand_no_lanes": ([], 4, 2),
        "hand_wall_of_barges": ([(frozenset(range(9)), 1), (frozenset({0}), -1)], 0, 8),
        "hand_fast_lanes": ([(frozenset({0, 1, 2, 3, 4, 5}), 2), (frozenset({3, 4, 5}), -2), (frozenset({8}), -1)], 8, 0),
    }
    for k, h in hands.items():
        cases.append((k, SYN["syn5"], 0, h))
    for cname, doc, seed, hand in cases:
        ctx = patched(cd, "lanes_for", lambda d, s=0, h=hand: (["h"] * len(h[0]), list(h[0]), h[1], h[2])) if hand \
            else patched(cd, "FORMAT", cd.FORMAT)
        with ctx:
            labels, lanes, dock, start = cd.lanes_for(doc, seed)
            par, plan = cd.solve(lanes, dock, start)
            out.append(f"C {cname}")
            out.append(cd_layout(lanes, dock, start))
            plan = plan or ""
            out.append(f"P {-1 if par is None else par} {plan or '-'}")
            tries = [plan, "", plan[:-1], plan + ".", "X", "U" * 7, "." * 9 + plan, "D", "L" * 10, "R" * 10,
                     ("." + plan[1:]) if plan else ".", "U.U.U.U.U.U.", plan[::-1]]
            for t in tries:
                ok, r = run(lambda m=t: cd.play(doc, seed, moves=m), CD_KINDS)
                if ok:
                    out.append(f"T {t or '-'} ok {r['ticks']} {r['hit_tick'] or 0} {r['row']} {r['col']} {r['verdict']}")
                else:
                    out.append(f"T {t or '-'} err {r}")
    return out


# ---------------------------------------------------------------- G562 Boom Defence
BD_KINDS = [("no post site", "site"), ("named twice", "twice"), ("only ", "many")]


def bd_lines():
    out = ["# disksaver boom_defence parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        if cname == "syn14":
            continue
        for s in (SEEDS[:3] if cname == "real" else SEEDS[1:2]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    line = [(3, c) for c in range(bd.COLS)]
    cases.append(("hand_no_sites", SYN["syn5"], 0, {"skiffs": ["a", "b"], "hulls": [4, 5], "path": line, "sites": []}))
    cases.append(("hand_one_site", SYN["syn5"], 0,
                  {"skiffs": ["a", "b", "c"], "hulls": [1, 4, 2], "path": line, "sites": [(2, 4)]}))
    cases.append(("hand_two_sites", SYN["syn5"], 0,
                  {"skiffs": ["a"], "hulls": [2], "path": line, "sites": [(2, 1), (4, 7)]}))
    for cname, doc, seed, hand in cases:
        ctx = patched(bd, "chart", lambda d, s=0, h=hand: h) if hand else patched(bd, "FORMAT", bd.FORMAT)
        with ctx:
            c = bd.chart(doc, seed)
            par, combo = bd.best(c)
            gt, gp = bd.greedy(c)
            L = "ABCDEFGHIJKL"
            out.append(f"C {cname}")
            out.append(f"L {lst(rc(p) for p in c['path'])} {lst(rc(p) for p in c['sites'])} {lst(c['hulls'])}")
            out.append(f"P {par} {''.join(L[i] for i in combo) or '-'} {gt} {''.join(L[i] for i in gp) or '-'}")
            k = len(c["sites"])
            tries = [""] if not k else [",".join(L[i] for i in combo), "", ",".join(L[i] for i in gp), "A", "A,A", "A,B,C", "Z",
                     "a,b", L[k - 1] if k else "B", f"{L[k - 1]},A" if k > 1 else "AB", "AA"]
            for t in tries:
                ok, r = run(lambda m=t: bd.play(doc, seed, posts=m), BD_KINDS)
                if ok:
                    fates = "".join("t" if r["fates"][s] == "through" else "s" for s in c["skiffs"])
                    out.append(f"T {t or '-'} ok {r['through']} {fates} {r['verdict']}")
                else:
                    out.append(f"T {t or '-'} err {r}")
    return out


# ---------------------------------------------------------------- G563 Salvage Sale
SS_KINDS = [("whole-number bids", "count"), ("coin left", "coin")]


def ss_greedy_bids(values, coin):
    mine, theirs, lost, out = coin, coin, 0, []
    for v in values:
        rb = ss.broker_bid(v, theirs, lost)
        if rb + 1 <= mine:
            mine -= rb + 1
            lost += 1
            out.append(rb + 1)
        else:
            theirs -= rb
            out.append(0)
    return out


def ss_lines():
    out = ["# disksaver salvage_sale parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    for k, h in {"hand_no_coin": ([3, 4, 5, 6, 7], 0), "hand_rich": ([9, 9, 9, 9, 9], 40),
                 "hand_six_lots": ([3, 12, 5, 7, 4, 11], 14)}.items():
        cases.append((k, SYN["syn5"], 0, h))
    for cname, doc, seed, hand in cases:
        ctx = patched(ss, "sale", lambda d, s=0, h=hand: (["h"] * len(h[0]), list(h[0]), h[1])) if hand else \
            patched(ss, "FORMAT", ss.FORMAT)
        with ctx:
            lots, values, coin = ss.sale(doc, seed)
            par, plan = ss.solve(values, coin)
            n = len(values)
            out.append(f"C {cname}")
            out.append(f"L {lst(values)} {coin}")
            out.append(f"P {par} {lst(plan)} {ss.greedy(values, coin)}")
            g = ss_greedy_bids(values, coin)
            tries = [plan, g, [0] * n, [coin] * n, [999] + [0] * (n - 1), plan[:-1], plan + [0],
                     [v // 2 + 1 for v in values], [1] * n]
            raw = [",".join(str(x) for x in t) for t in tries] + ["", "x," * (n - 1) + "1", "007" + ",0" * (n - 1)]
            for t in raw:
                ok, r = run(lambda m=t: ss.play(doc, seed, bids=m), SS_KINDS)
                if ok:
                    won = "".join("y" if e["winner"] == "you" else "b" for e in r["log"])
                    out.append(f"T {t or '-'} ok {r['score']} {won} {r['verdict']}")
                else:
                    out.append(f"T {t or '-'} err {r}")
    return out


# ---------------------------------------------------------------- G564 Rope Run
RR_KINDS = [("is not N", "letter"), ("already on the dock", "dock"), ("runs off the quay", "off"),
            ("cross itself", "cross")]


def rr_layout(q):
    rows = "/".join("".join(str(q["grip"][(r, c)]) if (r, c) in q["grip"] else "#" for c in range(rr.COLS))
                    for r in range(rr.ROWS))
    return f"L {rows} {rc(q['start'])} {rc(q['dock'])}"


def rr_greedy_route(q):
    open_cells, cell, seen, out = set(q["grip"]), q["start"], {q["start"]}, ""
    while cell != q["dock"]:
        opts = [(q["grip"][n], -"NSEW".index(d), n, d) for d, n in rr.neighbours(cell, open_cells) if n not in seen]
        if not opts:
            break
        _, _, cell, d = max(opts)
        seen.add(cell)
        out += d
    return out


def rr_hand(rows, start, dock):
    grip = {(r, c): int(ch) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != "#"}
    par, route = rr.solve(grip, start, dock)
    return {"labels": ["h"], "cleats": [], "crates": {(r, c) for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == "#"},
            "grip": grip, "start": start, "dock": dock, "par": par, "route": route}


def rr_lines():
    out = ["# disksaver rope_run parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    cases.append(("hand_dock_boxed_in", SYN["syn5"], 0, rr_hand(["111111", "111111", "1111#1", "111#1#", "1111#1"], (0, 0), (3, 4))))
    cases.append(("hand_next_door", SYN["syn5"], 0, rr_hand(["511111", "141111", "111111", "111111", "111115"], (0, 0), (0, 1))))
    for cname, doc, seed, hand in cases:
        ctx = patched(rr, "quay", lambda d, s=0, h=hand: h) if hand else patched(rr, "FORMAT", rr.FORMAT)
        with ctx:
            q = rr.quay(doc, seed)
            route = q["route"] or ""
            out.append(f"C {cname}")
            out.append(rr_layout(q))
            out.append(f"P {-1 if q['par'] is None else q['par']} {route or '-'} {rr.greedy(q['grip'], q['start'], q['dock'])}")
            tries = [route, "", route[:-1], route + "N", "X", "NNNNN", "SSSSS", "EEEEEE", "WWWWWW", "NS", "EW",
                     route[::-1], rr_greedy_route(q), "ESWN" * 2]
            for t in tries:
                ok, r = run(lambda m=t: rr.play(doc, seed, route=m), RR_KINDS)
                if ok:
                    out.append(f"T {t or '-'} ok {r['grip']} {int(r['on_dock'])} {r['verdict']}")
                else:
                    out.append(f"T {t or '-'} err {r}")
    return out


# ---------------------------------------------------------------- G565 Belfry Changes
BC_KINDS = [("is not places", "format"), ("places run", "range"), ("pairs overlap", "overlap"), ("must rest", "rest")]


def bc_text(changes):
    return ",".join("+".join(str(p + 1) for p in c) for c in changes)


def bc_lines():
    out = ["# disksaver belfry_changes parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    for k, h in {"hand_one_island": (1, 1, (2, 1, 3, 4, 5)), "hand_tenor_last": (5, 5, (5, 4, 3, 2, 1)),
                 "hand_six_bells": (6, 3, (3, 1, 2, 6, 4, 5))}.items():
        cases.append((k, SYN["syn5"], 0, h))
    for cname, doc, seed, hand in cases:
        ctx = patched(bc, "ring", lambda d, s=0, h=hand: (["h"] * len(h[2]), frozenset(range(1, h[0] + 1)), h[1], tuple(h[2]))) \
            if hand else patched(bc, "FORMAT", bc.FORMAT)
        with ctx:
            names, islands, tenor, start = bc.ring(doc, seed)
            n = len(start)
            out.append(f"C {cname}")
            out.append(f"L {lst(start)} {len(islands)} {tenor}")
            par, plan = bc.solve(start, islands, tenor)
            spar, splan = bc.solve(start, islands, tenor, single=True)
            out.append(f"P {par} {bc_text(plan) or '-'} {spar}")
            p = bc_text(plan)
            tries = [p, "", bc_text(plan[:-1]), (p + ",1") if p else "1", bc_text(splan), "1+2", "0", str(n), "x",
                     "1+3,1+3", "1,1,1,1", "2,1,2,1,2,1", "1+3,2+4", "+1", "3+1", ",".join(["1"] * 12)]
            for t in tries:
                ok, r = run(lambda m=t: bc.play(doc, seed, changes=m), BC_KINDS)
                if ok:
                    out.append(f"T {t or '-'} ok {r['count']} {lst(r['final'])} {lst(r['led'])} {r['verdict']}")
                else:
                    out.append(f"T {t or '-'} err {r}")
    return out


# ---------------------------------------------------------------- G566 Tram Shunt
TS_KINDS = [("is not FROM+TO", "format"), ("already out", "out"), ("not possible", "impossible")]


def ts_greedy_moves(order):
    s, n, out = (tuple(order), (), (), 1), len(order), []
    while s[3] <= n and len(out) <= 200:
        for m in ("inout", "Aout", "Bout"):
            t = ts.step(s, m)
            if t is not None:
                s = t
                out.append(m)
                break
        else:
            if not s[0]:
                break
            w = s[0][0]
            fits = [(top, m) for top, m in ((s[1][-1] if s[1] else None, "inA"), (s[2][-1] if s[2] else None, "inB"))
                    if top is not None and top > w]
            m = min(fits)[1] if fits else ("inA" if not s[1] else "inB" if not s[2] else "inA")
            s = ts.step(s, m)
            out.append(m)
    return out


def ts_lines():
    out = ["# disksaver tram_shunt parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    for k, order in {"hand_in_order": (1, 2, 3, 4, 5, 6), "hand_reversed": (6, 5, 4, 3, 2, 1),
                     "hand_four": (3, 1, 4, 2), "hand_one": (1,)}.items():
        cases.append((k, SYN["syn5"], 0, order))
    for cname, doc, seed, hand in cases:
        ctx = patched(ts, "train", lambda d, s=0, h=hand: (["h"] * len(h), tuple(h))) if hand else \
            patched(ts, "FORMAT", ts.FORMAT)
        with ctx:
            names, order = ts.train(doc, seed)
            out.append(f"C {cname}")
            out.append(f"L {lst(order)}")
            ok, pr = run(lambda: ts.solve(order), [("cannot marshal", "unsolvable")])
            if not ok:
                out.append(f"P err {pr}")
                continue
            par, plan = pr
            g = ts.greedy(order)
            out.append(f"P {par} {','.join(plan) or '-'} {-1 if g is None else g}")
            p = ",".join(plan)
            tries = [p, "", ",".join(plan[:-1]), p + ",inout", "inout", "xx", "AA", "inA,inB,inA,inB,inA,inB",
                     ",".join(ts_greedy_moves(order)), "inA,Aout", "inB,BA,Aout", "Bout", "outA",
                     p.replace("inA", "inB", 1)]
            for t in tries:
                ok, r = run(lambda m=t: ts.play(doc, seed, moves=m), TS_KINDS)
                if ok:
                    out.append(f"T {t or '-'} ok {r['count']} {r['out']} {r['verdict']}")
                else:
                    out.append(f"T {t or '-'} err {r}")
    return out

GAMES = {"manifest_match": mm_lines, "twin_pilots": tp_lines, "quayside_shove": qs_lines, "sack_chute": sc_lines,
         "seal_roll": sr_lines, "channel_dash": cd_lines, "boom_defence": bd_lines, "salvage_sale": ss_lines,
         "rope_run": rr_lines, "belfry_changes": bc_lines, "tram_shunt": ts_lines}


def texts():
    return {g: "\n".join(fn()) + "\n" for g, fn in GAMES.items()}


def path(g):
    return os.path.join(CORE_TEST, f"disksaver_{g}_parity.txt")


def main(argv):
    t = texts()
    if "--write" in argv:
        for g, text in t.items():
            with open(path(g), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        return 0
    if "--check" in argv:
        bad = []
        for g, text in t.items():
            try:
                with open(path(g), encoding="utf-8") as f:
                    if f.read() != text:
                        bad.append(g)
            except OSError:
                bad.append(g)
        print("disksaver parity " + ("up to date" if not bad else "STALE: " + ", ".join(bad) + " (rerun --write)"))
        return 1 if bad else 0
    for text in t.values():
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
