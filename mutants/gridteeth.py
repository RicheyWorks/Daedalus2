#!/usr/bin/env python3
"""Teeth for MazeGrid — the data structure everything else is built on.

63 test files reference this class and no mutation had ever been aimed at it, which is a
specific and common shape of blind spot: heavily *used* is not the same as *attacked*. A class
used by everything is exercised constantly and asserted about rarely, because each caller tests
its own concern and takes the substrate for granted.

The guarantees worth breaking here are the ones every layer above silently assumes:

  * `carve` opens **both** sides of a wall. A one-sided carve produces a grid where `a` lists
    `b` as an open neighbour and `b` does not list `a` — passable one way. Solvers would still
    find routes, generators would still report success, and only a property test looking for
    symmetry would notice. `fuzzteeth.py` pins this at the *generator* level by breaking Binary
    Tree; nothing pins it at the level where the invariant actually lives.
  * `openNeighbors` filters to in-bounds cells. Drop the check and a border cell's neighbour
    list escapes the grid, which surfaces as an ArrayIndexOutOfBounds somewhere far away.
  * `directionBetween` is what makes `carve(Point, Point)` refuse non-adjacent pairs. Widen it
    and diagonal or distant "carves" silently succeed, opening a wall between the wrong cells.
  * `markVisited` used to keep a fast boolean array and the Cell objects in sync. **That array is
    gone as of 2026-08-02**, on the evidence this harness produced: see below.
  * The constructor rejects non-positive dimensions, and `carve(Point, Point)` refuses pairs
    that do not share a wall. Both are documented contracts, both were unpinned, and both are
    now covered by MazeGridContractTest.

Three mutations were written, measured, and removed as unreachable rather than left here as
standing survivors. Each is defensive code that no production path can reach:

  * Dropping the in-bounds filter in `openNeighbors` changes nothing, because a border cell's
    outward wall is never open: `carve(Cell, Direction)` returns early when the neighbour is off
    the grid, and RecursiveDivision — the one place that opens a wall directly — guards with
    `inBounds` itself.
  * Removing the Cell sync from `markVisited`, and the Cell loop from `clearVisited`, were inert
    for a more interesting reason. **Nothing in production called `grid.markVisited(Point)` or
    `grid.isVisited(Point)` at all.** The `boolean[][]` the class comment labelled "THE BIG SPEED
    WIN" was written by nobody and read by nobody; every generator uses the Cell-level API
    directly, and no code outside the generators reads visited state in any form.

    That finding was acted on. Before deleting the array it was measured, interleaved A/B at
    300x300, best of five: recursive-backtracker 71.2ms -> 57.5ms, prims 115.8 -> 98.8,
    aldous-broder 859.8 -> 864.4 (its random walk dominates, and it is the control), copy()
    51.5 -> 49.1. Removing the "speed win" was never slower across eight paired runs, and it drops
    rows*cols bytes per grid and per copy — which the living-maze tick allocates every two
    seconds. The real gain is that two mutable copies of one fact, held in step by a single line,
    can no longer disagree; `MazeGridContractTest` pins that the two views are one flag.

Usage:  python3 mutants/gridteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
GRID = REPO / "daedalus-core/src/main/java/com/daedalus/engine/MazeGrid.java"

MUT = [
    (GRID, "carve opens only the near side (one-way passages)",
     "        from.open(d);\n        to.open(d.opposite());",
     "        from.open(d);"),
    (GRID, "carve opens only the far side",
     "        from.open(d);\n        to.open(d.opposite());",
     "        to.open(d.opposite());"),
    (GRID, "carve reflects the wrong wall on the far side",
     "        to.open(d.opposite());",
     "        to.open(d);"),
    (GRID, "openNeighbors ignores the wall and returns every neighbour",
     "            if (here.isOpen(d)) {",
     "            if (true) {"),
    (GRID, "directionBetween accepts a non-adjacent pair as NORTH",
     "        if (dr == -1 && dc == 0) return Direction.NORTH;",
     "        if (dr <= -1 && dc == 0) return Direction.NORTH;"),
    (GRID, "a zero-or-negative dimension is accepted",
     "        if (rows < 1 || cols < 1) {",
     "        if (false) {"),
]

# Spans two modules on purpose. The invariant that `carve` opens both sides is asserted by
# GeneratorInvariantFuzzTest, which lives in daedalus-server even though the code it protects is
# in daedalus-core — so a core-only run reports a false survivor for the most important mutation
# here. mutants/README.md warns about exactly this ("a guarantee may be pinned from a different
# module than the code implementing it"); this is that warning with a name.
CLASSES = ("MazeGridContractTest", "PerfectMazePropertyTest", "MazeGridCopyTest", "WeightedMazeGridTest",
           "WeightedRoutingTest", "GeneratorConnectivityTest", "SolverBraidedMazePropertyTest",
           "AsciiMazeVisualizerTest", "GeneratorInvariantFuzzTest", "TileGridProjectionTest")
TESTS = ",".join(CLASSES)


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-core,daedalus-server",
                        "-am", "test",
                        "-Dtest=" + TESTS,
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=1800)
    return V.classify(p.returncode, p.stdout, V.failing_tests(p.stdout, *CLASSES))


V.restore_on_signal()
originals = {p: p.read_text() for p in {m[0] for m in MUT}}
V.snapshot(originals)
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:52s} -> SKIP (anchor x{orig.count(old)})", flush=True)
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
        print(f"{name:52s} -> {v}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    V.release()
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
