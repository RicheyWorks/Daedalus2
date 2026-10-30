# SPDX-License-Identifier: MIT
"""Golden outputs for the C++17 ports of the DiskSaver minigame cores (G573 batch 1, G574 batch 2, G575 batch 3, G576 batch 4, G577 batch 5, G578 batch 6, G579 batch 7, G580 batch 8;
G581 seed spec draws from tools/streaming/disksaver_seed_spec.py;
G590 Gantry Sweep from tools/streaming/gantry_sweep_parity.py;
G590 Gantry Sweep from tools/streaming/gantry_sweep_parity.py;
G598 Buddy Berths from tools/streaming/tidelinks_golf_parity.py).

Each game's Python tool lays out the puzzle (its seeded layout stays in Python: the C++ side
never reimplements Python's random) and then plays a fixed set of move lists through the real
play() path. The layout, the par plan and every result or refusal go into
engines/unreal/core-test/disksaver_<game>_parity.txt, and the header-only
DaedalusDiskSaver<Game>Core.h ports replay every line in disksaver_<game>_core_test.cpp.

Batch 1: G556 Manifest Match, G557 Twin Pilots, G558 Quayside Shove, G559 Sack Chute.
Batch 2: G560 Seal Roll, G561 Channel Dash, G562 Boom Defence, G563 Salvage Sale.
Batch 3: G564 Rope Run, G565 Belfry Changes, G566 Tram Shunt.
Batch 4: G555 Watchfires, G554 Tide Lock, G553 Smugglers Island, G552 Harbour Cryptogram
(the cryptogram's cipher, key and plain text and the smuggler's hidden island are written into the file).
Batch 5: G551 Fleet Soundings, G550 Quay Duel, G549 Last Crate, G546 Census Riddles (the riddles
and their answers are written into the file).
Batch 6: G166 Tide Clocks, G171 Lighthouse Leases, G175 Tidemark Chunks, G179 Bottle Census: seeded
simulations over the G86 shoals data; every random draw the tool makes is recorded as a tape.
Batch 7: G253 Ebb Tide Eviction, G505 Beacon Watch, G529 Budget Fathoms, G533 Fleet Flags: the
G206 census budget tools. Each case writes its inputs (census or report, budget, config) and the
tool's expected output lines; seeded variants of the real census are made here with Python's
random and written out, so the C++ side only reads them.
Batch 8: G531 Stray Cargo, G519 Memory Footprint, G517 Budget Trend Ledger, G544 Caulking Check:
the survey, ranking, ledger diff/trend and byte checks; file walks, ledger files and CLIs stay in Python.
Cases cover the real tools/world_census fixtures (several seeds), synthetic censuses, and
hand-laid edge layouts (unsolvable, stuck, disconnected) injected through the tool's own
play() by swapping its layout function for one call.

  python tools/streaming/disksaver_cpp_parity.py            # print every file
  python tools/streaming/disksaver_cpp_parity.py --check    # exit 1 if a checked-in file is stale
  python tools/streaming/disksaver_cpp_parity.py --write    # rewrite the checked-in files
"""
import dataclasses
import json
import os
import random
import subprocess
import sys
import tempfile
import types
from collections import deque
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import beacon_watch as bw  # noqa: E402
import belfry_changes as bc  # noqa: E402
import boom_defence as bd  # noqa: E402
import bottle_census as bcs  # noqa: E402
import budget_fathoms as bf  # noqa: E402
import budget_ledger as bl  # noqa: E402
import caulking_check as ck  # noqa: E402
import census_budget as cb  # noqa: E402
import census_riddles as cr  # noqa: E402
import disksaver_seed_spec as dss  # noqa: E402
import gantry_sweep_parity as gsp  # noqa: E402
import buddy_berths_parity as bbp  # noqa: E402
import tidelinks_golf_parity as tgp  # noqa: E402
import ebb_eviction as ee  # noqa: E402
import harbour_cryptogram as hc  # noqa: E402
import last_crate as lc  # noqa: E402
import lighthouse_leases as ll  # noqa: E402
import channel_dash as cd  # noqa: E402
import fleet_flags as ff  # noqa: E402
import fleet_soundings as fs  # noqa: E402
import manifest_match as mm  # noqa: E402
import memory_footprint as mf  # noqa: E402
import quay_duel as qd  # noqa: E402
import quayside_shove as qs  # noqa: E402
import rope_run as rr  # noqa: E402
import sack_chute as sc  # noqa: E402
import salvage_sale as ss  # noqa: E402
import seal_roll as sr  # noqa: E402
import smugglers_island as si  # noqa: E402
import stray_cargo as sgc  # noqa: E402
import tide_clocks as tc  # noqa: E402
import tide_lock as tl  # noqa: E402
import tidemark_chunks as tm  # noqa: E402
import tram_shunt as ts  # noqa: E402
import twin_pilots as tp  # noqa: E402
import watchfires as wf  # noqa: E402

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

# ---------------------------------------------------------------- G555 Watchfires
WF_KINDS = [("no island", "unknown")]


def wf_lines():
    out = ["# disksaver watchfires parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    hl = lambda n: [f"h:{i}" for i in range(n)]  # noqa: E731
    for k, h in {"hand_one": (hl(1), []), "hand_path5": (hl(5), [(i, i + 1) for i in range(4)]),
                 "hand_star": (hl(7), [(0, i) for i in range(1, 7)]),
                 "hand_isolated3": (hl(3), []),
                 "hand_greedy_trap": (hl(6), [(0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 4), (4, 5)])}.items():
        cases.append((k, SYN["syn5"], 0, h))
    for cname, doc, seed, hand in cases:
        ctx = patched(wf, "chart", lambda d, s=0, h=hand: (list(h[0]), sorted(h[1]))) if hand else \
            patched(wf, "FORMAT", wf.FORMAT)
        with ctx:
            labels, edges = wf.chart(doc, seed)
            n = len(labels)
            k, best = wf.par(n, edges)
            g = wf.greedy(n, edges)
            out.append(f"C {cname}")
            out.append(f"L {lst(labels)} {lst(f'{a}-{b}' for a, b in edges)}")
            out.append(f"P {k} {lst(best)} {lst(g)}")
            bl = [labels[i] for i in best]
            tries = [None, bl, [labels[i] for i in g], [], bl[:-1], bl + [labels[-1]], bl + bl[:1], list(labels),
                     ["nowhere:9"], bl + ["nowhere:9"], labels[:1], list(reversed(labels))[:2]]
            for t in tries:
                ok, r = run(lambda m=t: wf.game(doc, seed, fires=m, auto=m is None), WF_KINDS)
                name = "auto" if t is None else lst(t)
                if ok:
                    idx = {l: i for i, l in enumerate(labels)}
                    out.append(f"T {name} ok {lst(idx[f] for f in r['fires'])} {lst(idx[f] for f in r['unlit'])} {r['verdict']}")
                else:
                    out.append(f"T {name} err {r}")
    return out


# ---------------------------------------------------------------- G554 Tide Lock
TL_REFUSE = [("longer than the chamber", "long"), ("must be a positive integer", "param")]


def tl_lines():
    out = ["# disksaver tide_lock parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            q = tl.boats(doc, s)
            big = max(b[1] for b in q)
            for f, cyc in ((1, 30), (3, 7)):
                cases.append((f"{cname}_seed{s}_x{f}_c{cyc}", doc, s, None, big * f, cyc))
    hand = {"hand_one": [("h:0", 5, 0)], "hand_burst": [(f"h:{i}", 3, 0) for i in range(6)],
            "hand_spread": [("h:0", 4, 0), ("h:1", 4, 40), ("h:2", 9, 41), ("h:3", 1, 90), ("h:4", 6, 91)],
            "hand_tie": [("h:0", 2, 0), ("h:1", 2, 10), ("h:2", 2, 20), ("h:3", 2, 30)]}
    for k, q in hand.items():
        cases.append((k, SYN["syn5"], 0, q, 12, 10))
    cases.append(("hand_too_long", SYN["syn5"], 0, hand["hand_spread"], 8, 10))
    cases.append(("hand_bad_cycle", SYN["syn5"], 0, hand["hand_one"], 5, 0))
    for cname, doc, seed, q, chamber, cyc in cases:
        ctx = patched(tl, "boats", lambda d, s, h=q: list(h)) if q else patched(tl, "FORMAT", tl.FORMAT)
        with ctx:
            queue = tl.boats(doc, seed)
            n = len(queue)
            out.append(f"C {cname}")
            out.append(f"L {chamber} {cyc} {lst(f'{b[1]}:{b[2]}' for b in queue)}")
            ok, r = run(lambda: tl.puzzle(doc, seed, chamber, cyc), TL_REFUSE)
            if not ok:
                out.append(f"P err {r}")
                continue
            best = tl.puzzle(doc, seed, chamber, cyc, auto=True)["optimal_plan"]
            out.append(f"P {r['optimal_wait']} {lst(best)} {lst(r['greedy_plan'])} {r['greedy_wait']}")
            tries = [None, best, r["greedy_plan"], [n], [1] * n, best[:-1], best + [1], [0] + best, [-1, n + 1], [],
                     [n + 1], [2] * (n // 2) + [1] * (n % 2), [1] * (n + 3)]
            for t in tries:
                p = tl.puzzle(doc, seed, chamber, cyc, plan=t, auto=t is None)
                name = "auto" if t is None else lst(t)
                if p["verdict"] == "jammed":
                    pr = p["problem"]
                    kind = "plan" if pr.startswith("plan must") else "group" + pr.split()[1]
                    out.append(f"T {name} jam {kind}")
                else:
                    out.append(f"T {name} ok {p['wait']} {p['verdict']}")
    return out


# ---------------------------------------------------------------- G553 Smugglers Island
SI_KINDS = [("give --auto", "mode"), ("accusation", "accuse"), ("unknown question", "question"), ("no island", "island")]


def si_lines():
    out = ["# disksaver smugglers_island parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))

    def hs(rows):
        return sorted(({"label": f"{w}:{s}", "world": w, "realm": r, "slot": s, "cargo": c} for w, r, s, c in rows),
                      key=lambda t: t["label"])
    for k, h in {"hand_one": (hs([("w", "none", 0, 0)]), 0),
                 "hand_twins": (hs([("w", "none", 0, 5), ("w", "none", 1, 5)]), 1),
                 "hand_realms": (hs([("a", "r1", 0, 0), ("a", "r1", 1, 3), ("b", "r2", 0, 3), ("c", "none", 2, 9),
                                     ("c", "none", 4, 1)]), 3),
                 "hand_wide": (hs([("z", "none", i, i % 3) for i in range(9)]), 8)}.items():
        cases.append((k, SYN["syn5"], 0, h))
    for cname, doc, seed, hand in cases:
        ctx = patched(si, "setup", lambda d, s, h=hand: (h[0], si.questions(h[0]), h[1])) if hand else \
            patched(si, "FORMAT", si.FORMAT)
        with ctx:
            sus, qs, hidden = si.setup(doc, seed)
            labels = [x["label"] for x in sus]
            depth, _ = si.solver(qs)
            out.append(f"C {cname}")
            out.append(f"L {hidden} {lst('|'.join(str(x[f]) for f in ('label', 'world', 'realm', 'slot', 'cargo')) for x in sus)}")
            out.append(f"P {depth(frozenset(range(len(sus))))} {lst(qs)}")
            a = si.play(doc, seed, auto=True)
            path = [x["question"] for x in a["asked"]]
            wrong = labels[(hidden + 1) % len(labels)]
            tries = [("auto", None, None), ("a", path, labels[hidden]), ("a", path, wrong), ("a", [], labels[hidden]),
                     ("a", list(qs), labels[hidden]), ("a", path + path[:1], labels[hidden]),
                     ("a", path[:-1], labels[hidden]), ("a", ["planet:x"], labels[hidden]),
                     ("a", path, "nowhere:0"), ("a", path, None), ("mix", path, labels[hidden])]
            for mode, asks, acc in tries:
                ok, r = run(lambda m=mode, q=asks, c=acc: si.play(doc, seed, q, c, auto=m in ("auto", "mix")), SI_KINDS)
                name = "auto -" if mode == "auto" else f"{lst(asks)} {acc or '-'}" + (" mix" if mode == "mix" else "")
                if ok:
                    log = lst(f"{x['question']}/{x['answer'][0]}/{x['suspects_left']}" for x in r["asked"])
                    out.append(f"T {name} ok {log} {r['accused']} {lst(r['still_possible'])} {r['verdict']}")
                else:
                    out.append(f"T {name} err {r}")
    return out


# ---------------------------------------------------------------- G552 Harbour Cryptogram
def hx(s):
    return "x" + s.encode("utf-8").hex()


def hc_hand(plain, shift, given):
    key = {c: chr((ord(c) - 65 + shift) % 26 + 65) for c in hc.ALPHA}
    cipher = hc.encode(plain, key)
    used = sorted({ch for ch in plain if ch in hc.ALPHA})
    freq = {}
    for ch in cipher:
        if ch in hc.ALPHA:
            freq[ch] = freq.get(ch, 0) + 1
    return {"seed": 0, "cipher": cipher, "plain": plain, "given": {key[p]: p for p in given},
            "frequency": dict(sorted(freq.items(), key=lambda t: (-t[1], t[0]))), "key": {key[p]: p for p in used}}


def hc_lines():
    out = ["# disksaver harbour_cryptogram parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    for n in (0, 1, 7, 13, 19, 20, 21, 40, 99, 100, 101, 110, 999, 1000, 1234, 20261029):
        out.append(f"N {n} {hc.number_words(n).replace(' ', '_')}")
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", hc.make(doc, s)))
    cases.append(("hand_short", hc_hand("SEA STOP TEA", 1, "SE")))
    cases.append(("hand_one_word", hc_hand("ARK", 25, "A")))
    cases.append(("hand_numbers", hc_hand(hc.number_words(4321) + " ISLANDS", 13, "IN")))
    for cname, p in cases:
        plain, cipher = p["plain"], p["cipher"]
        out.append(f"C {cname}")
        pairs = lambda m: lst(f"{c}={v}" for c, v in sorted(m.items()))  # noqa: E731
        out.append(f"L {cipher.replace(' ', '_')} {plain.replace(' ', '_')} {pairs(p['key'])} {pairs(p['given'])}")
        board = "".join(p["given"].get(ch, "_") if ch in hc.ALPHA else "." for ch in cipher)
        out.append(f"F {lst(f'{c}:{k}' for c, k in p['frequency'].items())} {board}")
        half = plain[:len(plain) // 2]
        guesses = [plain, "", plain.lower(), "Q" + plain[1:], half, plain + " EXTRA", plain.replace(" ", "--") + "!",
                   cipher, "A" * len(plain), "  " + plain.lower() + "  ", plain[1:], "x"]
        for gs in guesses:
            r = hc.grade(p, gs)
            out.append(f"T g {hx(gs)} {r['right']} {r['letters']} {r['verdict']}")
        inv = dict(p["key"])
        ks = sorted(inv)
        rot = {c: inv[ks[(i + 1) % len(ks)]] for i, c in enumerate(ks)}
        maps = [inv, {}, {c: inv[c] for c in ks[:len(ks) // 2]}, {" " + c.lower(): inv[c].lower() + "\t" for c in ks},
                {"QQ": "S"}, {"1": "A"}, {ks[0]: ""}, rot, dict([(ks[0].lower(), "Z"), (ks[0] + " ", inv[ks[0]])]),
                {c: "E" for c in ks}]
        for m in maps:
            enc = lst(f"{hx(k)}.{hx(v)}" for k, v in m.items())
            try:
                reads = hc.apply_mapping(p, m)
            except hc.CryptogramError as e:
                assert "single letters" in str(e)
                out.append(f"T m {enc} err letters")
                continue
            r = hc.grade(p, reads)
            out.append(f"T m {enc} ok {hx(reads)} {r['right']} {r['letters']} {r['verdict']}")
    return out


# ---------------------------------------------------------------- G551 Fleet Soundings
def fs_grid(cells, size):
    return ["".join("#" if (r, c) in cells else "." for c in range(size)) for r in range(size)]


def fs_lines():
    out = ["# disksaver fleet_soundings parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    for k, ships in {"hand_one_boat": [("h:0", 1)], "hand_pair": [("h:0", 2), ("h:1", 2)],
                     "hand_full": [("h:0", 4), ("h:1", 3), ("h:2", 3), ("h:3", 2)],
                     "hand_singles": [(f"h:{i}", 1) for i in range(5)]}.items():
        cases.append((k, SYN["syn5"], 3, ships))
    for cname, doc, seed, ships in cases:
        ctx = patched(fs, "fleet", lambda d, s=0, h=ships: (__import__("random").Random(11), list(h))) if ships else \
            patched(fs, "FORMAT", fs.FORMAT)
        with ctx:
            p = fs.generate(doc, seed)
        size = p["size"]
        lengths = [s["length"] for s in p["fleet"]]
        hints = {(h["row"], h["col"]): h["hull"] for h in p["hints"]}
        sol = p["solution"]
        out.append(f"C {cname}")
        out.append(f"L {size} {lst(lengths)} {lst(p['rows'])} {lst(p['cols'])} "
                   f"{lst(f'{r}.{c}.{int(v)}' for (r, c), v in sorted(hints.items()))} {'/'.join(sol)}")
        for limit, hs in ((2, hints), (1, hints), (2, {}), (4, {})):
            sols = fs.solve(size, lengths, p["rows"], p["cols"], hs, limit)
            out.append(f"S {limit} {int(bool(hs))} {len(sols)} {lst(('/'.join(fs_grid(x, size)) for x in sols), ';')}")
        flip = [list(r) for r in sol]
        flip[0][0] = "." if flip[0][0] == "#" else "#"
        tr = ["".join(sol[c][r] for c in range(size)) for r in range(size)]
        water = ["." * size] * size
        bent = list(water)
        bent[1] = "##" + "." * (size - 2)
        bent[2] = ".#" + "." * (size - 2)
        diag = list(water)
        diag[0] = "#" + "." * (size - 1)
        diag[1] = ".#" + "." * (size - 2)
        grids = [sol, water, ["".join(r) for r in flip], tr, sol[:-1], [r + "." for r in sol],
                 [sol[0].replace(".", "~")] + sol[1:], bent, diag, list(reversed(sol)), ["#" * size] * size,
                 [r[::-1] for r in sol]]
        for g in grids:
            r = fs.check(p, g)
            out.append(f"T {hx(chr(10).join(g))} {r['verdict']} {hx(chr(10).join(r['problems']))}")
    return out


# ---------------------------------------------------------------- G550 Quay Duel
QD_KINDS = [("exactly one", "mode"), ("ran out", "short"), ("unknown move", "move"), ("after the quay", "long")]


def qd_lines():
    out = ["# disksaver quay_duel parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    for k, vals in {"hand_one": [5], "hand_twin": [7, 7], "hand_trap": [1, 100, 1], "hand_classic": [3, 9, 1, 2],
                    "hand_flat": [4, 4, 4, 4, 4], "hand_zero": [0, 0, 0]}.items():
        cases.append((k, SYN["syn5"], 0, [(f"h:{i}", v) for i, v in enumerate(vals)]))
    for cname, doc, seed, hand in cases:
        ctx = patched(qd, "quay", lambda d, s, h=hand: list(h)) if hand else patched(qd, "FORMAT", qd.FORMAT)
        with ctx:
            values = [v for _, v in qd.quay(doc, seed)]
            n = len(values)
            out.append(f"C {cname}")
            out.append(f"L {lst(values)}")
            out.append(f"P {qd.margins(values)[0][n - 1]}")
            for second in (False, True):
                a = qd.duel(doc, seed, auto=True, second=second)
                mine = [t["move"] for t in a["turns"] if t["captain"] == "you"]
                k = len(mine)
                tries = [None, mine, ["L"] * k, ["R"] * k, mine[:-1], mine + ["L"], ["X"] + mine[1:], [],
                         [("L", "R")[i % 2] for i in range(k)], ["l"] * k]
                if second:
                    tries.append("both")
                for t in tries:
                    if t == "both":
                        ok, r = run(lambda: qd.duel(doc, seed, moves=mine, auto=True, second=second), QD_KINDS)
                    else:
                        ok, r = run(lambda m=t: qd.duel(doc, seed, moves=m, auto=m is None, second=second), QD_KINDS)
                    name = "both" if t == "both" else "auto" if t is None else lst(t)
                    head = f"T {int(second)} {name}"
                    if ok:
                        mv = "".join(x["move"] for x in r["turns"])
                        out.append(f"{head} ok {r['you_kib']} {r['casimir_kib']} {r['best_margin_kib']} {r['gave_away_kib']} "
                                   f"{mv} {r['outcome']}")
                    else:
                        out.append(f"{head} err {r}")
    return out


# ---------------------------------------------------------------- G549 Last Crate
LC_KINDS = [("hold-kib must", "hold"), ("exactly one", "mode"), ("moves ran out", "short"), ("unknown move", "move"),
            ("stack is empty", "empty"), ("after the game", "long")]


def lc_lines():
    out = ["# disksaver last_crate parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            cases.append((f"{cname}_seed{s}", doc, s, None))
    for k, ws in {"hand_one": [5], "hand_equal": [3, 3, 3], "hand_spike": [1, 2, 50, 1], "hand_zero": [0, 0, 4]}.items():
        cases.append((k, SYN["syn5"], 0, [(f"h:{i}", w) for i, w in enumerate(ws)]))
    for cname, doc, seed, hand in cases:
        ctx = patched(lc, "stack", lambda d, s, h=hand: list(h)) if hand else patched(lc, "FORMAT", lc.FORMAT)
        with ctx:
            deck = [w for _, w in lc.stack(doc, seed)]
            n, tot = len(deck), sum(deck)
            holds = sorted({max(1, tot // 2), max(1, max(deck) - 1), max(1, tot), cb.MAX_KIB}) + [0, cb.MAX_KIB + 1]
            out.append(f"C {cname}")
            out.append(f"L {lst(deck)}")
            for hold in holds:
                ok, a = run(lambda: lc.play(doc, seed, hold, auto=True), LC_KINDS)
                tries = [None, ["sail"], ["load", "sail"], ["load"] * n + ["sail"], ["load"] * (n + 1), [], ["load"],
                         ["fly"], ["Load", "sail"], "both"]
                if ok:
                    tries.append([t["move"] for t in a["turns"]] + ["sail"])
                for t in tries:
                    if t == "both":
                        ok, r = run(lambda: lc.play(doc, seed, hold, moves=["sail"], auto=True), LC_KINDS)
                    else:
                        ok, r = run(lambda m=t: lc.play(doc, seed, hold, moves=m, auto=m is None), LC_KINDS)
                    name = "both" if t == "both" else "auto" if t is None else lst(t)
                    head = f"T {hold} {name}"
                    if ok:
                        adv = lst((";".join((x["advice"]["bust_chance"], x["advice"]["load_value"], x["advice"]["sail_value"],
                                             x["advice"]["advice"]) + ((x["move"],))) for x in r["turns"]))
                        out.append(f"{head} ok {r['carried_kib']} {r['best_kib']} {r['outcome']} {adv}")
                    else:
                        out.append(f"{head} err {r}")
    return out


# ---------------------------------------------------------------- G546 Census Riddles
def cr_riddle(r):
    return f"{r['id']}.{r['kind']}.{hx(r['question'])}.{hx(r['answer'])}"


def cr_lines():
    out = ["# disksaver census_riddles parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    with open(cb.DEFAULT_CONFIG, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    for n in (0, 1, 20, 21, -3):
        ok, _ = run(lambda c=n: cr.draw(SYN["syn5"], cfg, 0, c), [("count must", "count")])
        out.append(f"N {n} {'ok' if ok else 'count'}")
    cases = []
    for cname, doc in censuses():
        for s in (SEEDS if cname == "real" else SEEDS[1:3]):
            for count in ((5, 9) if cname == "real" else (5,)):
                cases.append((f"{cname}_seed{s}_n{count}", cr.draw(doc, cfg, s, count)))
    hand = [("islands_total", "1000"), ("widest_world", "Alpha"), ("world_ram", "0"), ("heaviest_island", "beta:7"),
            ("cargo_total", "-12")]
    cases.append(("hand_mixed", {"seed": 0, "riddles": [{"id": f"r{i + 1}", "kind": k, "question": f"Q {k}?", "answer": a}
                                                       for i, (k, a) in enumerate(hand)]}))
    cases.append(("hand_single", {"seed": 0, "riddles": [{"id": "r1", "kind": "empty_islands", "question": "How many?",
                                                          "answer": "7"}]}))
    for cname, q in cases:
        rs = q["riddles"]
        out.append(f"C {cname}")
        out.append(f"L {lst(cr_riddle(r) for r in rs)}")
        right = {r["id"]: r["answer"] for r in rs}

        def vary(a, how):
            if how == "case":
                return "  " + a.upper() + "\t"
            if a.lstrip("-").isdigit():
                return {"commas": ",".join(a), "plus": "+" + a.lstrip("-") if not a.startswith("-") else a,
                        "zeros": ("-00" + a[1:]) if a.startswith("-") else "00" + a, "under": a[0] + "_" + a[1:],
                        "spaced": a + " ,"}[how]
            return a + "!"
        tries = [right, {}, {k: v + "x" for k, v in right.items()}, dict(list(right.items())[: len(right) // 2])]
        for how in ("case", "commas", "plus", "zeros", "under", "spaced"):
            tries.append({k: vary(v, how) for k, v in right.items()})
        tries.append(dict(right, r99="1", extra="x"))
        tries.append({k: "" for k in right})
        tries.append({k: "-0" if v == "0" else " " for k, v in right.items()})
        for t in tries:
            g = cr.grade(q, t)
            flags = "".join("1" if x["correct"] else "0" for x in g["results"])
            out.append(f"T {lst(f'{hx(k)}.{hx(v)}' for k, v in t.items())} {g['score']} {g['out_of']} {flags} {g['verdict']}")
    return out


# ---------------------------------------------------------------- batch 6: seeded simulations (G166, G171, G175, G179)
# These tools interleave Python's random with their simulation, so the generator records every
# draw the tool makes (a "tape": randrange/randint results and sample picks, in call order) and the
# C++ core replays the tape through the ported simulation, checking each draw against its own bound.
class _Tape(random.Random):
    last = None

    def __init__(self, seed):
        self.tape, self.depth = [], 0
        super().__init__(seed)
        _Tape.last = self

    def randrange(self, start, stop=None, step=1):
        self.depth += 1
        v = super().randrange(start, stop, step)
        self.depth -= 1
        if not self.depth:
            self.tape.append(v)
        return v

    def randint(self, a, b):
        self.depth += 1
        v = super().randint(a, b)
        self.depth -= 1
        if not self.depth:
            self.tape.append(v)
        return v

    def sample(self, population, k, **kw):
        self.depth += 1
        v = super().sample(population, k, **kw)
        self.depth -= 1
        if not self.depth:
            self.tape.extend(v)
        return v


def taped(mod, fn):
    """(result, tape) of fn() with mod.random.Random recording every draw."""
    with patched(mod, "random", types.SimpleNamespace(Random=_Tape)):
        r = fn()
    return r, lst(_Tape.last.tape)


def cfg_json(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def vlines(mod, base, section, fields):
    out = []
    for k, vals in fields.items():
        for v in vals:
            cfg = json.loads(json.dumps(base))
            cfg[section][k] = v
            try:
                mod.validate(cfg)
                out.append(f"V {k} {v} ok")
            except ValueError:
                out.append(f"V {k} {v} err")
    return out


def tc_lines():
    out = ["# disksaver tide_clocks parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    base = cfg_json("data/islands/disk-saver/tide-clocks-v1.json")
    real = tc.validate(base)
    ids, kpi = tc.islands_from_shoals(cfg_json(base["shoals_data"]))
    out.append(f"K {len(ids)} {kpi}")
    out.append(f"B {len(real.islands)} {len(real.saves)} {real.steps} {real.edit_permille} {real.max_skew}")
    out += vlines(tc, base, "clocks", {"islands": [1, 2, len(ids), len(ids) + 1], "saves": [0, 1, kpi, kpi + 1],
                                        "steps": [0, 1, 5000], "edit_permille": [0, 1, 999, 1000],
                                        "max_skew": [-1, 0, 1000]})
    R = dataclasses.replace
    cases = [(f"real_seed{s}", R(real, seed=s)) for s in (real.seed, 1, 7, 42)]
    isl = lambda n: tuple(f"i{k}" for k in range(n))  # noqa: E731
    sv = lambda n: tuple(f"save_{k:03d}" for k in range(n))  # noqa: E731
    cases += [("hand_two_one_step", R(real, islands=isl(2), saves=sv(1), steps=1)),
              ("hand_edit_heavy", R(real, edit_permille=999, steps=200)),
              ("hand_ferry_heavy", R(real, edit_permille=1, steps=200)),
              ("hand_no_skew", R(real, max_skew=0, steps=300)),
              ("hand_wild_skew", R(real, max_skew=500, steps=300, islands=isl(3), saves=sv(2))),
              ("hand_six_isles", R(real, islands=isl(6), saves=sv(3), steps=400, seed=9))]
    for name, c in cases:
        out.append(f"C {name}")
        out.append(f"L {len(c.islands)} {len(c.saves)} {c.steps} {c.edit_permille} {c.max_skew}")
        tapes = set()
        for clock in tc.CLOCKS:
            (r, _), tape = taped(tc, lambda k=clock: tc.run(c, k))
            tapes.add(tape)
            out.append(f"T {clock} {r.status} {r.edits} {r.lost} {r.detected_conflicts} {r.oracle_conflicts} "
                       f"{r.causal_inversions} {r.survivors} {lst(r.lost_vids)}")
        assert len(tapes) == 1
        out.insert(len(out) - 3, f"R {tapes.pop()}")
    return out


def ll_lines():
    out = ["# disksaver lighthouse_leases parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    for lease, drift, guard in ((20, 150, 4), (20, 0, 0), (1000, 500, 0), (2, 499, 1), (7, -200, 3), (100, 33, 99)):
        out.append(f"D {lease} {drift} {guard} {ll.drift_bound(lease, drift)} {ll.last_valid_elapsed(lease, drift, guard)}")
    base = cfg_json("data/islands/disk-saver/lighthouse-leases-v1.json")
    real = ll.validate(base)
    c = real
    out.append(f"B {len(c.keepers)} {c.lease} {c.epochs} {c.write_permille} {c.max_drift_permille} {c.pause_permille} "
               f"{c.max_pause} {c.news_delay} {c.guard}")
    out += vlines(ll, base, "leases", {"lease": [1, 2, 1000, 1001], "epochs": [0, 1, 10000, 10001],
                                        "write_permille": [0, 1, 1000, 1001], "max_drift_permille": [-1, 0, 500, 501],
                                        "pause_permille": [-1, 1000, 1001], "max_pause": [-1, 1000, 1001],
                                        "news_delay": [-1, 0, 1001], "guard": [-1, 0, 19, 20]})
    R = dataclasses.replace
    cases = [(f"real_seed{s}", R(real, seed=s)) for s in (real.seed, 1, 7, 42)]
    cases += [("hand_two_keepers", R(real, keepers=("a", "b"), epochs=12)),
              ("hand_no_pause", R(real, pause_permille=0, max_pause=0)),
              ("hand_no_drift", R(real, max_drift_permille=0, epochs=15)),
              ("hand_tiny_lease", R(real, lease=2, guard=1, epochs=30)),
              ("hand_one_epoch", R(real, epochs=1, news_delay=0)),
              ("hand_wide_guard", R(real, guard=19, write_permille=1000, epochs=10)),
              ("hand_long_pause", R(real, pause_permille=1000, max_pause=40, epochs=8))]
    for name, c in cases:
        out.append(f"C {name}")
        out.append(f"L {len(c.keepers)} {c.lease} {c.epochs} {c.write_permille} {c.max_drift_permille} {c.pause_permille} "
                   f"{c.max_pause} {c.news_delay} {c.guard}")
        for mode in ll.MODES:
            r, tape = taped(ll, lambda m=mode: ll.run(c, m))
            out.append(f"T {mode} {tape} {r.writes} {r.accepted} {r.rejected} {r.stale_accepted} {r.outside_lease} {r.status}")
    return out


def tm_lines():
    out = ["# disksaver tidemark_chunks parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    for w in (b"", b"a", bytes(range(16)), b"\xff" * 16, b"tidemark chunks!"):
        out.append(f"H x{w.hex()} {tm.window_hash(w)}")
    base = cfg_json("data/islands/disk-saver/tidemark-chunks-v1.json")
    real = tm.validate(base)
    c = real
    out.append(f"S {cfg_json('data/islands/disk-saver/byte-spring-v1.json')['cistern']['budget_cap']}")
    out.append(f"B {lst(it.weight for it in c.islands)} {c.versions} {c.bytes_per_weight} {c.edits} {c.max_run} "
               f"{c.insert_permille} {c.delete_permille} {c.window} {c.mask_bits} {c.min_chunk} {c.max_chunk} "
               f"{c.fixed_size} {c.ref_bytes} {c.quota} {c.byte_unit}")
    out += vlines(tm, base, "chunks", {"versions": [0, 1, 1000, 1001], "insert_permille": [-1, 0, 1000, 1001],
                                        "delete_permille": [0, 600, 601], "window": [15, 16, 17], "mask_bits": [6, 7, 8],
                                        "min_chunk": [0, 1, 1024, 1025], "max_chunk": [31, 32, 1 << 20, (1 << 20) + 1],
                                        "fixed_size": [0, 1, 1 << 20], "ref_bytes": [-1, 0, 1024, 1025],
                                        "byte_unit": [0, 1, 1 << 20, (1 << 20) + 1], "edits": [-1, 0, 1000, 1001],
                                        "max_run": [0, 1, 4096, 4097], "bytes_per_weight": [0, 1, 65536, 65537]})
    R = dataclasses.replace
    Isl = tm.Island
    cases = [(f"real_seed{s}", R(real, seed=s)) for s in (real.seed, 1)]
    small = (Isl("a", 3), Isl("b", 1))
    cases += [("hand_small", R(real, islands=small, bytes_per_weight=64, versions=6, seed=3)),
              ("hand_no_edits", R(real, islands=small, bytes_per_weight=40, versions=4, edits=0)),
              ("hand_deletes", R(real, islands=(Isl("a", 1),), bytes_per_weight=30, versions=8, insert_permille=0,
                                 delete_permille=1000, max_run=40, edits=3)),
              ("hand_overwrites", R(real, islands=small, bytes_per_weight=50, versions=5, insert_permille=0,
                                    delete_permille=0)),
              ("hand_tight_chunks", R(real, islands=small, bytes_per_weight=60, versions=5, min_chunk=5, max_chunk=5,
                                      fixed_size=1, ref_bytes=0)),
              ("hand_one_version", R(real, islands=small, bytes_per_weight=100, versions=1, quota=1)),
              ("hand_big_runs", R(real, islands=small, bytes_per_weight=20, versions=6, max_run=300, quota=10 ** 9))]
    for name, c in cases:
        out.append(f"C {name}")
        out.append(f"L {lst(it.weight for it in c.islands)} {c.versions} {c.bytes_per_weight} {c.edits} {c.max_run} "
                   f"{c.insert_permille} {c.delete_permille} {c.window} {c.mask_bits} {c.min_chunk} {c.max_chunk} "
                   f"{c.fixed_size} {c.ref_bytes} {c.quota}")
        hist, tape = taped(tm, lambda: tm.saves(c))
        out.append(f"R {tape}")
        last = hist[-1][0]
        for mode in tm.MODES:
            r, t2 = taped(tm, lambda m=mode: tm.run(c, m))
            assert t2 == tape
            rec = [tm.chunk(s, c, mode) for ver in hist for s in ver]
            out.append(f"T {mode} {r.raw_bytes} {r.refs} {r.unique_chunks} {r.stored_bytes} {r.cost} "
                       f"{tm.cost_oracle(rec, c.ref_bytes)} {r.status} {lst(len(x) for x in tm.chunk(last, c, mode))}")
    return out


def bc_census_lines():
    out = ["# disksaver bottle_census parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    base = cfg_json("data/islands/disk-saver/bottle-census-v1.json")
    real = bcs.validate(base)
    c = real
    out.append(f"B {lst(it.weight for it in c.islands)} {c.credits_per_weight} {c.ticks} {c.send_permille} "
               f"{c.max_amount} {c.max_delay} {c.start} {c.max_skew} {c.initiator}")
    out += vlines(bcs, base, "census", {"ticks": [1, 2, 100000, 100001], "credits_per_weight": [0, 1, 10 ** 6, 10 ** 6 + 1],
                                         "send_permille": [-1, 0, 1000, 1001], "max_amount": [0, 1, 10 ** 6 + 1],
                                         "max_delay": [0, 1, 1000, 1001], "start": [-1, 0, 119, 120],
                                         "max_skew": [-1, 0, 1000, 1001], "initiator": [-1, 0, 5, 6]})
    R = dataclasses.replace
    Isl = bcs.Island
    cases = [(f"real_seed{s}", R(real, seed=s)) for s in (real.seed, 1, 7, 42)]
    cases += [("hand_two_isles", R(real, islands=(Isl("a", 2), Isl("b", 1)), initiator=1, ticks=60, start=20)),
              ("hand_silent", R(real, send_permille=0, ticks=30, start=10)),
              ("hand_fast_lanes", R(real, max_delay=1, ticks=60, start=30)),
              ("hand_start_zero", R(real, start=0, ticks=40)),
              ("hand_start_last", R(real, start=59, ticks=60, max_skew=0)),
              ("hand_flood", R(real, send_permille=1000, max_amount=10 ** 6, max_delay=30, ticks=50, start=25))]
    for name, c in cases:
        out.append(f"C {name}")
        out.append(f"L {lst(it.weight for it in c.islands)} {c.credits_per_weight} {c.ticks} {c.send_permille} "
                   f"{c.max_amount} {c.max_delay} {c.start} {c.max_skew} {c.initiator}")
        for mode in bcs.MODES:
            for fifo in (True, False):
                r, tape = taped(bcs, lambda m=mode, f=fifo: bcs.run(c, m, f))
                out.append(f"T {mode} {int(fifo)} {tape} {r.true_total} {r.census_total} {r.counted_balances} "
                           f"{r.counted_at_sea} {r.bottles} {int(r.consistent)} {r.status} {r.reason or '-'} "
                           f"{lst(r.cut)} {lst(r.lane_bottles)}")
    return out


# ---------------------------------------------------------------- batch 7 shared census lines
def b7_realm(w):
    if "realm_id" not in w or w["realm_id"] is None:
        return "-"
    r = w["realm_id"]
    return hx(r) if isinstance(r, str) else "!"


def b7_census(doc, tag="W", side=None):
    """Census input lines: W [side] id realm world_asset_definitions slot:n,..."""
    pre = f"{tag} {side} " if side else f"{tag} "
    out = []
    for w in doc["worlds"]:
        wad = w.get("asset_definitions")
        out.append(pre + f"{hx(w['id'])} {b7_realm(w)} {'-' if wad is None else wad} "
                   + lst(f"{i['slot']}:{i['asset_definitions']}" for i in w["islands"]))
    return out


def b7_budget(cfg, side=None):
    b = cfg["budget"]
    return (f"U {side} " if side else "U ") + f"{b['ram_budget_kib']} {b['disk_budget_kib']} {b['warn_permille']}"


def b7_refusal(e, kinds):
    msg = str(e)
    for needle, kind in kinds:
        if needle in msg:
            return "O refused " + kind
    raise e


def b7_seeded(seed):
    """The real tools/world_census census, re-weighted with Python's random (inputs only)."""
    doc = real_census()
    rng = random.Random(seed)
    realms = [None, "synthetic-realm", "harbour", "reef"]
    for w in doc["worlds"]:
        for i in w["islands"]:
            i["asset_definitions"] = rng.randrange(0, 1200)
        for s in range(rng.randrange(0, 5)):
            slot = 20 + s * rng.randrange(1, 4)
            if all(i["slot"] != slot for i in w["islands"]):
                w["islands"].append({"slot": slot, "asset_definitions": rng.randrange(0, 1200)})
        if seed % 2:
            w["realm_id"] = rng.choice(realms)
    if seed % 3 == 0:
        doc["worlds"].append({"id": f"seed-{seed}", "realm_id": rng.choice(realms), "asset_definitions": rng.randrange(0, 50),
                              "islands": [{"slot": s, "asset_definitions": rng.randrange(0, 900)} for s in range(rng.randrange(1, 7))]})
    return doc


def b7_censuses():
    yield "real", real_census()
    for s in SEEDS:
        yield f"real_seed{s}", b7_seeded(s)
    for k, v in SYN.items():
        yield k, v


B7_BUDGETS = [("shipped", {"budget": {"ram_budget_kib": 40000, "disk_budget_kib": 32768, "warn_permille": 900}}),
              ("roomy", {"budget": {"ram_budget_kib": 200000, "disk_budget_kib": 400000, "warn_permille": 750}}),
              ("tight", {"budget": {"ram_budget_kib": 16384, "disk_budget_kib": 4096, "warn_permille": 1000}})]
CB_KINDS = [("kib out of range", "budget_range"), ("warn_permille", "budget_warn"), ("nonempty list", "no_worlds"),
            ("world id missing", "world_id"), ("duplicate world", "duplicate_world"), ("duplicate slot", "duplicate_slot")]


def b7_bad_censuses():
    good = census([("a", [(0, 1)])])
    yield "refuse_no_worlds", {"budget": dict(B7_BUDGETS[0][1]["budget"])}, census([])
    yield "refuse_blank_id", B7_BUDGETS[0][1], census([(" \t", [(0, 1)])])
    yield "refuse_dup_world", B7_BUDGETS[0][1], census([("a", [(0, 1)]), ("a", [(1, 2)])])
    yield "refuse_dup_slot", B7_BUDGETS[0][1], census([("a", [(3, 1), (3, 2)])])
    yield "refuse_ram_zero", {"budget": {"ram_budget_kib": 0, "disk_budget_kib": 10, "warn_permille": 900}}, good
    yield "refuse_disk_big", {"budget": {"ram_budget_kib": 10, "disk_budget_kib": 100000001, "warn_permille": 900}}, good
    yield "refuse_warn", {"budget": {"ram_budget_kib": 10, "disk_budget_kib": 10, "warn_permille": 1001}}, good


def b7_edge_censuses():
    # 40000 KiB RAM: one island of n assets costs 16384 + 24n KiB
    yield "edge_ram_at_budget", B7_BUDGETS[0][1], census([("at", [(0, 984)]), ("over", [(0, 985)])])
    yield "edge_world_at_budget", {"budget": {"ram_budget_kib": 32816, "disk_budget_kib": 8384, "warn_permille": 900}}, \
        census([("pair", [(0, 1), (1, 1)]), ("pair_over", [(0, 1), (1, 2)])])
    yield "edge_near", {"budget": {"ram_budget_kib": 20000, "disk_budget_kib": 30000, "warn_permille": 900}}, \
        census([("near", [(0, 67), (1, 68), (2, 0)])])
    yield "edge_empty_world", B7_BUDGETS[0][1], census([("bare", []), ("one", [(5, 3)])])


# ---------------------------------------------------------------- G253 Ebb Tide Eviction
EE_KINDS = [("weights must be 1..", "weight_range"), ("duplicate world", "duplicate_world"),
            ("duplicate slot", "duplicate_slot"), ("islands", "too_many_islands")]


def ee_view(v):
    return "-" if v is None else f"{v['weight']}/{v['count']}/{lst(v['unload_slots'])}"


def ee_case(name, cfg, report, out, src):
    out.append(f"C {name}")
    out.append(f"K {lst(cfg.get('pinned_slots', []))} {cfg.get('default_weight', 1)}")
    for wid, m in sorted(cfg.get("weights", {}).items()):
        for k, v in sorted(m.items()):
            out.append(f"X {hx(wid)} {k} {v}")
    out.extend(src)
    try:
        p = ee.plan(report, cfg)
    except ee.EvictionError as e:
        out.append(b7_refusal(e, EE_KINDS))
        return
    for w in p["worlds"]:
        out.append(f"O w {hx(w['id'])} {w['total_ram_kib']} {w['need_kib']} {lst(w['pinned_slots'])} {w['tide']} "
                   f"{ee_view(w['optimal'])} {ee_view(w['greedy_heaviest_first'])} {ee_view(w['greedy_lowest_weight_first'])}")
    s = p["summary"]
    out.append(f"O s {s['worlds']} {s['over_budget']} {s['cannot_fit']} {s['unloads']} {s['greedy_heaviest_worse']} {s['greedy_weight_worse']}")


def ee_raw(budget, worlds):
    doc = {"format": "daedalus-census-budget", "version": 1, "budget": {"ram_budget_kib": budget},
           "worlds": [{"id": w, "islands": [{"slot": s, "ram_kib": r} for s, r in isl]} for w, isl in worlds]}
    src = [f"Q {budget}"] + [f"R {hx(w)} " + lst(f"{s}:{r}" for s, r in isl) for w, isl in worlds]
    return doc, src


def ee_lines():
    out = ["# disksaver ebb_eviction parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    shipped = cfg_json("data/islands/disk-saver/ebb-eviction-v1.json")
    heavy = dict(shipped, weights={"alpha": {"2": 9}, "seed-0": {"1": 7, "2": 3}, "big": {"3": 5, "7": 2, "11": 40}})
    nopin = dict(shipped, pinned_slots=[], default_weight=3)
    for cname, c in b7_censuses():
        for bname, b in (B7_BUDGETS[0], ("ebb", {"budget": {"ram_budget_kib": 20000, "disk_budget_kib": 32768, "warn_permille": 900}})):
            rep = cb.plan(c, b)
            src = [b7_budget(b)] + b7_census(c)
            for kname, k in (("shipped", shipped), ("weighted", heavy), ("nopin", nopin)):
                ee_case(f"{cname}_{bname}_{kname}", k, rep, out, src)
    for cname, b, c in b7_edge_censuses():
        ee_case(cname, shipped, cb.plan(c, b), out, [b7_budget(b)] + b7_census(c))
    hand = [
        ("hand_greedy_trap", 100, [("w", [(0, 10), (1, 60), (2, 50), (3, 50)])], {"w": {"1": 5, "2": 2, "3": 2}}),
        ("hand_at_budget", 100, [("w", [(0, 40), (1, 60)])], {}),
        ("hand_one_over", 100, [("w", [(0, 40), (1, 61)])], {}),
        ("hand_stranded", 50, [("w", [(0, 60), (1, 5)])], {}),
        ("hand_zero_budget", 0, [("z", [(1, 0), (2, 0)]), ("y", [(1, 3), (4, 0)])], {"y": {"4": 1000}}),
        ("hand_ties", 30, [("t", [(5, 10), (6, 10), (7, 10), (8, 10), (9, 20)])], {"t": {"9": 2}}),
        ("hand_no_islands", 10, [("e", [])], {}),
        ("hand_many", 1000, [("m", [(s, 37 * s % 101 + 50) for s in range(1, 15)])],
         {"m": {str(s): s % 4 + 1 for s in range(1, 15)}}),
    ]
    for name, budget, worlds, weights in hand:
        doc, src = ee_raw(budget, worlds)
        ee_case(name, dict(shipped, weights=weights), doc, out, src)
    bad = [
        ("refuse_weight_zero", dict(shipped, default_weight=0), [("w", [(0, 5)])]),
        ("refuse_weight_big", dict(shipped, weights={"w": {"1": 1001}}), [("w", [(0, 5)])]),
        ("refuse_dup_world", shipped, [("w", [(0, 5)]), ("w", [(1, 5)])]),
        ("refuse_dup_slot", shipped, [("w", [(1, 5), (1, 6)])]),
        ("refuse_513_islands", shipped, [("w", [(s, 1) for s in range(513)])]),
    ]
    for name, k, worlds in bad:
        doc, src = ee_raw(10, worlds)
        ee_case(name, k, doc, out, src)
    return out


# ---------------------------------------------------------------- G505 Beacon Watch
BW_KINDS = [("world id missing", "world_id"), ("duplicate world", "duplicate_world"), ("fits_all_resident", "fits"),
            ("max_resident", "max_resident"), ("beacon must be", "beacon"), ("duplicate slot", "duplicate_slot")]


def bw_raw_lines(side, doc):
    out = []
    for w in doc["worlds"]:
        f = w["fits_all_resident"]
        out.append(f"R {side} {hx(w['id'])} {int(f) if isinstance(f, bool) else '!'} {w['max_resident']} "
                   + lst(f"{i['slot']}:{i['beacon']}" for i in w["islands"]))
    return out


def bw_case(name, src, bdoc, cdoc, out):
    out.append(f"C {name}")
    out.extend(src)
    try:
        v = bw.watch(bdoc, cdoc)
    except bw.BeaconWatchError as e:
        side = str(e).split(":")[0]
        line = b7_refusal(e, BW_KINDS)
        out.append(line.replace("O refused ", f"O refused {side}_"))
        return
    for f in v["findings"]:
        out.append(f"O f {hx(f['world'])} {'-' if f['slot'] is None else f['slot']} {f['kind']} {f['before']} {f['after']} {int(f['fails'])}")
    out.append(f"O v {v['verdict']} {v['regressions']} " + lst(f"{k}={n}" for k, n in v["counts"].items()))


def bw_raw(worlds):
    return {"format": "daedalus-census-budget", "version": 1,
            "worlds": [{"id": w, "fits_all_resident": f, "max_resident": m,
                        "islands": [{"slot": s, "beacon": b} for s, b in isl]} for w, f, m, isl in worlds]}


def bw_lines():
    out = ["# disksaver beacon_watch parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cs = list(b7_censuses())
    pairs = []
    for i, (an, a) in enumerate(cs):
        bn, b = cs[(i + 1) % len(cs)]
        pairs.append((an, a, an, a))
        pairs.append((an, a, bn, b))
    for an, a, bn, b in pairs:
        for (n1, c1), (n2, c2) in ((B7_BUDGETS[1], B7_BUDGETS[0]), (B7_BUDGETS[0], B7_BUDGETS[2]), (B7_BUDGETS[0], B7_BUDGETS[1])):
            src = [b7_budget(c1, "b"), b7_budget(c2, "c")] + b7_census(a, "W", "b") + b7_census(b, "W", "c")
            bw_case(f"{an}_{n1}_to_{bn}_{n2}", src, cb.plan(a, c1), cb.plan(b, c2), out)
    for name, cfg, c in b7_edge_censuses():
        tighter = {"budget": dict(cfg["budget"], ram_budget_kib=cfg["budget"]["ram_budget_kib"] - 1)}
        src = [b7_budget(cfg, "b"), b7_budget(tighter, "c")] + b7_census(c, "W", "b") + b7_census(c, "W", "c")
        bw_case(name + "_minus_one", src, cb.plan(c, cfg), cb.plan(c, tighter), out)
    G, A, R = "green", "amber", "red"
    hand = [
        ("hand_all_kinds", [("keep", True, 3, [(0, G), (1, A), (2, R), (3, G)]), ("gone", True, 1, [(0, G)]),
                            ("spill", True, 2, [(0, G)]), ("unspill", False, 0, [(0, R)])],
         [("keep", True, 2, [(0, A), (1, G), (2, R), (4, A), (5, G)]), ("new", False, 1, [(0, R), (1, G)]),
          ("spill", False, 2, [(0, G)]), ("unspill", True, 4, [(0, G)])]),
        ("hand_calm", [("w", True, 5, [(0, R)])], [("w", True, 6, [(0, A), (1, G)])]),
        ("hand_empty_both", [], []),
        ("hand_all_gone", [("a", True, 1, [(0, G)]), ("b", False, 0, [])], []),
    ]
    for name, bws, cws in hand:
        bd_, cd_ = bw_raw(bws), bw_raw(cws)
        bw_case(name, bw_raw_lines("b", bd_) + bw_raw_lines("c", cd_), bd_, cd_, out)
    ok = [("w", True, 1, [(0, G)])]
    bad = [
        ("refuse_blank_id", [(" ", True, 1, [(0, G)])], ok),
        ("refuse_dup_world", ok, ok + ok),
        ("refuse_fits", [("w", 1, 1, [(0, G)])], ok),
        ("refuse_beacon", ok, [("w", True, 1, [(0, "blue")])]),
        ("refuse_dup_slot", [("w", True, 1, [(0, G), (0, R)])], ok),
        ("refuse_beacon_before_dup", ok, [("w", True, 1, [(0, G), (0, "Red")])]),
    ]
    for name, bws, cws in bad:
        bd_, cd_ = bw_raw(bws), bw_raw(cws)
        bw_case(name, bw_raw_lines("b", bd_) + bw_raw_lines("c", cd_), bd_, cd_, out)
    return out


# ---------------------------------------------------------------- G529 Budget Fathoms
BF_KINDS = [("--sweep-ram", "sweep_ram"), ("--sweep-disk", "sweep_disk")] + CB_KINDS


def bf_case(name, cfg, c, sr_, sd_, out):
    out.append(f"C {name}")
    out.append(b7_budget(cfg))
    out.extend(b7_census(c))
    out.append(f"S {'n' if sr_ is None else hx(sr_)} {'n' if sd_ is None else hx(sd_)}")
    try:
        r = bf.build(bf.to_report(c, cfg), bf.parse_list(sr_, "--sweep-ram"), bf.parse_list(sd_, "--sweep-disk"))
    except bf.FathomError as e:
        out.append(b7_refusal(e, BF_KINDS))
        return
    for dim in ("ram", "disk"):
        n, s = r["need_kib"][dim], r["slack_kib"][dim]
        out.append(f"O n {dim} {n['all_green']} {n['no_red']} {n['all_fit']} {n['deep']} "
                   f"{s['all_green']} {s['no_red']} {s['all_fit']} {s['deep']}")
    for w in r["worlds"]:
        out.append(f"O w {hx(w['world'])} {w['ram_fit_kib']} {w['disk_fit_kib']} "
                   + lst(f"{i['slot']}:{i['ram_green_kib']}:{i['ram_clear_kib']}:{i['disk_green_kib']}:{i['disk_clear_kib']}" for i in w["islands"]))
    for s in r["sweep"]:
        out.append(f"O s {s['dim']} {s['budget_kib']} {s['green']} {s['amber']} {s['red']} {s['worlds_spilling']} {s['verdict']}")
    n = r["now"]
    out.append(f"O now {n['green']} {n['amber']} {n['red']} {n['worlds_spilling']} {r['verdict']}")


def bf_lines():
    out = ["# disksaver budget_fathoms parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    for cname, c in b7_censuses():
        for bname, b in B7_BUDGETS:
            bf_case(f"{cname}_{bname}", b, c, "16384,40000, 39999,100000000" if bname == "shipped" else None,
                    "32768,4096,8000" if bname != "tight" else "1", out)
    for name, b, c in b7_edge_censuses():
        bf_case(name, b, c, "1,2", None, out)
    for name, b, c in b7_bad_censuses():
        bf_case(name, b, c, None, None, out)
    good = census([("a", [(0, 1)])])
    sweeps = [("sweep_leading_zeros", "007,7,0000000000000000000000040000", None),
              ("sweep_dupes_sorted", "9,3,9,3,1", "5,5"),
              ("refuse_sweep_zero", "0", None), ("refuse_sweep_empty", "", None), ("refuse_sweep_trailing_comma", "1,", None),
              ("refuse_sweep_sign", "+5", None), ("refuse_sweep_big", "100000001", None),
              ("refuse_sweep_long_digits", "1" * 30, None), ("refuse_sweep_disk_word", "1", "ten"),
              ("refuse_sweep_65", ",".join(str(i) for i in range(1, 66)), None),
              ("sweep_64", ",".join(str(i * 1000) for i in range(1, 65)), None),
              ("refuse_sweep_65_dupes", ",".join("5" for _ in range(65)), None),
              ("sweep_spaces", " 12 ,\t13", None),
              ("refuse_census_before_sweep", None, "0")]
    for name, a, d in sweeps:
        c = census([]) if name == "refuse_census_before_sweep" else good
        bf_case(name, B7_BUDGETS[0][1], c, a, d, out)
    return out


# ---------------------------------------------------------------- G533 Fleet Flags
FF_KINDS = [("realm_id must be", "realm")] + CB_KINDS


def ff_claim(c):
    rid = c["id"]
    vals = [str(c[k]) if k in c else "?" for k in ("worlds", "islands", "asset_definitions")]
    return f"M {'-' if rid is None else hx(rid)} " + " ".join(vals)


def ff_case(name, cfg, c, out):
    out.append(f"C {name}")
    out.append(b7_budget(cfg))
    out.extend(b7_census(c))
    for m in c.get("realms") or []:
        out.append(ff_claim(m))
    if c.get("realms") is None:
        out.append("M none")
    try:
        r = ff.muster(c, cfg)
    except ff.FlagError as e:
        out.append(b7_refusal(e, FF_KINDS))
        return
    for g in r["realms"]:
        out.append(f"O r {'-' if g['realm'] is None else hx(g['realm'])} {g['worlds']} {g['islands']} {g['asset_definitions']} "
                   f"{g['ram_kib']} {g['disk_kib']} {g['green']} {g['amber']} {g['red']} {g['worlds_spilling']} "
                   f"{hx(g['heaviest_world'])} {g['flag']}")
    for m in r["tally_mismatches"]:
        out.append(f"O m {'-' if m['realm'] is None else hx(m['realm'])} {m['field']} "
                   f"{'-' if m['claimed'] is None else m['claimed']} {m['found']}")
    out.append(f"O v {r['verdict']}")


def ff_realmed(worlds, realms=None):
    doc = census([(w, isl) for w, _, _, isl in worlds])
    for d, (_, rid, wad, _) in zip(doc["worlds"], worlds):
        if rid != "absent":
            d["realm_id"] = rid
        if wad is not None:
            d["asset_definitions"] = wad
    if realms is not None:
        doc["realms"] = realms
    return doc


def ff_lines():
    out = ["# disksaver fleet_flags parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    for cname, c in b7_censuses():
        for bname, b in B7_BUDGETS:
            ff_case(f"{cname}_{bname}", b, c, out)
    for name, b, c in b7_edge_censuses():
        ff_case(name, b, c, out)
    for name, b, c in b7_bad_censuses():
        ff_case(name, b, c, out)
    sb = B7_BUDGETS[0][1]
    hand = [
        ("hand_realms_heaviest_tie", [("b", "r", 5, [(0, 10)]), ("a", "r", 5, [(0, 10)]), ("c", None, 0, [(0, 1)])],
         [{"id": "r", "worlds": 2, "islands": 2, "asset_definitions": 10}, {"id": None, "worlds": 1}]),
        ("hand_mismatches", [("w1", "north", 3, [(0, 1), (1, 2)]), ("w2", "absent", None, [(0, 900)]), ("w3", "south", 7, [])],
         [{"id": "north", "worlds": 2, "islands": 2, "asset_definitions": 4}, {"id": "ghost", "worlds": 0, "islands": 1},
          {"id": "south", "asset_definitions": 7}, {"id": "north", "islands": 2}]),
        ("hand_no_claims_list", [("w", "x", 1, [(0, 1)])], None),
        ("hand_empty_claims", [("w", "x", 1, [(0, 1)]), ("v", None, None, [(0, 1)])], []),
        ("hand_amber_signal", [("w", "x", 0, [(0, 980)])], [{"id": "x", "worlds": 1}]),
        ("hand_spill_red", [("w", "x", 0, [(0, 1), (1, 1), (2, 1)])], None),
    ]
    for name, worlds, realms in hand:
        ff_case(name, sb, ff_realmed(worlds, realms), out)
    for name, rid in (("refuse_realm_blank", " "), ("refuse_realm_empty", ""), ("refuse_realm_number", 5)):
        ff_case(name, sb, ff_realmed([("ok", "r", 0, [(0, 1)]), ("bad", rid, 0, [(0, 1)])]), out)
    return out


# ---------------------------------------------------------------- batch 8 shared
def b8_jhex(obj, compact=False):
    """Python's json.dumps(obj, sort_keys=True) text, hex-encoded for the golden line."""
    kw = {"separators": (",", ":")} if compact else {}
    return hx(json.dumps(obj, sort_keys=True, **kw))


def b8_shex(s):
    return "x" + s.encode("utf-8", "surrogatepass").hex()


def b8_val(v):
    """A JSON scalar golden token: - null, iN int, s<hex> string, t/f bool."""
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "t" if v else "f"
    if isinstance(v, int):
        return f"i{v}"
    return "s" + b8_shex(v)[1:]


def b8_refusal(e, kinds):
    msg = str(e)
    for needle, kind in kinds:
        if needle in msg:
            return "O refused " + kind
    raise e


# ---------------------------------------------------------------- G531 Stray Cargo
SG_KINDS = [("nonempty list", "no_worlds"), ("duplicate world id", "world_id"), ("bad island", "bad_island"),
            ("bad asset", "bad_asset")]


def sg_lines_for(doc):
    out = []
    for w in doc["worlds"]:
        isl = lst(f"{'!' if not isinstance(i.get('slot'), int) or isinstance(i.get('slot'), bool) else i['slot']}:"
                  f"{'-' if i.get('asset_definitions') is None else i['asset_definitions']}" for i in w.get("islands") or [])
        claimed = w.get("assets_without_island")
        out.append(f"W {hx(w['id'])} {'-' if w.get('realm_id') is None else 'r'} {'-' if claimed is None else claimed} {isl}")
        for a in w.get("assets") or []:
            name = a.get("name")
            out.append(f"A {hx(name) if isinstance(name, str) else '!'} {b8_val(a.get('island_slot'))} {b8_val(a.get('file'))}")
    return out


def sg_case(name, doc, out):
    out.append(f"C {name}")
    out.extend(sg_lines_for(doc))
    try:
        r = sgc.survey(doc)
    except sgc.StrayError as e:
        out.append(b8_refusal(e, SG_KINDS))
        return
    for f in r["findings"]:
        out.append(f"O f {b8_jhex(f)}")
    c = r["counts"]
    out.append("O k " + " ".join(str(c[k]) for k in sgc.ERRORS + sgc.ADVISORIES))
    out.append(f"O v {r['verdict']} {r['hidden_cost_kib']['ram_kib']} {r['hidden_cost_kib']['disk_kib']} "
               f"{r['empty_hull_ram_kib']} {r['shared_disk_kib']}")


def sg_seeded(seed):
    doc = real_census()
    rng = random.Random(seed)
    files = ["assets/ark.glb", "assets/beacon.glb", "assets/crate.glb", ""]
    for w in doc["worlds"]:
        slots = [i["slot"] for i in w["islands"]]
        for i in w["islands"]:
            i["asset_definitions"] = rng.choice([0, 0, 1, 3, 12])
        for k in range(rng.randrange(0, 6)):
            slot = rng.choice(slots + [None, None, 77])
            w["assets"].append({"name": rng.choice(["ark", "beacon", f"crate{k}", "mast"]), "island_slot": slot,
                                "file": rng.choice(files + [None])})
        w["assets_without_island"] = sum(1 for a in w["assets"] if a.get("island_slot") is None) + rng.choice([0, 0, 1])
        if seed % 2:
            w["realm_id"] = rng.choice([None, "harbour"])
    return doc


def sg_doc(worlds):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions", "worlds": worlds}


def sgc_lines():
    out = ["# disksaver stray_cargo parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    sg_case("real", real_census(), out)
    for s in SEEDS:
        sg_case(f"real_seed{s}", sg_seeded(s), out)
    for k, v in SYN.items():
        sg_case(k, v, out)
    A = lambda n, s, f=None: {"name": n, "island_slot": s, "file": f}  # noqa: E731
    hand = [
        ("hand_every_kind", [
            {"id": "w1", "islands": [{"slot": 0, "asset_definitions": 0}, {"slot": 3, "asset_definitions": 2}],
             "assets": [A("ark", 3, "a.glb"), A("ark", None, "a.glb"), A("mast", 9), A("rope", None), A("sail", "3"), A("keel", True)],
             "assets_without_island": 5},
            {"id": "w0", "realm_id": "r", "islands": [{"slot": -2, "asset_definitions": 0}], "assets": [A("ark", -2, "a.glb")]},
        ]),
        ("hand_tidy", [{"id": "t", "realm_id": "r", "islands": [{"slot": 1, "asset_definitions": 4}], "assets": [A("a", 1, "x.glb")],
                        "assets_without_island": 0}]),
        ("hand_littered_only", [{"id": "l", "islands": [], "assets": [A("s", None, "f.glb")]}]),
        ("hand_dup_island_slot", [{"id": "d", "realm_id": "r", "islands": [{"slot": 1, "asset_definitions": 0}, {"slot": 1, "asset_definitions": 5}],
                                   "assets": [A("a", 1)]}]),
        ("hand_text_escapes", [{"id": "q\"\\", "islands": [], "assets": [A("tab\tname", None, "dir/\u00e9\u2603.glb"), A("\U0001f600", 4, "\x7f")]}]),
        ("hand_shared_three", [{"id": f"s{k}", "realm_id": "r", "islands": [{"slot": 0, "asset_definitions": 1}], "assets": [A("x", 0, "same.glb")]}
                               for k in (2, 0, 1)]),
        ("hand_dangling_order", [{"id": "o", "realm_id": "r", "islands": [], "assets": [A("b", 5), A("a", "x"), A("a", 4), A("a", False)]}]),
        ("refuse_no_worlds", []),
        ("refuse_blank_id", [{"id": " ", "islands": []}]),
        ("refuse_dup_world", [{"id": "a", "islands": []}, {"id": "a", "islands": []}]),
        ("refuse_island_slot", [{"id": "a", "islands": [{"slot": "1", "asset_definitions": 0}]}]),
        ("refuse_asset_name", [{"id": "a", "islands": [], "assets": [A(5, None)]}]),
        ("refuse_after_finding", [{"id": "a", "islands": [], "assets": [A("ok", None)]}, {"id": "b", "islands": [{"slot": True}]}]),
    ]
    for name, worlds in hand:
        sg_case(name, sg_doc(worlds), out)
    return out


# ---------------------------------------------------------------- G519 Memory Footprint
MF_KINDS = [("--top and --wins", "top_wins"), ("nonnegative integer", "negative"), ("budgets must be positive", "budget_positive"),
            ("duplicate world id", "world_id")]


def mf_case(name, src, report, top, wins, out):
    out.append(f"C {name}")
    out.extend(src)
    out.append(f"P {top} {wins}")
    try:
        r = mf.build(report, top, wins)
    except mf.FootprintError as e:
        out.append(b8_refusal(e, MF_KINDS))
        return
    for w in r["worlds"]:
        out.append(f"O w {hx(w['world'])} {w['ram_kib']} {w['disk_kib']} {w['ram_permille']} {w['disk_permille']} {int(w['over'])} "
                   f"{w['islands']} " + lst(f"{t['slot']}:{t['ram_kib']}:{t['disk_kib']}:{t['ram_share_permille']}" for t in w["top"]))
    t = r["totals"]
    out.append(f"O t {t['worlds']} {t['islands']} {t['ram_kib']} {t['disk_kib']} {t['peak_permille']}")
    for c in r["top_consumers"]:
        out.append(f"O c {hx(c['world'])} {c['slot']} {c['ram_kib']} {c['disk_kib']}")
    for c in r["wins"]:
        out.append(f"O n {c['rank']} {hx(c['world'])} {c['slot']} {c['action']} {c['ram_free_kib']} {c['disk_free_kib']} "
                   f"{int(c['world_over'])} {int(c['clears'])}")
    out.append(f"O v {r['verdict']}")


def mf_raw(budget, worlds):
    rb, db, warn = budget
    doc = {"format": "daedalus-census-budget", "version": 1,
           "budget": {"ram_budget_kib": rb, "disk_budget_kib": db, "warn_permille": warn},
           "worlds": [{"id": w, "islands": [{"slot": s, "ram_kib": r, "disk_kib": d, "asset_definitions": n} for s, r, d, n in isl]}
                      for w, isl in worlds]}
    src = [f"Q {rb} {db} {warn}"] + [f"R {hx(w)} " + lst(f"{s}:{r}:{d}:{n}" for s, r, d, n in isl) for w, isl in worlds]
    return doc, src


def mf_lines():
    out = ["# disksaver memory_footprint parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    for cname, c in b7_censuses():
        for bname, b in B7_BUDGETS:
            for top, wins in ((3, 10), (1, 1), (50, 100)):
                if bname != "shipped" and top != 3:
                    continue
                mf_case(f"{cname}_{bname}_{top}_{wins}", [b7_budget(b)] + b7_census(c), cb.plan(c, b), top, wins, out)
    for name, b, c in b7_edge_censuses():
        mf_case(name, [b7_budget(b)] + b7_census(c), cb.plan(c, b), 3, 10, out)
    hand = [
        ("hand_clears", (100, 100, 900), [("w", [(0, 60, 10, 1), (1, 50, 95, 2), (2, 1, 1, 0)])]),
        ("hand_ties_dup_slots", (100, 100, 500), [("t", [(1, 10, 10, 1), (1, 10, 10, 1), (0, 10, 10, 0)]), ("a", [(5, 10, 10, 1)])]),
        ("hand_laden_at_warn", (1000, 1000, 900), [("w", [(0, 900, 0, 0)])]),
        ("hand_just_under_warn", (1000, 1000, 900), [("w", [(0, 899, 0, 0)])]),
        ("hand_at_budget", (1000, 1000, 900), [("w", [(0, 1000, 1000, 3)])]),
        ("hand_just_over", (1000, 1000, 900), [("w", [(0, 1001, 10, 3)])]),
        ("hand_zero_ram_world", (10, 10, 0), [("z", [(0, 0, 0, 0)]), ("e", [])]),
        ("hand_no_worlds", (10, 10, 900), []),
        ("refuse_top_zero", (10, 10, 900), [("w", [])]),
        ("refuse_negative_ram", (10, 10, 900), [("w", [(0, -1, 0, 0)])]),
        ("refuse_zero_disk", (10, 0, 900), [("w", [])]),
        ("refuse_negative_warn", (10, 10, -1), [("w", [])]),
        ("refuse_dup_world", (10, 10, 900), [("w", []), ("w", [])]),
        ("refuse_blank_world", (10, 10, 900), [("\t", [])]),
    ]
    for name, budget, worlds in hand:
        doc, src = mf_raw(budget, worlds)
        mf_case(name, src, doc, 0 if name == "refuse_top_zero" else 2, 3, out)
    doc, src = mf_raw((10, 10, 900), [("w", [])])
    mf_case("refuse_wins_zero", src, doc, 1, 0, out)
    return out


# ---------------------------------------------------------------- G517 Budget Trend Ledger
BL_KINDS = [("run id must be", "run"), ("at must be", "at"), ("duplicate world id", "world_id"),
            ("nonnegative integer", "negative"), ("bad beacon or duplicate slot", "beacon_slot"), ("fits_all_resident", "fits"),
            ("--last must be", "last"), ("ledger is empty", "empty")]


def bl_raw(budget, worlds):
    doc = {"format": "daedalus-census-budget", "version": 1, "worlds": []}
    if budget is not None:
        doc["budget"] = budget
    src = ["B " + " ".join("?" if budget is None or k not in budget else ("-" if budget[k] is None else str(budget[k]))
                           for k in ("ram_budget_kib", "disk_budget_kib", "warn_permille"))]
    for w, fits, ram, disk, isl in worlds:
        doc["worlds"].append({"id": w, "fits_all_resident": fits, "total_ram_kib": ram, "total_disk_kib": disk,
                              "islands": [{"slot": s, "beacon": b} for s, b in isl]})
        src.append(f"R {hx(w)} {int(fits) if isinstance(fits, bool) else '!'} {ram} {disk} " + lst(f"{s}:{b}" for s, b in isl))
    return doc, src


def bl_case(name, runs, lasts, out):
    """runs = [(run, at, src_lines, report)]; records made in order, then diffs of neighbours and trends."""
    out.append(f"C {name}")
    recs = []
    for run, at, src, rep in runs:
        out.append(f"N {hx(run) if isinstance(run, str) else '!'} {'-' if at is None else (hx(at) if isinstance(at, str) else '!')}")
        out.extend(src)
        try:
            rec = bl.make_record(rep, run, at)
        except bl.LedgerError as e:
            out.append(b8_refusal(e, BL_KINDS))
            continue
        recs.append(rec)
        out.append("O r " + hx(bl.dumps_line(rec).rstrip("\n")))
    for a, b in zip(recs, recs[1:]):
        d = bl.diff(a, b)
        out.append(f"O d {hx(d['from'])} {hx(d['to'])} {d['verdict']}")
        for w in d["worlds"]:
            out.append(f"O dw {hx(w['world'])} {w['ram_delta_kib']} {w['disk_delta_kib']}")
        for f in d["findings"]:
            out.append(f"O df {hx(f['world'])} {f['kind']} {f.get('slot', '-')} {f.get('before', '-')} {f.get('after', '-')}")
    for last in lasts:
        out.append(f"L {last}")
        try:
            t = bl.trend(recs, last)
        except bl.LedgerError as e:
            out.append(b8_refusal(e, BL_KINDS))
            continue
        out.append(f"O t {lst(hx(r) for r in t['runs'])} {t['tally']}")
        for w in t["worlds"]:
            out.append(f"O tw {hx(w['world'])} {w['runs']} {lst(w['ram_kib'])} {w['net_kib']} {w['trend']}")


def bl_lines():
    out = ["# disksaver budget_ledger parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    cs = list(b7_censuses())
    for bname, b in B7_BUDGETS:
        runs = []
        for k, (cname, c) in enumerate(cs):
            runs.append((f"{bname}-{cname}", f"2026-10-{20 + k:02d}T00:00:00Z" if k % 3 else None,
                         [b7_budget(b)] + b7_census(c), cb.plan(c, b)))
        bl_case(f"ledger_{bname}", runs, (2, 3, 5, 100), out)
    seq = []
    for k, (cname, cfg, c) in enumerate(b7_edge_censuses()):
        seq.append((f"edge-{k}", "\u00e9t\u00e9 \"quoted\"", [b7_budget(cfg)] + b7_census(c), cb.plan(c, cfg)))
    bl_case("ledger_edges", seq, (2, 4), out)
    G, A, R = "green", "amber", "red"
    hand_runs = []
    for run, budget, worlds in [
        ("h1", {"ram_budget_kib": 100, "disk_budget_kib": 50, "warn_permille": 900},
         [("keep", True, 10, 5, [(2, G), (10, A), (9, R)]), ("drop", True, 1, 1, [(0, G)]), ("calm", True, 3, 3, [(0, G)])]),
        ("h2", {"ram_budget_kib": 100, "disk_budget_kib": None},
         [("keep", False, 20, 1, [(2, R), (10, G), (11, A)]), ("new_hot", True, 1, 1, [(0, A)]), ("new", True, 0, 0, []),
          ("calm", True, 3, 3, [(0, G)])]),
        ("h3", None, [("keep", True, 15, 1, [(2, G), (10, G)]), ("calm", False, 3, 3, [(0, G)])]),
        ("h4", {}, [("keep", True, 15, 1, [(2, G)])]),
    ]:
        doc, src = bl_raw(budget, worlds)
        hand_runs.append((run, None, src, doc))
    bl_case("ledger_hand", hand_runs, (1, 2, 3), out)
    ok_doc, ok_src = bl_raw({}, [("w", True, 1, 1, [(0, G)])])
    bad = [("blank", None, ok_src, ok_doc), (5, None, ok_src, ok_doc), ("r1", 7, ok_src, ok_doc)]
    for run, worlds in [("dupw", [("w", True, 1, 1, []), ("w", True, 1, 1, [])]), ("blankw", [(" ", True, 1, 1, [])]),
                        ("negslot", [("w", True, 1, 1, [(-1, G)])]), ("badbeacon", [("w", True, 1, 1, [(0, "Green")])]),
                        ("dupslot", [("w", True, 1, 1, [(0, G), (0, R)])]), ("fits", [("w", 1, 1, 1, [])]),
                        ("negram", [("w", True, -5, 1, [])]), ("negdisk", [("w", True, 1, -1, [])])]:
        doc, src = bl_raw({"ram_budget_kib": 1}, worlds)
        bad.append((run, None, src, doc))
    bad[0] = (" \t", None, ok_src, ok_doc)
    bl_case("ledger_refusals", bad, (2,), out)
    bl_case("ledger_empty", [], (2, 1), out)
    for cname, c in cs[1:6]:
        runs = [(f"{cname}-{bname}", None, [b7_budget(b)] + b7_census(c), cb.plan(c, b)) for bname, b in (B7_BUDGETS[1], B7_BUDGETS[0], B7_BUDGETS[2])]
        bl_case(f"ledger_tighten_{cname}", runs, (2, 3), out)
    one = cs[0][1]
    bl_case("ledger_single", [("only", "2026-10-29", [b7_budget(B7_BUDGETS[0][1])] + b7_census(one), cb.plan(one, B7_BUDGETS[0][1]))], (2,), out)
    return out


# ---------------------------------------------------------------- G544 Caulking Check
def cc_case(name, files, out):
    out.append(f"C {name}")
    for rel, raw in files:
        out.append(f"F {hx(rel)} x{raw.hex()}")
    findings = []
    for rel in sorted(dict(files)):
        findings += ck.check_bytes(rel, dict(files)[rel])
    order = {k: i for i, k in enumerate(ck.ORDER)}
    findings.sort(key=lambda x: (order[x["kind"]], x["file"]))
    for f in findings:
        out.append(f"O f {b8_jhex(f)}")
    counts = [sum(1 for x in findings if x["kind"] == k) for k in ck.ORDER]
    verdict = "leaking" if any(counts[:len(ck.ERRORS)]) else "weeping" if findings else "sound"
    out.append(f"O k {' '.join(map(str, counts))} {verdict}")


CC_JSON = [  # one .json file each; CPython 3.10 json messages (no trailing-comma or 4300-digit cases: those differ by version)
    b'{"a": 1, "b": [true, false, null, NaN, Infinity, -Infinity, 1.5e3, -0, 0.25]}\n',
    b'{"a": 1, "a": 2}\n', b'{"x": {"k": 1, "k": 2}, "x": 3}\n', b'{"x":1,"y":1,"y":2,"x":2}\n',
    b'{"\\u00e9": 1, "\xc3\xa9": 2}\n', b'{"\\ud83d\\ude00": 1, "\xf0\x9f\x98\x80": 2}\n', b'{"\\ud800": 1, "\\ud800": 2}\n',
    b'{"\\ud800\\u0041": 1}\n', b'{"": 1, "": 2}\n', b'[{"a": 1}, {"a": 1, "a": 1}]\n',
    b'', b'   \n', b'{', b'[', b'{"a"', b'{"a" 1}', b'{"a": }', b'{"a": 1 "b": 2}', b'{1: 2}', b'[1 2]',
    b'"abc', b'"a\\qb"', b'"\\u12"', b'"\\u12G4"', b'"\\u0041', b'"\\ud800\\uZZZZ"', b'"tab\there"', b'nul', b'tru', b'-',
    b'-Infinit', b'01', b'1.', b'1e', b'1e+', b'.5', b'{"a": 1} x', b'[] []', b'\xef\xbb\xbf{}', b'{"a": [1, {"b": "c\\"d"}]}',
    b'{"a":\t1,\r\n"b":2}', b'[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]',
    b'{"deep": [[[[[[[[[[{"a": 1, "a": 2}]]]]]]]]]]}', b'"\\/\\b\\f\\n\\r\\t\\\\\\""', b'{"a": "\x1f"}',
    b'123456789012345678901234567890', b'{"k": 1}\x00',
]


def cc_lines():
    out = ["# disksaver caulking_check parity v1: written by tools/streaming/disksaver_cpp_parity.py; do not edit"]
    real = []
    for rel in ("tools/world_census/fixtures/alpha.json", "tools/world_census/fixtures/beta.json",
                "tools/world_census/fixtures/bindings.json", "data/islands/disk-saver/ebb-eviction-v1.json",
                "data/islands/disk-saver/census-budget-v1.json"):
        with open(os.path.join(ROOT, rel), "rb") as f:
            real.append((rel, f.read()))
    cc_case("real_fixtures", real, out)
    for k, raw in enumerate(CC_JSON):
        cc_case(f"json_{k:02d}", [(f"j/case{k:02d}.json", raw)], out)
    text = [
        ("bom_only.md", b"\xef\xbb\xbf"), ("double_bom.json", b"\xef\xbb\xbf\xef\xbb\xbf{}\n"), ("crlf.txt", b"a\r\nb\r\n"),
        ("mixed.py", b"a\r\nb\nc\r\n"), ("lone_cr.txt", b"a\rb\n"), ("nofinal.yml", b"a: 1"), ("empty.txt", b""),
        ("trail.py", b"x = 1 \n\ty = 2\n  \tz\n"), ("trail.md", b"keep  \n\tTab\n"), ("tabs.yaml", b" \t- a\n\t- b\n- c\t\n"),
        ("tabs.txt", b"\tnot checked\n"), ("UPPER.JSON", b'{"a":1,"a":2}'), ("a/.json", b"{"), ("a/b.c/noext", b"x \n"),
        ("a/..json", b"{"), ("x.tar.json", b"[]\n"), ("bad1.txt", b"ok\xff"), ("bad2.txt", b"\xc3"), ("bad3.txt", b"\xe2\x82"),
        ("overlong.txt", b"a\xc0\xafb"), ("surrogate.txt", b"\xed\xa0\x80"), ("big.txt", b"\xf4\x90\x80\x80"),
        ("bom_bad.txt", b"\xef\xbb\xbfab\x80"), ("cont.txt", b"\x80abc"), ("f5.txt", b"\xf5\x80\x80\x80"),
        ("e0.txt", b"\xe0\x80\x80"), ("f0.txt", b"\xf0\x8f\xbf\xbf"), ("ok4.txt", b"\xf0\x9f\x98\x80\n"),
        ("lines.jsonl", b'{"a":1}\n\n   \n{"b":2,"b":3}\n{bad\n'), ("lines2.jsonl", b'{"a":1}\r\n[1,\r\n'),
        ("spaces.jsonl", b'\x0b\n\xc2\xa0\n\xe3\x80\x80\n{"ok":1}\n'), ("nel.jsonl", b'\xc2\x85\n{"x":1,"x":1}\n'),
        ("ctrl.jsonl", b'\x1c\n"a\x1fb"\n'),
    ]
    for rel, raw in text:
        cc_case("file_" + rel.replace("/", "_").replace(".", "_"), [(rel, raw)], out)
    cc_case("survey_sorted", [(rel, raw) for rel, raw in text[:12]], out)
    return out


GAMES = {"manifest_match": mm_lines, "twin_pilots": tp_lines, "quayside_shove": qs_lines, "sack_chute": sc_lines,
         "seal_roll": sr_lines, "channel_dash": cd_lines, "boom_defence": bd_lines, "salvage_sale": ss_lines,
         "rope_run": rr_lines, "belfry_changes": bc_lines, "tram_shunt": ts_lines,
         "watchfires": wf_lines, "tide_lock": tl_lines, "smugglers_island": si_lines, "harbour_cryptogram": hc_lines,
         "fleet_soundings": fs_lines, "quay_duel": qd_lines, "last_crate": lc_lines, "census_riddles": cr_lines,
         "tide_clocks": tc_lines, "lighthouse_leases": ll_lines, "tidemark_chunks": tm_lines,
         "bottle_census": bc_census_lines, "ebb_eviction": ee_lines, "beacon_watch": bw_lines,
         "budget_fathoms": bf_lines, "fleet_flags": ff_lines,
         "stray_cargo": sgc_lines, "memory_footprint": mf_lines, "budget_ledger": bl_lines,
         "caulking_check": cc_lines, "seed_spec": dss.lines,
         "gantry_sweep": gsp.lines,
         "buddy_berths": bbp.lines,
         "tidelinks_golf": tgp.lines}


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
