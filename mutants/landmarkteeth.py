#!/usr/bin/env python3
"""Teeth for LandmarkHeuristic — admissibility, which is the only property that matters here.

A heuristic that over-estimates does not crash, log, or fail a smoke test. It makes A* return a
route that is merely *good*, and every assertion phrased as "a path was found" still passes.
This class has the receipts: ADR-001 item 4 records the version that stored hop counts on
weighted grids over-estimating in 575 of 576 cells and returning a suboptimal route on all
twelve mazes tested, up to 36% worse than Dijkstra — and perfect mazes hid it completely,
because a spanning tree offers exactly one route and every heuristic finds it.

So the mutations below are not arbitrary breakages. Three of them reconstruct that exact bug
from three different directions:

  * mutation 3 sends weighted grids down the hop-count path at `estimate` time,
  * mutation 4 does it at `precompute` time, by failing to notice the weights,
  * mutation 5 restores the symmetric `|d(L,t) - d(L,a)|` bound in weighted mode, which assumes
    d(a,b) == d(b,a) — false under an entry-cost model, and the subtler half of the same error.

If any of those survives, the fix for a documented optimality bug is not pinned by anything, and
the next refactor can reintroduce it in silence.

Mutations 1 and 2 are the generic over-estimate: inflate an otherwise correct bound. A suite
that checks "landmark beats Manhattan" or "a path exists" will not notice; only a test that
compares h against true distance, or A*'s cost against Dijkstra's, can.

Two mutations were written, run, and then deleted rather than left here as permanent survivors,
because both were measured and neither is a defect:

  * Routing weighted grids through `hopEstimate` at estimate time looks like the ADR-001 bug and
    is not: in weighted mode `hopFields` is empty, so the mutant returns 0. Zero is admissible.
    A* degenerates toward Dijkstra and stays optimal — a performance regression with no
    correctness consequence, and no test should fail for it.
  * Removing the `dFrom < 0 || dTo < 0` guard cannot over-estimate either. Landmarks are chosen
    from the largest component, so a pair that sees a -1 field entry is a pair spanning
    components, whose true distance is infinite and which no admissibility check can fail on.
    The guard is defensive, and the mutation is inert.

Both were confirmed by measurement, not argument: a probe swept every ordered pair on a braided
weighted grid and on a deliberately disconnected one, counting admissibility violations. The
symmetric-bound mutation produced 7,454 of them (worst h = 9.94 against a true cost of 5.97);
these two produced zero.

A third was retired for a different reason. Dropping the inbound bound `d(s,L) - d(t,L)` leaves
the heuristic admissible but looser, so A* expands more nodes and still returns the optimal
route. Nothing fails, and arguably nothing should — but that does mean **weighted-mode tightness
is unpinned**, and a refactor could quietly halve the heuristic's value with no signal. Pinning
it is possible along the lines the lens tests already use (assert the sharper configuration does
measurably less work, via MazeStats expansions); it is left undone deliberately rather than
overlooked, and a permanent survivor in this list would have communicated that far worse than
this paragraph does.

Usage:  python3 mutants/landmarkteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
LH = REPO / "daedalus-core/src/main/java/com/daedalus/solver/LandmarkHeuristic.java"

MUT = [
    (LH, "unit-cost bound inflated by one (inadmissible)",
     "            int bound = Math.abs(dTo - dFrom);",
     "            int bound = Math.abs(dTo - dFrom) + 1;"),
    (LH, "weighted bound inflated by one (inadmissible)",
     "                best = Math.max(best, dLt - dLs);",
     "                best = Math.max(best, dLt - dLs + 1.0);"),
    (LH, "weights not noticed at precompute (the ADR-001 bug, upstream)",
     "        if (hasNonUnitWeights(grid)) {\n"
     "            return precomputeWeighted(grid, chooseLandmarks(grid, count));\n"
     "        }",
     "        if (false) {\n"
     "            return precomputeWeighted(grid, chooseLandmarks(grid, count));\n"
     "        }"),
    (LH, "symmetric bound restored in weighted mode (directed graph ignored)",
     "                best = Math.max(best, dLt - dLs);",
     "                best = Math.max(best, Math.abs(dLt - dLs));"),
]

CLASSES = ("LandmarkHeuristicTest", "LandmarkHeuristicWeightedTest",
           "SolverBraidedMazePropertyTest", "MazeMetricsWeightedDistanceTest",
           "WeightedRoutingTest", "BidirectionalOptimalityTest")
TESTS = ",".join(CLASSES)


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-core", "test",
                        "-Dtest=" + TESTS,
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=1800)
    return V.classify(p.returncode, p.stdout, V.failing_tests(p.stdout, *CLASSES))


originals = {p: p.read_text() for p in {m[0] for m in MUT}}
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:56s} -> SKIP (anchor x{orig.count(old)})", flush=True)
            survivors.append(name + " [anchor lost]")
            continue
        path.write_text(orig.replace(old, new))
        try:
            v = run_once()
        except subprocess.TimeoutExpired:
            v = "caught: timed out"
        finally:
            path.write_text(orig)
        if not V.is_catch(v):
            survivors.append(name)
        print(f"{name:56s} -> {v}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
