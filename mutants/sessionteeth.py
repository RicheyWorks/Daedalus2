#!/usr/bin/env python3
"""Teeth for GameSessionService — the lock, the flag gate, and the two cache bounds.

Why this file exists: `GameSession`'s fields were made safe for unlocked readers on 2026-08-01
(volatile score/completed, AtomicLong moveCount), and that fix is only half a design. The other
half is the per-session lock in `tryMove` that serialises the writers, and no mutation had ever
been pointed at this class. A fix whose premise is unverified is a guess with a test attached.

Two mutations are aimed at guarantees the class documents in prose:

  * "The lock is per session, so distinct sessions never contend" — widening it to a shared
    monitor keeps every single-threaded test green while making one blocked listener able to
    stall the whole server, which is the exact failure the comment says the design prevents.
  * "expireAfterAccess ... sessions previously lived in an unbounded map" — `BoundedStoresTest`
    pins `maximumSize`, and pins that every Caffeine cache in the server declares one, but it
    passes a one-hour TTL and never advances a clock. The size bound and the idle bound are
    separate promises; only one of them is checked.

Usage:  python3 mutants/sessionteeth.py
"""
import pathlib, subprocess

import verdict as V

REPO = pathlib.Path(__file__).resolve().parent.parent
SVC = REPO / "daedalus-server/src/main/java/com/daedalus/server/service/GameSessionService.java"

TRYMOVE_LOCK = "        synchronized (s) {\n            if (s.completed()) return false;"

MUT = [
    # `if (true) {` does not compile here -- javac cannot see that the block always returns,
    # so the method loses its return statement and the harness reports a broken build rather
    # than a result. Locking a fresh object per call removes mutual exclusion while leaving
    # the control flow, and the structure, exactly as they were.
    (SVC, "the per-session lock guards nothing (fresh monitor per call)",
     TRYMOVE_LOCK,
     "        synchronized (new Object()) {\n            if (s.completed()) return false;"),
    (SVC, "the lock is widened to one shared monitor",
     TRYMOVE_LOCK,
     "        synchronized (sessions) {\n            if (s.completed()) return false;"),
    (SVC, "a completed session accepts more moves",
     "            if (s.completed()) return false;\n            String actor",
     "            String actor"),
    (SVC, "a player who never joined can be moved into existence",
     "            if (from == null) return false;",
     "            if (false) return false;"),
    (SVC, "illegal steps are accepted (walls ignored)",
     "            if (!live.openNeighbors(from).contains(to)) return false;",
     "            if (false) return false;"),
    (SVC, "a living replace is ignored (stale snapshot used)",
     "            MazeGrid live = grid;\n"
     "            if (mazes != null) {\n"
     "                MazeGenerationService.Cached cached = mazes.find(s.mazeId());\n"
     "                if (cached == null) {\n"
     "                    return false;\n"
     "                }\n"
     "                live = cached.grid();\n"
     "            }",
     "            MazeGrid live = grid;"),
    (SVC, "join ignores the multiplayer flag",
     "        if (!multiplayer) return null;",
     "        if (false) return null;"),
    (SVC, "join admits players into a finished session",
     "            if (s.completed()) return null;",
     "            if (false) return null;"),
    (SVC, "the session store loses its size bound",
     "                .maximumSize(maxSessions)\n",
     ""),
    (SVC, "the session store loses its idle expiry",
     "                .expireAfterAccess(idleTtl)\n",
     ""),
    (SVC, "the score floor is removed (negative scores)",
     "        long score = Math.max(0, 100_000 - hops * 10 - elapsed / 100);",
     "        long score = 100_000 - hops * 10 - elapsed / 100;"),
    (SVC, "a joiner finish is credited to the opener",
     "                s.id(), s.mazeId(), winner, score, hops, elapsed,",
     "                s.id(), s.mazeId(), s.playerName(), score, hops, elapsed,"),
]

CLASSES = ("GameSessionServiceConcurrencyTest", "SessionLockIsolationTest",
           "GameSessionMultiplayerTest", "BoundedStoresTest", "MazeControllerJoinTest",
           "GhostServiceTest", "GameSessionLiveGridTest")
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
            print(f"{name:52s} -> SKIP (anchor x{orig.count(old)})", flush=True)
            survivors.append(name + " [anchor lost]")
            continue
        path.write_text(orig.replace(old, new))
        try:
            v = run_once()
        except subprocess.TimeoutExpired:
            v = "caught: timed out (a lock this wide serialises everything)"
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
