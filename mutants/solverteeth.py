#!/usr/bin/env python3
"""Teeth for the solver family — optimality, termination, and the claims in the prose.

`SolverBraidedMazePropertyTest` is the strongest test in the core module and it knows why it
exists: a perfect maze has exactly one route between any two cells, so every solver returns the
optimal path on every perfect-maze fixture whatever it does internally, and a suite built on them
proves nothing about optimality. It braids. It then holds every solver on the roster to three
properties — the returned path is a legal traversal, a complete solver finds a route wherever BFS
does, and an optimal solver matches BFS's length once there is route choice.

So this harness is not looking for unpinned optimality. It is asking a different question in three
parts.

**Does the property test cover the algorithms' own subtleties**, or only their outputs? Dial's
bucket arithmetic, IDA*'s bound update and bidirectional's meeting point are the three places
these algorithms classically go wrong, and each fails in a way that still returns *a* path.

**Are the performance claims claims?** The bidirectional solver's javadoc promises expansion of
the *smaller* frontier, "which preserves the b^(d/2) advantage" and is the stated reason its
first-touch stop is safe. Expanding the larger frontier returns identical paths, so every
correctness property stays green while the algorithm quietly becomes a slower BFS with two arrays.
A performance argument load-bearing for a correctness argument deserves a test.

**Do the panic paths hold?** Dial grows its bucket array on demand and Dial's own comment calls
out a stale-duplicate guard; both are one character from an index crash or a wrong distance.

**First run: 1 of 6. Final: 3 of 3, with three mutations retired as provably inert.** Only one of
the five survivors turned out to be a hole, and the other four are the more interesting result:
this solver family has three branches that *cannot be taken*, and a harness that reports them as
survivors is telling you the truth in the wrong units.

**Dial's decrease-key machinery is dead, all of it.** Deleting `tentative < dist[next]` from the
relaxation — a cell first reached expensively can never be improved, which is the textbook way
this algorithm fails — passes the entire core suite. The first reading was the obvious one: the
suite is uniform-cost, so weights will expose it. They do not. This engine uses an *entry-cost*
model — `Graph.edgeWeight` returns the weight of the destination cell, never a property of the
edge — so every edge into a node costs the same, buckets are scanned in ascending `k`, and a
node's first relaxation therefore always uses the smallest `k` any neighbour will be settled at.
Every later attempt is greater or equal. The branch cannot fire. Nor can the `settled[current] ||
dist[current] != k` guard that exists to discard the stale bucket entry such a relaxation would
leave behind: with no improving relaxation there is no duplicate entry to discard. Instrumented
over 640 weighted grids (four sizes, four braid factors, random weights 0-39 including zero-cost
cells) the improving branch fired **0 times in 231,734 relaxations** and the stale guard **0
times**. Both are documented in `DialSolver` as dead-by-contract and kept: the reason they are
dead lives in `Graph`, and the day `edgeWeight` becomes genuinely edge-dependent — a one-way ramp,
a door that costs more from one side — they come alive and a Dial without them returns wrong
distances quietly.

IDA*'s `bound = next` is the third: identical to `bound + 1` **for this solver**, because its `g`
advances by 1.0 per step, so the measured next bound on a unit-cost search is always one more than
the last.

`WeightedSolverOptimalityTest` was written under the wrong hypothesis and kept for the right one.
Weights do not expose Dial's relaxation, but they expose something nothing else in the suite
states: of the seven solvers `SolverBraidedMazePropertyTest` holds to BFS's *hop count*, only
Dijkstra, Dial and A* read `weightOf` at all. That split lived in `TrafficService`'s prose and in
no test. It also covers Dial's bucket growth, which needs a cell heavier than twice the array
length (64 buckets, so above 128) to reach.

The one real hole is now pinned. Expanding the *larger* frontier in `BidirectionalSolver`
returns identical paths, so every correctness property stayed green while the b^(d/2) advantage
the class javadoc promises quietly evaporated. Pinning it means asserting on expansion counts,
which is a performance assertion in a correctness suite — worth doing, and worth doing on purpose.
Two measurements were needed first, and each killed a version of the test:

* **"Fewer cells than BFS" does not discriminate.** The mutant still expands fewer cells than BFS
  on every fixture — by about half a percent. It beats BFS by a nose and passes. The margin is
  what separates them: 0.67 of BFS's expansions with the balance in place, 0.997 without it. So
  the threshold *is* the assertion, and 0.85 sits in the gap between a measured worst case of
  0.743 and a measured mutant best of 0.991.
* **Perfect mazes are the wrong fixture**, and not for the usual reason. Over 120 perfect mazes at
  four sizes the real solver expanded *more* cells than BFS on 34 of them. The advantage is
  exponential in branching factor and a perfect maze is a tree of one-wide corridors; the
  goal-side search also pays for dead ends behind the goal that BFS never reaches, because BFS
  stops when it pops the goal. Braiding restores the branching. The class javadoc's "~40% the
  explored count of plain BFS" was the best case (0.384 measured) reported as the typical one —
  the mean over 30 perfect 101x101 mazes is 0.877 with a worst of 1.296. Header corrected with
  the measured table.

Usage:  python3 mutants/solverteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
S = REPO / "daedalus-core/src/main/java/com/daedalus/solver/solvers"

BIDI = S / "BidirectionalSolver.java"
DIAL = S / "DialSolver.java"
IDA = S / "IDAStarSolver.java"

MUT = [
    (BIDI, "the larger frontier is expanded (the b^(d/2) claim is dropped)",
     "            int meet = (qs.size() <= qg.size())",
     "            int meet = (qs.size() >= qg.size())"),
    (DIAL, "the bucket array grows one slot short",
     "                            buckets = Arrays.copyOf(buckets, Math.max(tentative + 1, buckets.length * 2));",
     "                            buckets = Arrays.copyOf(buckets, Math.max(tentative, buckets.length * 2));"),
    (DIAL, "the last bucket is never scanned",
     "        for (int k = 0; k <= maxKey; k++) {",
     "        for (int k = 0; k < maxKey; k++) {"),
    # Retired, not dropped: `if (dist[next] == UNREACHED || tentative < dist[next])` reduced to
    # `if (dist[next] == UNREACHED)` survives everything, because under the entry-cost model the
    # improving branch is unreachable — 0 firings in 231,734 instrumented relaxations. Leaving it
    # in the list would report a permanent survivor for a mutation that changes no behaviour.
    # Same for the `settled[current] || dist[current] != k` guard downstream of it. See above.
]

CLASSES = ("SolverBraidedMazePropertyTest", "WeightedSolverOptimalityTest",
           "BidirectionalOptimalityTest", "DialSolverTest", "IDAStarBudgetTest",
           "WeightedRoutingTest")
TESTS = ",".join(CLASSES)


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-core", "test",
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
            print(f"{name:60s} -> SKIP (anchor x{orig.count(old)})", flush=True)
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
        print(f"{name:60s} -> {v}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    V.release()
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
