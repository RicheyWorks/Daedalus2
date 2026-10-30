#!/usr/bin/env python3
"""Teeth for leaderboard attribution — the field only the production path fills in.

This harness exists because of a bug found by running the server rather than by reading it.
Play a session to the goal, read the board back, and every entry says
`"mazeGeneratorId": "unknown"` — a literal, hard-coded in `GameSessionService.complete`, on
every run the server has ever recorded.

**Why the suite could not see it.** Six test classes construct a `LeaderboardEntry` and every one
of them passes its own generator id. `LeaderboardPartitionTest` uses "recursive-backtracker" and
"binary-tree"; the Redis tests use their own. Each is a good test of the thing it tests, and
together they mean the value the *service* writes is the one value nothing observes. That is the
shape worth naming: **a field whose only producer is the code under test, asserted everywhere by
fixtures that supply it themselves.** The mutation that proves it is not subtle — the production
line is already the mutation, and it survived from the day it was written.

**Why it was worse than a wrong string.** `LeaderboardService.submit` keys a Redis sorted set on
this value. The per-generator partition was therefore never a set per generator; it was one set,
`daedalus:leaderboard:gen:unknown`, holding every run on every algorithm. And it had no reader at
all — a sorted-set write plus a trim on every completed run, serving no request. The trim's own
javadoc argues against exactly that ("write-only storage ... a slow leak with a scoreboard
attached") three lines below the line doing it.

So the fix has two halves and this harness attacks both: the id is carried from session open
(recorded, not resolved later — a session is allowed to outlive its maze's cache entry, so a
completion-time lookup would put a placeholder on the longest games), and `topByGenerator` is the
reader that makes the partition mean something.

**First run: 5 of 7, and both survivors were holes in the tests written *for this fix*.** One was
the original bug moved one level up — reverting the controller to the four-argument `open()` left
every attribution test green, because all of them called the service directly with the id in hand.
That is the same mistake the bug came from, committed again in the fix's own test: exercise the
production path or you are testing your fixture. Closed with an endpoint test that generates a
maze and opens a session over HTTP and then asks the stored session what it thinks it is playing.
The other: `topByGenerator(n, null)` forwarding to the global board is load-bearing, because the
controller routes every *unpartitioned* request through it — and the routing test cannot see that,
because it mocks the service. **Now 7 of 7.**

Usage:  python3 mutants/boardteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
SRV = REPO / "daedalus-server/src/main/java/com/daedalus/server"
GS = SRV / "service/GameSessionService.java"
LB = SRV / "service/LeaderboardService.java"
MC = SRV / "controller/MazeController.java"
SESSION = REPO / "daedalus-core/src/main/java/com/daedalus/model/GameSession.java"

MUT = [
    # The original defect, put back exactly as it shipped.
    (GS, "the recorded run forgets which algorithm built its maze",
     "                s.generatorId(), Instant.now()));",
     "                \"unknown\", Instant.now()));"),
    # The wiring, one level up: the controller knows the id and declines to pass it.
    (MC, "the controller drops the generator id on the way into the session",
     "        var s = sessions.open(id, c.metadata().generatorId(), player, c.grid().start(),\n"
     "                ownerOf(authentication));",
     "        var s = sessions.open(id, player, c.grid().start(), ownerOf(authentication));"),
    # The model: every session claims ignorance regardless of what it was told.
    (SESSION, "the session ignores the id it was handed",
     "        this.generatorId = generatorId == null ? UNKNOWN_GENERATOR : generatorId;",
     "        this.generatorId = UNKNOWN_GENERATOR;"),
    # A null must land on the constant, not become the string "null" and key ':gen:null'.
    (SESSION, "a null id becomes the literal null rather than the constant",
     "        this.generatorId = generatorId == null ? UNKNOWN_GENERATOR : generatorId;",
     "        this.generatorId = String.valueOf(generatorId);"),
    # The reader, in-memory: no filter means every generator's board is the global board.
    (LB, "the per-generator board stops filtering",
     "            if (generatorId.equals(e.mazeGeneratorId())) out.add(e);",
     "            out.add(e);"),
    # The reader's empty-argument case: absent generator means "no partition", not "no rows".
    (LB, "an absent generator returns nothing instead of the global board",
     "        if (generatorId == null || generatorId.isBlank()) {\n"
     "            return top(n);\n"
     "        }",
     "        if (generatorId == null || generatorId.isBlank()) {\n"
     "            return List.of();\n"
     "        }"),
    # Precedence: maze is the more specific partition and must win when both are given.
    (MC, "generator shadows maze when both partitions are requested",
     "        if (maze != null) {\n"
     "            return leaderboard.top(n, maze);\n"
     "        }\n"
     "        return leaderboard.topByGenerator(n, generator);",
     "        return leaderboard.topByGenerator(n, generator);"),
]

CLASSES = ("LeaderboardGeneratorAttributionTest", "LeaderboardPartitionTest",
           "LeaderboardRedisRetentionTest", "LeaderboardPartitionRoutingTest", "BoundedStoresTest",
           "GameSessionMultiplayerTest", "RedisSerializationRoundTripTest")
TESTS = ",".join(CLASSES)


def run_once():
    p = subprocess.run(["mvn", "-B", "-ntp", "-pl", "daedalus-core,daedalus-server", "-am",
                        "test", "-Dtest=" + TESTS,
                        "-Dsurefire.failIfNoSpecifiedTests=false",
                        "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                       cwd=REPO, capture_output=True, text=True, timeout=2400)
    return V.classify(p.returncode, p.stdout, V.failing_tests(p.stdout, *CLASSES))


V.restore_on_signal()
originals = {p: p.read_text() for p in {m[0] for m in MUT}}
V.snapshot(originals)
survivors = []
try:
    for path, name, old, new in MUT:
        orig = originals[path]
        if orig.count(old) != 1:
            print(f"{name:62s} -> SKIP (anchor x{orig.count(old)})", flush=True)
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
        print(f"{name:62s} -> {v}", flush=True)
finally:
    for path, text in originals.items():
        path.write_text(text)
    V.release()
    print("restored")

print(f"\n{len(MUT) - len(survivors)}/{len(MUT)} caught; survivors: {survivors or 'none'}")
