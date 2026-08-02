#!/usr/bin/env python3
"""Teeth for TrafficService — the bounded pool, the clamp, the decay floor, the quiet stop.

Largest server class no mutation had been aimed at (230 lines). It is also the one with the
most ways to fail quietly, because every guarantee it makes is about something *not* happening:
a tracker not being scheduled twice, a weight not growing past its ceiling, a decay not
converging asymptotically instead of stopping, a tracker not running forever after the players
leave. Nothing throws when any of those lapses; the maze just gets slowly, permanently worse.

Three of these deserve naming.

`maxCost` is the only thing standing between a busy cell and unbounded cost growth: occupancy
raises weight every tick and nothing else caps it. Remove the clamp and a popular corridor
climbs until routing round it costs more than the maze is wide.

`SNAP` is why decay terminates. Geometric decay toward 1.0 never *reaches* 1.0, so without the
snap a maze that emptied hours ago still carries weights of 1.0000001 — permanently "congested"
by any test that asks, and permanently re-serialised every tick.

The `EPSILON` comparison looked like the third. It is a documented fix, with a comment saying
the previous exact `!=` test "happened to work" and was "one decay-factor change away from
spinning on deltas no player could see" — the kind of guard that should have a test. Reverting
it to `decayed != w` survived, and the survivor is false: **the mutation cannot change an
observable**, for the reason the comment itself gives. The two conditions are equivalent under
the SNAP that precedes them. For any non-uniform `w` (so |w - 1| > EPSILON), either

  * `decayed < SNAP`, in which case SNAP has already set `decayed` to exactly 1.0, and
    |decayed - w| = |w - 1| > EPSILON; or
  * `decayed >= SNAP`, which forces w - 1 >= 0.0625, so |decayed - w| = 0.2·(w - 1) >= 0.0125.

Both branches move by more than EPSILON, so `> EPSILON` and `!=` agree on every value the code
can produce, and no test could distinguish them without calling `setWeight` with a weight within
a nanounit of uniform — which nothing does. The guard is worth keeping (it is what makes the
comment's "one decay-factor change away" safe rather than lucky), and the mutation is retired
here rather than left standing, because a permanent survivor reads as an untested guarantee and
this one is not a guarantee at all. The four remaining ex-survivors were the opposite: real, and
now pinned by TrafficTickContractTest.

Usage:  python3 mutants/trafficteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
TS = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/TrafficService.java"

MUT = [
    (TS, "the concurrent-tracker cap is removed",
     "            if (trackers.size() >= maxConcurrent) {\n"
     "                throw new CapacityExceededException(maxConcurrent);\n"
     "            }",
     "            if (false) {\n"
     "                throw new CapacityExceededException(maxConcurrent);\n"
     "            }"),
    (TS, "enable is no longer idempotent (a second tracker per maze)",
     "            if (existing != null) {\n                return existing;\n            }",
     "            if (false) {\n                return existing;\n            }"),
    (TS, "a second ticker is scheduled on re-enable",
     "            if (tracker.future == null) {",
     "            if (true) {"),
    (TS, "the cost ceiling is removed (unbounded weight growth)",
     "                double raised = Math.min(maxCost, next.weightOf(p.row(), p.col())\n"
     "                        + bump * entry.getValue());",
     "                double raised = next.weightOf(p.row(), p.col())\n"
     "                        + bump * entry.getValue();"),
    (TS, "decay never snaps to uniform (asymptotic congestion)",
     "                    if (decayed < SNAP) {\n                        decayed = UNIFORM;\n                    }",
     "                    if (false) {\n                        decayed = UNIFORM;\n                    }"),
    (TS, "quiet tracking never retires (the ticker runs forever)",
     "                if (++tracker.quietTicks >= quietTicksToStop) {",
     "                if (false) {"),
    (TS, "the quiet counter never resets (premature retirement)",
     "            tracker.quietTicks = 0;",
     "            tracker.quietTicks += 0;"),
    (TS, "a failing tick leaves its tracker spinning",
     "            log.warn(\"traffic tick on maze {} failed — retiring its tracker\", tracker.mazeId, e);\n"
     "            stop(tracker, false);",
     "            log.warn(\"traffic tick on maze {} failed — retiring its tracker\", tracker.mazeId, e);"),
    (TS, "occupancy is dropped instead of drained",
     "                Integer v = tracker.pending.remove(p);",
     "                Integer v = tracker.pending.get(p);"),
]

CLASSES = ("TrafficServiceTest", "TrafficTickContractTest", "TrafficEndpointTest")
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
