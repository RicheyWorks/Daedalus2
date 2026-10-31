#!/usr/bin/env python3
"""Sluicegate parity fixture (Python rules are the authority; the native core must match from seed alone).

Writes engines/unreal/core-test/sluicegate_parity.txt from tools/minigames/sluicegate.py for a fixed set of
seeds x difficulties, playing demo_action to the end:

  game s=<seed> d=<difficulty> size=<n> turns=<t> gates=<g> head=<r,c> mill=<r,c|-> cisterns=<r,c;...> field=<rows of . and #;...>
  move t=<turn> act=<r,c|wait> wet=<r,c;...> gates=<r,c;...|-> left=<g> filled=<k> turns=<t> score=<s> over=<0|1> won=<0|1> res=<text>
  end  score=<s> won=<0|1> filled=<k> turns=<t>

`wet` is the full wet list in wetting order, because that order decides where the next push goes.

Edge-case vectors follow the seeded fields: a hand-set field (no seed) and one scripted action each, so both sides
prove the rule corners (push order, a gate turning the flow, the flood, the dry channel, the closing headgate) and
the gatekeeper's pick on states the seeds may never produce:

  vector <name> size=<n> turns=<t> gates=<g> flow=<f> head=<r,c> mill=<r,c|-> cisterns=<...> field=<...> wet=<...> gated=<...|->
  step act=<r,c|wait> demo=<r,c|wait> wet=<...> gates=<...> left=<g> filled=<k> turns=<t> score=<s> over=<0|1> won=<0|1> res=<text>

DaedalusSluicegateCore.h seeds its own CPython-compatible stream from "sluicegate:<seed>:<difficulty>", so the
generated field, cisterns and mill are the parity check, and the gatekeeper (rollout per candidate gate, waits as the
baseline) must match gate for gate. Run with --check to verify the committed file is current.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sluicegate as sg  # noqa: E402

SEEDS = (0, 1, 2, 3, 7, 11, 42, 1337, 2026, 65535)
DIFFS = ("easy", "normal", "hard")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "engines", "unreal", "core-test",
                   "sluicegate_parity.txt")


def cells(v):
    return ";".join("%d,%d" % (r, c) for r, c in v) or "-"


def field_text(g):
    return ";".join("".join("." if x == sg.CHANNEL else "#" for x in row) for row in g.field)


def play(seed, difficulty):
    g = sg.Game(seed, difficulty)
    lines = ["game s=%d d=%s size=%d turns=%d gates=%d head=%d,%d mill=%s cisterns=%s field=%s"
             % (seed, difficulty, g.size(), g.turns, g.gates_left, g.head[0], g.head[1],
                cells([g.mill]) if g.mill is not None else "-", cells(g.cisterns), field_text(g))]
    turn = 0
    while not g.over:
        a = g.demo_action()
        res = g.step(a)
        turn += 1
        lines.append("move t=%d act=%s wet=%s gates=%s left=%d filled=%d turns=%d score=%d over=%d won=%d res=%s"
                     % (turn, a, cells(g.wet), cells(g.gates), g.gates_left, g.filled, g.turns, g.score, int(g.over),
                        int(g.won), res))
    lines.append("end  score=%d won=%d filled=%d turns=%d" % (g.score, int(g.won), g.filled, g.turns))
    return lines


VECTORS = (
    # name, rows ('.' channel, '#' rock, 'H' headgate), cisterns, mill, gates left, turns, flow, wet so far, gates so far, action
    ("push_east_then_south", ["..H..", ".....", ".....", ".....", "....."], [(4, 4)], None, 4, 10, 2, [], [], "wait"),
    ("gate_turns_the_flow", ["..H..", ".....", ".....", ".....", "....."], [(4, 4)], None, 4, 10, 2, [], [], "0,3"),
    ("second_push_walks_the_wet_list", ["..H..", ".....", ".....", ".....", "....."], [(4, 4)], None, 4, 9, 2, [(0, 3), (1, 2)], [], "wait"),
    ("cistern_fills_and_wins", ["H##", ".##", ".##"], [(2, 0)], None, 3, 4, 1, [(1, 0)], [], "wait"),
    ("mill_floods", ["H.#", "..#", "###"], [(1, 1)], (1, 0), 2, 5, 2, [], [], "wait"),
    ("headgate_closes", ["H.#", "..#", "##."], [(2, 2)], None, 2, 1, 2, [(0, 1)], [], "wait"),
    ("channel_runs_dry", ["H.#", "###", "..."], [(2, 0)], None, 2, 9, 2, [(0, 1)], [], "wait"),
    ("flood_and_fill_together_lose", ["H..", "...", "..."], [(1, 0)], (0, 1), 2, 5, 2, [], [], "wait"),
    ("gatekeeper_gates_the_throat", ["#H#", "...", ".#."], [(2, 0)], (2, 2), 3, 6, 1, [], [], "wait"),
    ("gatekeeper_waits_when_safe", ["#H#", "#.#", "#.#"], [(2, 1)], None, 3, 6, 1, [], [], "wait"),
)


def vector(name, rows, cisterns, mill, gates, turns, flow, wet, gated, action):
    g = sg.Game(1, "easy")
    s = len(rows)
    g.cfg = dict(g.cfg, size=s, cisterns=len(cisterns), gates=gates + len(gated), turns=turns, flow=flow)
    g.field = [[sg.ROCK if ch == "#" else sg.CHANNEL for ch in row] for row in rows]
    g.head = [0, rows[0].index("H")]
    g.wet = [list(g.head)] + [list(w) for w in wet]
    g.cisterns = [list(c) for c in cisterns]
    g.mill = list(mill) if mill else None
    g.gates, g.gates_left, g.turns = [list(x) for x in gated], gates, turns
    g.filled = sum(1 for c in g.cisterns if c in g.wet)
    lines = ["vector %s size=%d turns=%d gates=%d flow=%d head=%d,%d mill=%s cisterns=%s field=%s wet=%s gated=%s"
             % (name, s, turns, gates, flow, g.head[0], g.head[1], cells([g.mill]) if g.mill else "-", cells(g.cisterns),
                field_text(g), cells(g.wet), cells(g.gates))]
    demo = g.demo_action()
    res = g.step(action)
    lines.append("step act=%s demo=%s wet=%s gates=%s left=%d filled=%d turns=%d score=%d over=%d won=%d res=%s"
                 % (action, demo, cells(g.wet), cells(g.gates), g.gates_left, g.filled, g.turns, g.score, int(g.over),
                    int(g.won), res))
    return lines


def generate():
    out = ["# sluicegate_parity.txt: generated by tools/minigames/sluicegate_parity.py from sluicegate.py (Python rules "
           "are the authority). %d seeds x %s, demo_action. Do not hand-edit." % (len(SEEDS), "/".join(DIFFS))]
    for d in DIFFS:
        for s in SEEDS:
            out += play(s, d)
    for v in VECTORS:
        out += vector(*v)
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed file differs")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    text = generate()
    if a.check:
        with open(a.out, encoding="utf-8") as fh:
            same = fh.read() == text
        print("parity file %s" % ("current" if same else "STALE"))
        return 0 if same else 1
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s (%d lines)" % (os.path.normpath(a.out), text.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
