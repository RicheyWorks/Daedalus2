#!/usr/bin/env python3
"""Teeth for HeuristicLensServiceTest (ADR-007 idea 8).

Seven mutations, all caught — but only after a survivor changed the feature.

`expandedAboveOptimal` counts cells A* touched above the optimal cost, which must be zero for an
admissible heuristic. The original test asserted exactly that, and a mutation that simply never
incremented the counter SURVIVED: an assertion that can only ever confirm zero cannot tell a
working counter from a dead one. The fix was to give the counter something real to detect, which
meant adding a deliberately inadmissible heuristic (Manhattan x3) to the service. Measured on a
31x31 dungeon it cuts expansions from 341 to 213 and returns a 96-step route where the best is
88 — so the check now has a case that must fire, and the product gained an honest demonstration
of what admissibility is worth.

Usage:  python3 mutants/lensteeth.py
"""

import pathlib, re, subprocess
import verdict as V
REPO = pathlib.Path(__file__).resolve().parent.parent
T = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/HeuristicLensService.java"
orig = T.read_text()
MUT = [
 # Re-aimed 2026-08-01: the classifier moved from exact float comparison
 # (`f < optimal` / `f == optimal`) to an epsilon band (`delta < -EPSILON` /
 # `delta <= EPSILON`). Both mutations below had silently reported SKIP since that
 # refactor -- and nobody saw it, because this script could not start at all.
 ("must-expand swallows the tie band", "                if (delta < -EPSILON) {",
  "                if (delta <= EPSILON) {"),
 ("tie folded into must", "                } else if (delta <= EPSILON) {\n                    bands[r][c] = BAND_TIE;\n                    tie++;",
  "                } else if (delta <= EPSILON) {\n                    bands[r][c] = BAND_MUST_EXPAND;\n                    mustExpand++;"),
 # Aimed at the refactor itself: EPSILON is what makes the tie band a band rather than an
 # equality test, so widening it should be visible. The first version of this mutation
 # scaled `delta` by 1e-9 instead and duly "survived" -- proving nothing, because path
 # costs are integers and EPSILON is 1e-9, so every comparison landed exactly where it
 # had before. An inert mutation is the most expensive kind: it reads as a gap in the
 # tests and sends you writing an assertion for a hole that is not there.
 ("epsilon widened until every cell ties",
  "private static final double EPSILON = 1e-9;",
  "private static final double EPSILON = 1e9;"),
 ("above-optimal check disabled", "                    if (expanded.contains(p)) {\n                        expandedAbove++;\n                    }", "                    if (false) {\n                        expandedAbove++;\n                    }"),
 ("landmark ignored, always manhattan", "            case LANDMARK -> LandmarkHeuristic.precompute(grid, 4)::estimate;",
  "            case LANDMARK -> Heuristics.MANHATTAN;"),
 ("inflation neutered", "            case INFLATED -> (from, to) -> INFLATION * Heuristics.MANHATTAN.applyAsDouble(from, to);",
  "            case INFLATED -> Heuristics.MANHATTAN;"),
 ("unreachable counted as reachable", "                if (fromStart[r][c] < 0 || optimal < 0) {", "                if (false) {"),
 ("cap ignored", "        if (cells > maxFieldCells) {", "        if (false) {"),
]
for name, old, new in MUT:
    if orig.count(old) != 1:
        print(f"{name:36s} -> SKIP (anchor x{orig.count(old)})", flush=True); continue
    T.write_text(orig.replace(old, new))
    try:
        p = subprocess.run(["mvn","-B","-ntp","-pl","daedalus-server","test",
            "-Dtest=HeuristicLensServiceTest","-Dsurefire.failIfNoSpecifiedTests=false",
            "-Dcheckstyle.skip","-Dspotbugs.skip","-Djacoco.skip"],
            cwd=REPO, capture_output=True, text=True, timeout=600)
        failed = sorted({m for m in re.findall(r"HeuristicLensServiceTest\.(\w+)", p.stdout)})
        v = V.classify(p.returncode, p.stdout, failed)
    except subprocess.TimeoutExpired:
        v = "caught: timed out"
    finally:
        T.write_text(orig)
    print(f"{name:36s} -> {v}", flush=True)
T.write_text(orig)
print("restored")
