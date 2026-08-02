#!/usr/bin/env python3
"""Teeth for the Redis leaderboard retention bound.

The bound has two independent ways to be wrong and only one of them is about size.

Mutations 1 and 2 remove the trim, restoring the unbounded sets: one member per completed run,
evicted never, on keys no `top(n)` could read past rank 100. That is the leak the fix closes.

Mutation 3 is the one worth having a harness for. It trims the *other end* -- keeping the worst
entries and deleting the best -- and leaves the set exactly `maxEntries` large while doing it.
Every size assertion still passes. `removeRange` works on ascending rank while every read in
this class is `reverseRange`, descending, so the correct call reads backwards at a glance and
the wrong one reads right; a test that asserted on call arguments rather than on which entries
survived would wave this straight through.

Mutation 4 is the off-by-one: `-maxEntries` instead of `-(maxEntries + 1)` keeps one fewer than
the cap. Small, permanent, and invisible to any assertion phrased as "the set stopped growing".

REPO resolves from this file, so the harness runs wherever the checkout is.
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
SVC = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/LeaderboardService.java"

TRIM = "        zset.removeRange(key, 0, -(maxEntries + 1L));"

MUT = [
    (SVC, "the trim is dropped (unbounded sets return)",
     TRIM, "        // mutation: no trim"),
    (SVC, "only the global set is trimmed, partitions leak",
     "            addAndTrim(zset, PER_GEN_KEY + entry.mazeGeneratorId(), entry);",
     "            zset.add(PER_GEN_KEY + entry.mazeGeneratorId(), entry, entry.score());"),
    (SVC, "the trim aims at the best end, not the worst",
     TRIM, "        zset.removeRange(key, maxEntries, -1L);"),
    (SVC, "off by one: keeps maxEntries - 1",
     TRIM, "        zset.removeRange(key, 0, -maxEntries);"),
]

TESTS = "LeaderboardRedisRetentionTest,LeaderboardPartitionTest"


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-server", "test",
                        "-Dtest=" + TESTS,
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=1200)
    failed = V.failing_tests(p.stdout, "LeaderboardRedisRetentionTest",
                             "LeaderboardPartitionTest")
    return V.classify(p.returncode, p.stdout, failed)


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
            verdict = run_once()
        except subprocess.TimeoutExpired:
            verdict = "timed out"
        finally:
            path.write_text(orig)
        if not V.is_catch(verdict):
            survivors.append(name)
        print(f"{name:56s} -> {verdict}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
