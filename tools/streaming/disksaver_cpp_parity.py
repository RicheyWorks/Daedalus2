# SPDX-License-Identifier: MIT
"""Golden outputs for the C++17 ports of the DiskSaver minigame cores (G573 batch 1, G574 batch 2, G575 batch 3, G576 batch 4, G577 batch 5).

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
import census_riddles as cr  # noqa: E402
import harbour_cryptogram as hc  # noqa: E402
import last_crate as lc  # noqa: E402
import channel_dash as cd  # noqa: E402
import fleet_soundings as fs  # noqa: E402
import manifest_match as mm  # noqa: E402
import quay_duel as qd  # noqa: E402
import quayside_shove as qs  # noqa: E402
import rope_run as rr  # noqa: E402
import sack_chute as sc  # noqa: E402
import salvage_sale as ss  # noqa: E402
import seal_roll as sr  # noqa: E402
import smugglers_island as si  # noqa: E402
import tide_lock as tl  # noqa: E402
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


GAMES = {"manifest_match": mm_lines, "twin_pilots": tp_lines, "quayside_shove": qs_lines, "sack_chute": sc_lines,
         "seal_roll": sr_lines, "channel_dash": cd_lines, "boom_defence": bd_lines, "salvage_sale": ss_lines,
         "rope_run": rr_lines, "belfry_changes": bc_lines, "tram_shunt": ts_lines,
         "watchfires": wf_lines, "tide_lock": tl_lines, "smugglers_island": si_lines, "harbour_cryptogram": hc_lines,
         "fleet_soundings": fs_lines, "quay_duel": qd_lines, "last_crate": lc_lines, "census_riddles": cr_lines}


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
