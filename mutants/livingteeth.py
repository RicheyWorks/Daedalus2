#!/usr/bin/env python3
"""Teeth for LivingMazeService — erosion's bounds, its determinism, and its scheduling.

The sibling of `trafficteeth.py`, and written straight after it for that reason. Both classes
run per-maze tickers over the same copy-on-write cache entry, both bound concurrency, both
self-terminate, and both make most of their promises about things that must *not* happen. When
mutation found four unpinned scheduling guarantees in one of them, the honest next question was
whether the other has the same holes — not whether its tests read well.

They do not read badly. `LivingMazeServiceTest` is the stronger of the two suites: it pins the
copy-on-write swap by identity, checks the pre-tick snapshot is still intact afterwards, proves
determinism by eroding two identical mazes with one seed, and — unlike the traffic suite — makes
a *meaningful* idempotence assertion, restarting a live maze with a different tick count and
checking the run kept its original one. That is the test asking the right question.

So the mutations below aim where even a good suite tends not to look:

  * the **one-wall-per-tick floor** (`max(erosionFactor, 1.0 / deadEnds)`), whose comment says it
    exists so small mazes "don't stall at round(factor * few) == 0 forever". A stalled run is not
    a failure — it is a run that ticks to its cap opening nothing, which reads as a maze that
    settled slowly, and no assertion about connectivity or determinism can tell the difference;
  * the **hotspot floor in `drift`**, which skips uniform cells so "erosion never mints new
    hotspots". Remove it and every cell in a weighted maze breathes: the response's hotspot list
    goes from a handful to rows·cols, every tick, and everything downstream still type-checks;
  * the **`replace` false path**, the documented stop signal that must never resurrect an evicted
    maze — the one place this class could put an entry back into a cache that just dropped it;
  * the **scheduling pair** that `trafficteeth.py` found unpinned next door: `future == null`
    guarding the schedule, and `stop` in the tick's catch;
  * the **per-run tick clamp** and the **last-tick comparison**, the two arithmetic bounds a run
    is trusted to enforce on itself.

One mutation was written, run, and retired rather than left standing, and the reasoning is worth
more than the mutation. Collapsing the per-tick seed (`run.seed + done + 1` down to a constant
`run.seed + 1`) survives, and unlike the inert cases elsewhere in this folder it genuinely does
change behaviour — it just breaks no promise the class makes. Determinism survives it: "same maze
+ same seed erodes identically" holds for a fixed seed as much as a walking one, which is why
`erosionIsDeterministic_sameSeedSameMazeSameResult` is quiet. Erosion survives it too, because
braid draws from a dead-end list that shrinks every tick, so a repeated seed still opens new
walls.

What it would degrade is `drift`. Its RNG is seeded from the tick seed, so a frozen seed hands
every hotspot the *same* multiplier on every tick, and "breathing" becomes a ratchet: a cell that
drew 1.2 climbs 1.2^n until it pins at the 1000 ceiling, one that drew 0.8 decays to 1.0 and
leaves the hotspot list for good. That is a real difference — and pinning it means asserting a
random walk did not saturate, which is a statistical claim dressed as a test and would hold or
fail on the choice of seed. The absorbing state at 1.0 is not the mutation's fault either: the
real code can flatten a hotspot too, just not systematically. So it is recorded here instead: the
per-tick seed is load-bearing for cost *drift*, not for erosion, and its guarantee is
unpinned — deliberately, not by oversight.

Usage:  python3 mutants/livingteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
LM = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/LivingMazeService.java"

MUT = [
    (LM, "the concurrent-run cap is removed",
     "            if (runs.size() >= maxConcurrent) {\n"
     "                throw new CapacityExceededException(maxConcurrent);\n"
     "            }",
     "            if (false) {\n"
     "                throw new CapacityExceededException(maxConcurrent);\n"
     "            }"),
    (LM, "start is no longer idempotent (a second run per maze)",
     "            if (existing != null) {\n"
     "                run = existing;\n"
     "            }",
     "            if (false) {\n"
     "                run = existing;\n"
     "            }"),
    (LM, "a second ticker is scheduled on restart",
     "            if (run.future == null) {",
     "            if (true) {"),
    (LM, "the per-run tick cap is ignored",
     "        int bounded = Math.min(Math.max(1, ticks), maxTicks);",
     "        int bounded = Math.max(1, ticks);"),
    (LM, "erosion loses its one-wall-per-tick floor (small mazes stall)",
     "            double factor = deadEnds == 0 ? 0.0 : Math.max(erosionFactor, 1.0 / deadEnds);",
     "            double factor = deadEnds == 0 ? 0.0 : erosionFactor;"),
    (LM, "the last tick is off by one (a run overshoots its request)",
     "            boolean lastTick = run.done.get() + 1 >= run.ticks;",
     "            boolean lastTick = run.done.get() >= run.ticks;"),
    (LM, "a settled maze keeps ticking instead of ending early",
     "            if (!changed) {",
     "            if (false) {"),
    (LM, "drift mints new hotspots on every uniform cell",
     "                if (Math.abs(w - 1.0) <= WEIGHT_EPSILON) {\n"
     "                    continue; // only existing hotspots breathe; erosion never mints new ones\n"
     "                }",
     "                if (false) {\n"
     "                    continue; // only existing hotspots breathe; erosion never mints new ones\n"
     "                }"),
    (LM, "drifted costs escape the weighted API's domain",
     "                double drifted = Math.min(COST_MAX,\n"
     "                        Math.max(COST_MIN, w * (DRIFT_MIN + DRIFT_SPAN * rng.nextDouble())));",
     "                double drifted = w * (DRIFT_MIN + DRIFT_SPAN * rng.nextDouble());"),
    (LM, "a lost race with eviction resurrects the maze",
     "            if (!gen.replace(run.mazeId, updated)) {\n"
     "                stop(run, false); // lost the race with eviction — never resurrect\n"
     "                return;\n"
     "            }",
     "            gen.replace(run.mazeId, updated);"),
    (LM, "a failing tick leaves its run scheduled",
     "            log.warn(\"living maze {} tick failed — ending its run\", run.mazeId, e);\n"
     "            stop(run, false);",
     "            log.warn(\"living maze {} tick failed — ending its run\", run.mazeId, e);"),
]

CLASSES = ("LivingMazeServiceTest", "LivingMazeTickContractTest", "LivingMazeEndpointTest",
           "MazeWebSocketMutationBridgeTest", "BoundedStoresTest")
TESTS = ",".join(CLASSES)


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "test",
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
            print(f"{name:58s} -> SKIP (anchor x{orig.count(old)})", flush=True)
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
        print(f"{name:58s} -> {v}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    V.release()
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
