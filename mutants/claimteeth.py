#!/usr/bin/env python3
"""Does the test named after the bug actually catch the bug?

Every other harness in this folder asks "does the *suite* notice?" and runs a mutation against a
wide class list, because a false survivor is the expensive mistake there. This one asks a
narrower and more uncomfortable question: **does the specific test that claims to hold a specific
fix fail when that fix is removed?** So each mutation runs against exactly one test class — its
claimed guardian — and a catch by anything else is beside the point and deliberately invisible.

The question is not academic. `genteeth.py` found that `MazeGenerationStartGoalTest`, written to
hold the fix for start and goal landing on solid rock, passes with that fix deleted. Its
perfect-maze case asserts a route length a corner-to-corner walk already clears, and its dungeon
case cannot fail at all: `DungeonGenerator` places its own start and goal inside carved rooms, so
the service-level fix the test is named for is redundant on exactly the maze it tests. Both
assertions are true of the broken code. That is the most expensive kind of green — a test whose
name and javadoc tell every future reader the ground is covered, so nobody looks again.

Once is an accident. This harness is the check for a pattern, and it is cheap: one class per run,
mostly unit tests. The pairs below are the repo's explicit claims — a fix, and the test its
javadoc or commit message says holds it.

Reading the results: `SURVIVED` here does **not** mean the codebase is unprotected. It means the
named guardian is not the thing protecting it, which is worth knowing either way — a fix whose
only real coverage is three modules away is one refactor from unguarded, and the comment pointing
at the wrong test is what will make that invisible.

Runs are capped at four minutes rather than the usual thirty. A single test class that has not
finished by then is not thinking — it is blocked, which is itself a result worth recording.

Usage:  python3 mutants/claimteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "daedalus-server/src/main/java/com/daedalus/server"
CORE = REPO / "daedalus-core/src/main/java/com/daedalus"

TREMAUX = CORE / "solver/solvers/TremauxSolver.java"
WEIGHTED = CORE / "engine/WeightedMazeGrid.java"
GRID = CORE / "engine/MazeGrid.java"
LANDMARK = CORE / "solver/LandmarkHeuristic.java"
RATELIMIT = SRC / "ratelimit/PerKeyRateLimitInterceptor.java"
GEN = SRC / "service/MazeGenerationService.java"
SESSION = SRC / "service/GameSessionService.java"
LEADER = SRC / "service/LeaderboardService.java"
SENDREJECT = SRC / "security/StompSendRejectionInterceptor.java"
REQUEST = REPO / "daedalus-server/src/main/java/com/daedalus/api/dto/GenerateRequest.java"

# (module, claiming test class, fix description, file, old, new)
CLAIMS = [
    ("daedalus-core", "TremauxSolverTest",
     "Trémaux's third rule (turn back on a revisited junction)",
     TREMAUX,
     "            if (revisited && entryDir >= 0 && marks[pos * 4 + entryDir] == 1) {",
     "            if (false) {"),
    ("daedalus-core", "MazeGridCopyTest",
     "WeightedMazeGrid.copy keeps the weights",
     WEIGHTED,
     "        for (int r = 0; r < rows(); r++) {\n"
     "            System.arraycopy(weights[r], 0, out.weights[r], 0, cols());\n"
     "        }\n",
     ""),
    ("daedalus-core", "GeneratorConnectivityTest",
     "carve opens both sides of a wall",
     GRID,
     "        from.open(d);\n        to.open(d.opposite());",
     "        from.open(d);"),
    ("daedalus-core", "LandmarkHeuristicWeightedTest",
     "the directed bound in weighted mode",
     LANDMARK,
     "                best = Math.max(best, dLt - dLs);",
     "                best = Math.max(best, Math.abs(dLt - dLs));"),
    ("daedalus-server", "PerKeyRateLimitEvictionTest",
     "a bucket never expires before its own refill period",
     RATELIMIT,
     "            return (refill.compareTo(idleTtl) > 0 ? refill : idleTtl).toNanos();",
     "            return idleTtl.toNanos();"),
    ("daedalus-server", "MazeGenerationStartGoalTest",
     "start and goal at the extremes, never at corners",
     GEN,
     "        MazeMetrics.placeStartAndGoalAtExtremes(grid);\n"
     "        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,",
     "        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,"),
    ("daedalus-server", "MazeGenerationContractTest",
     "start and goal at the extremes — same fix, the new claimant",
     GEN,
     "        MazeMetrics.placeStartAndGoalAtExtremes(grid);\n"
     "        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,",
     "        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,"),
    ("daedalus-server", "SessionLockIsolationTest",
     "the per-session lock is per session",
     SESSION,
     "        synchronized (s) {\n            if (s.completed()) return false;",
     "        synchronized (sessions) {\n            if (s.completed()) return false;"),
    ("daedalus-server", "LeaderboardRedisRetentionTest",
     "the Redis sorted sets are trimmed from the worst end",
     LEADER,
     "        zset.removeRange(key, 0, -(maxEntries + 1L));",
     "        zset.removeRange(key, 1L, (long) maxEntries);"),
    ("daedalus-server", "StompSendRejectionTest",
     "every client SEND frame is refused",
     SENDREJECT,
     "        if (accessor == null || !StompCommand.SEND.equals(accessor.getCommand())) {",
     "        if (true) {"),
    ("daedalus-server", "MazeControllerValidationTest",
     "hotspot validation cascades into the list",
     REQUEST,
     "        List<@Valid Hotspot> hotspots",
     "        List<Hotspot> hotspots"),
]


def run_once(module, test_class):
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", module, "test",
                        "-Dtest=" + test_class,
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=240)
    return V.classify(p.returncode, p.stdout, V.failing_tests(p.stdout, test_class))


V.restore_on_signal()
originals = {c[3]: c[3].read_text() for c in CLAIMS}
V.snapshot(originals)
broken = []
try:
    for module, test_class, what, path, old, new in CLAIMS:
        orig = originals[path]
        label = f"{test_class} :: {what}"
        if orig.count(old) != 1:
            print(f"{label:78s} -> SKIP (anchor x{orig.count(old)})", flush=True)
            broken.append(label + " [anchor lost]")
            continue
        path.write_text(orig.replace(old, new))
        try:
            v = run_once(module, test_class)
        except subprocess.TimeoutExpired:
            # A hang is evidence, but a poor guardian: see the note on the rate limiter below.
            v = "caught: timed out (the guardian hangs rather than fails)"
        finally:
            path.write_text(orig)
        if not V.is_catch(v):
            broken.append(label)
        print(f"{label:78s} -> {v}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    V.release()
    print("restored")

print(f"\n{len(CLAIMS) - len(broken)}/{len(CLAIMS)} claims hold; "
      f"unheld: {broken or 'none'}")
