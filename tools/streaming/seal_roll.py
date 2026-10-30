# SPDX-License-Identifier: MIT
"""Seal Roll (G560, disk-saver): tip a sealed cargo cube across the quay to stamp every mark.

Python dev tooling only; nothing here runs inside Unreal. A seed lays out a walled 7x7 quay with
a few bollards. Each census island (tools/world_census output, read-only; up to four) gets a
chalk mark on the cobbles, and there is one dock square. Sealwright Cornelius has a heavy cube
with the harbour seal on one face. He cannot lift it, only tip it over an edge: north, south,
east or west, one square at a time, and the seal turns with it.

A mark is stamped when the cube comes to rest on it with the seal facing up. Stamp every mark,
then finish on the dock, in as few tips as possible. The par is an exact breadth-first search
over (square, which way the seal faces, marks stamped). The tests check it against an
independent solver that turns the seal as a 3-D vector.

  verdict   true      every mark stamped and the cube on the dock, in par tips,
            wobbly    the same, in more tips,
            off_mark  a mark unstamped or the cube not on the dock.

  python tools/streaming/seal_roll.py CENSUS.json [--seed N] [--tips NNESW... | --auto] [--json]

Map: # wall, letters a-d marks (capital once stamped), D dock, @ the cube.
Deterministic, stdlib only, no clock. Exit 0 = printed or graded, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import random
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-seal-roll"
VERDICTS = ("true", "wobbly", "off_mark")
SIZE = 7
MAX_MARKS = 4
SIDES = ("up", "down", "north", "south", "east", "west")
MOVES = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
# where the seal goes when the cube tips in each direction
TIP = {
    "N": {"up": "north", "north": "down", "down": "south", "south": "up"},
    "S": {"up": "south", "south": "down", "down": "north", "north": "up"},
    "E": {"up": "east", "east": "down", "down": "west", "west": "up"},
    "W": {"up": "west", "west": "down", "down": "east", "east": "up"},
}


class RollError(ValueError):
    pass


def tip(pos, seal, d):
    dr, dc = MOVES[d]
    return (pos[0] + dr, pos[1] + dc), TIP[d].get(seal, seal)


def labels_for(census_doc):
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise RollError(str(e))
    labels = sorted(f"{w}:{s}" for w, il in worlds for s, _ in il)
    if not labels:
        raise RollError("census has no islands to stamp")
    return labels[:MAX_MARKS]


def solve(walls, marks, dock, start, seal="up"):
    """(par, tips string) or (None, None)."""
    full = (1 << len(marks)) - 1
    idx = {p: i for i, p in enumerate(marks)}
    m0 = (1 << idx[start]) if start in idx and seal == "up" else 0
    s0 = (start, seal, m0)
    prev = {s0: None}
    q = deque([s0])
    while q:
        s = q.popleft()
        if s[2] == full and s[0] == dock:
            path = []
            while prev[s] is not None:
                s, d = prev[s]
                path.append(d)
            return len(path), "".join(reversed(path))
        for d in "NSEW":
            p, sl = tip(s[0], s[1], d)
            if p in walls:
                continue
            m = s[2] | (1 << idx[p]) if (p in idx and sl == "up") else s[2]
            t = (p, sl, m)
            if t not in prev:
                prev[t] = (s, d)
                q.append(t)
    return None, None


def quay(census_doc, seed=0):
    labels = labels_for(census_doc)
    key = f"{census_doc.get('snapshot_date')}|{','.join(labels)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    border = {(r, c) for r in range(SIZE) for c in range(SIZE) if r in (0, SIZE - 1) or c in (0, SIZE - 1)}
    inner = sorted({(r, c) for r in range(SIZE) for c in range(SIZE)} - border)
    for _ in range(100):
        walls = frozenset(border | set(rng.sample(inner, rng.randint(3, 6))))
        floor = [p for p in inner if p not in walls]
        pick = rng.sample(floor, len(labels) + 2)
        marks, dock, start = tuple(pick[:len(labels)]), pick[-2], pick[-1]
        par, plan = solve(walls, marks, dock, start)
        if par is not None:
            return {"labels": labels, "walls": walls, "marks": marks, "dock": dock,
                    "start": start, "par": par, "plan": plan}
    raise RollError("could not lay out a quay for this seed")


def draw(q, pos, stamped):
    rows = []
    for r in range(SIZE):
        row = ""
        for c in range(SIZE):
            p = (r, c)
            if p in q["walls"]:
                row += "#"
            elif p == pos:
                row += "@"
            elif p in q["marks"]:
                i = q["marks"].index(p)
                row += "ABCD"[i] if i in stamped else "abcd"[i]
            elif p == q["dock"]:
                row += "D"
            else:
                row += " "
        rows.append(row.rstrip())
    return rows


def play(census_doc, seed=0, tips=None, auto=False):
    q = quay(census_doc, seed)
    r = {"format": FORMAT, "version": 1, "seed": seed, "par": q["par"],
         "marks": {"abcd"[i]: l for i, l in enumerate(q["labels"])},
         "start": draw(q, q["start"], set())}
    if auto:
        tips = q["plan"]
    if tips is None:
        r["verdict"] = None
        return r
    tips = tips.strip().upper()
    pos, seal = q["start"], "up"
    stamped = {q["marks"].index(pos)} if pos in q["marks"] else set()
    for i, d in enumerate(tips, 1):
        if d not in MOVES:
            raise RollError(f"tip {i}: {d!r} is not N, S, E or W")
        p, sl = tip(pos, seal, d)
        if p in q["walls"]:
            raise RollError(f"tip {i}: {d} runs into a wall or bollard")
        pos, seal = p, sl
        if pos in q["marks"] and seal == "up":
            stamped.add(q["marks"].index(pos))
    done = len(stamped) == len(q["marks"]) and pos == q["dock"]
    r.update({"tips": tips, "count": len(tips), "stamped": sorted("abcd"[i] for i in stamped),
              "seal": seal, "on_dock": pos == q["dock"], "final": draw(q, pos, stamped)})
    r["verdict"] = ("true" if len(tips) <= q["par"] else "wobbly") if done else "off_mark"
    return r


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise RollError(f"census: {e}")


def text(r):
    marks = ", ".join(f"{k}={v}" for k, v in r["marks"].items())
    lines = [f"seal roll: marks {marks}; par {r['par']} tips; seed {r['seed']}"]
    lines += ["  " + row for row in (r["final"] if r["verdict"] else r["start"])]
    if r["verdict"]:
        lines.append(f"verdict: {r['verdict']} ({r['count']} tips, stamped {len(r['stamped'])}/{len(r['marks'])}, "
                     f"seal {r['seal']}, {'on' if r['on_dock'] else 'off'} the dock, par {r['par']})")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seal Roll: tip a sealed cube to stamp every census mark.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--tips", help="tips as a string of N S E W")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = play(_load(a.census), a.seed, a.tips, a.auto)
    except RollError as e:
        print(f"seal_roll: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
