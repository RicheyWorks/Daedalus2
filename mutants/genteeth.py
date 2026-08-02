#!/usr/bin/env python3
"""Teeth for MazeGenerationService — the substrate every other service commits through.

The same shape of blind spot `gridteeth.py` found one layer down: heavily *used* is not the same
as *attacked*. Every feature in the server ends up here — generation, the cache, the swap point
for both tickers, the adoption path for crossbred mazes, the circuit-breaker fallback — and no
mutation had ever been aimed at it. Classes like this are exercised constantly and asserted about
rarely, because each caller tests its own concern and takes the foundation for granted.

Three of its promises are made in prose and load-bearing elsewhere:

  * **`replace` is present-only.** Its javadoc says `computeIfPresent` "never resurrects a maze the
    cache already evicted, so a living run whose maze ages out stops on its next tick instead of
    pinning the entry forever". Two services depend on that answer being false-and-inert rather
    than false-and-inserting, and `put` returns null for an absent key — so the naive form passes
    a `isFalse()` assertion while quietly putting the entry back.
  * **Start and goal are placed at the extremes, never at corners.** The comment records why: for
    sparse generators a corner is solid rock, so the served maze was unsolvable and a session
    opened inside a wall. `adopt` runs the same finishing steps for the same reason.
  * **A caller error is not a generator failure.** The fallback rethrows `IllegalArgumentException`
    so a bad hotspot answers 400 rather than silently returning a different maze.

And two bounds: the maze cache's size and idle TTL. The idle half is exactly what survived on
`GameSessionService` — `BoundedStoresTest` pins that every Caffeine cache declares a
`maximumSize`, and pinning the declaration is not pinning the expiry.

**First run: 5 of 13 caught.** The one worth the whole harness is the start/goal placement.
`MazeGenerationStartGoalTest` exists *because* of a real bug — fixed corners meant "a dungeon's
corners are solid rock, so the served maze was unsolvable and a play session opened inside a
wall" — and deleting `placeStartAndGoalAtExtremes` from `generate` leaves all three of its tests
green. Verified directly, not inferred: mutate, run that class alone, 3/3 pass. Its dungeon case
tests one (generator, size, seed) triple and at 15x21 seed 7 the corners happen to be carved and
connected; its perfect-maze case asserts the route is at least as long as the grid's longer
dimension, which corner-to-corner clears by itself. A regression test that cannot detect its own
regression is the most expensive kind of green.

`MazeGenerationContractTest` replaces both with assertions that can tell the difference: a sweep
of twelve dungeon seeds, and — on a perfect maze, where the graph is a tree and double-BFS
placement is exact — start-to-goal *equals* the diameter. The other seven survivors are pinned
there too: the cache's idle expiry (via the same Ticker seam `GameSessionService` carries),
`replace` not re-inserting an evicted maze (`put` also answers null for an absent key, so the
naive form passes an `isFalse()` assertion while resurrecting the entry), `adopt`'s placement and
its event, the hotspot bounds check at exactly `row == rows`, the fallback's rethrow of a caller
error, and the null-grid guard — which is not a formality, because generators are a plugin
extension point and "returns null" is third-party behaviour this service has to survive.

Usage:  python3 mutants/genteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
GS = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/MazeGenerationService.java"

MUT = [
    (GS, "the maze cache loses its size bound",
     "                .maximumSize(cacheMaxSize)\n", ""),
    (GS, "the maze cache loses its idle expiry",
     "                .expireAfterAccess(cacheTtl)\n", ""),
    (GS, "replace resurrects an evicted maze (put, not computeIfPresent)",
     "        return cache.asMap().computeIfPresent(id, (k, old) -> updated) != null;",
     "        return cache.asMap().put(id, updated) != null;"),
    (GS, "a generator returning null is served instead of failing loudly",
     "        if (grid == null) {\n"
     "            // Timer.record(Supplier) is @Nullable; a generator returning null\n"
     "            // is a contract violation worth failing loudly on.\n"
     "            throw new IllegalStateException(\"generator returned null grid: \" + generatorId);\n"
     "        }",
     "        if (grid == null) {\n"
     "            return null;\n"
     "        }"),
    (GS, "out-of-range hotspots are accepted",
     "                if (h.row() >= rows || h.col() >= cols) {",
     "                if (false) {"),
    (GS, "the hotspot bounds check is off by one",
     "                if (h.row() >= rows || h.col() >= cols) {",
     "                if (h.row() > rows || h.col() > cols) {"),
    (GS, "generated mazes keep their default start and goal",
     "        MazeMetrics.placeStartAndGoalAtExtremes(grid);\n"
     "        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,",
     "        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,"),
    (GS, "adopted mazes keep their default start and goal",
     "        MazeMetrics.placeStartAndGoalAtExtremes(grid);\n"
     "        MazeMetadata meta = MazeMetadata.of(grid.rows(), grid.cols(), seed, generatorId,",
     "        MazeMetadata meta = MazeMetadata.of(grid.rows(), grid.cols(), seed, generatorId,"),
    (GS, "an adopted maze is never cached",
     "        Cached cached = new Cached(meta, grid, new MazeStats(), null);\n"
     "        cache.put(meta.id(), cached);",
     "        Cached cached = new Cached(meta, grid, new MazeStats(), null);"),
    (GS, "an adopted maze is never announced",
     "        events.publishEvent(new MazeGeneratedEvent(this, meta, grid, cached.stats()));\n"
     "        return cached;",
     "        return cached;"),
    (GS, "the applied-hotspot list is dropped from the cache entry",
     "            applied = java.util.List.copyOf(hotspots);",
     "            applied = null;"),
    (GS, "a caller error falls back to a silently different maze",
     "        if (t instanceof IllegalArgumentException iae) {\n"
     "            throw iae;\n"
     "        }",
     "        if (false) {\n"
     "            throw (IllegalArgumentException) t;\n"
     "        }"),
    (GS, "the fallback reports the requested algorithm, not the one that ran",
     "        return generate(\"binary-tree\", rows, cols, seed, hotspots);",
     "        return generate(generatorId, rows, cols, seed, hotspots);"),
]

# Deliberately wide. This class is the substrate: a narrow list would report false survivors for
# guarantees that other features pin from their own tests (mutants/README.md warns about exactly
# this), and a substrate harness that cries survivor is worse than no harness.
CLASSES = ("MazeGenerationContractTest",
           "MazeGenerationStartGoalTest", "MazeGenerationServiceFallbackTest", "BoundedStoresTest",
           "CampaignServiceTest", "LivingMazeServiceTest", "LivingMazeTickContractTest",
           "TrafficServiceTest", "TrafficTickContractTest", "WeightedMazeApiTest",
           "MazeControllerValidationTest", "BreedAndSpectateEndpointTest", "DailyMazeServiceTest",
           "SolveReplayTest", "MazeControllerGeneratorIdTest", "GeneratorInvariantFuzzTest")
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
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
