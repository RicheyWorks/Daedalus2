# SPDX-License-Identifier: MIT
"""Golden outputs for the C++17 ports of the DiskSaver minigame cores (G573 batch 1).

Each game's Python tool lays out the puzzle (its seeded layout stays in Python: the C++ side
never reimplements Python's random) and then plays a fixed set of move lists through the real
play() path. The layout, the par plan and every result or refusal go into
engines/unreal/core-test/disksaver_<game>_parity.txt, and the header-only
DaedalusDiskSaver<Game>Core.h ports replay every line in disksaver_<game>_core_test.cpp.

Batch 1: G556 Manifest Match, G557 Twin Pilots, G558 Quayside Shove, G559 Sack Chute.
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
import census_budget as cb  # noqa: E402
import manifest_match as mm  # noqa: E402
import quayside_shove as qs  # noqa: E402
import sack_chute as sc  # noqa: E402
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


GAMES = {"manifest_match": mm_lines, "twin_pilots": tp_lines, "quayside_shove": qs_lines, "sack_chute": sc_lines}


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
