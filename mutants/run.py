#!/usr/bin/env python3
"""Mutation-test the project's headline guarantees.

Each mutation is a small SEMANTIC break that a serious test suite must catch. For every
one: patch the source, run the relevant module's tests, record whether anything failed,
then restore the file byte-for-byte. A mutation that survives means the guarantee it
breaks is not actually pinned by any test.
"""
import subprocess, pathlib, sys

REPO = pathlib.Path("/root/daedalus-work/repo")

MUTANTS = [
    # (name, relative path, old, new, maven module, guarantee at stake)
    ("move-legality",
     "daedalus-server/src/main/java/com/daedalus/server/service/GameSessionService.java",
     "if (!grid.openNeighbors(from).contains(to)) return false;",
     "if (false) return false; // MUTANT: players may walk through walls",
     "daedalus-server",
     "a player cannot move through a wall"),

    ("bfs-optimality",
     "daedalus-core/src/main/java/com/daedalus/solver/solvers/BfsSolver.java",
     "int current = queue[head++];",
     "int current = queue[--tail]; // MUTANT: LIFO, so paths are no longer shortest",
     "daedalus-core",
     "BFS returns a shortest path"),

    ("generator-determinism",
     "daedalus-core/src/main/java/com/daedalus/engine/generators/GrowingTreeEngine.java",
     "new Random(seed)",
     "new Random() /* MUTANT: seed ignored */",
     "daedalus-core",
     "same seed reproduces the same maze"),

    ("leaderboard-order",
     "daedalus-core/src/main/java/com/daedalus/model/LeaderboardEntry.java",
     "int byScore = Long.compare(other.score, this.score);",
     "int byScore = Long.compare(this.score, other.score); // MUTANT: worst-first",
     "daedalus-core",
     "the leaderboard ranks best-first"),

    ("rate-limit-off",
     "daedalus-server/src/main/java/com/daedalus/server/ratelimit/PerKeyRateLimitInterceptor.java",
     "RateLimiter.waitForPermission(bucket);",
     "if (false) RateLimiter.waitForPermission(bucket); // MUTANT: never throttles",
     "daedalus-server",
     "per-key rate limits actually reject"),

    ("replay-fidelity",
     "daedalus-core/src/main/java/com/daedalus/solver/SearchRecorder.java",
     "observer.accept(node);",
     "if (node % 2 == 0) observer.accept(node); // MUTANT: drops half the expansions",
     "daedalus-core",
     "recorded expansions are the real search order"),

    # NOTE the anchor. GameSessionService has two `synchronized (s) {` blocks and join()'s
    # comes first, so a naive first-match replace patches join() and leaves tryMove's lock
    # untouched — which reports a false CAUGHT. Anchored on the preceding line instead.
    ("session-lock-scope",
     "daedalus-server/src/main/java/com/daedalus/server/service/GameSessionService.java",
     "        synchronized (s) {\n            if (s.completed()) return false;\n"
     "            String actor",
     "        synchronized (this) { // MUTANT: global lock, not per-session\n"
     "            if (s.completed()) return false;\n            String actor",
     "daedalus-server",
     "one session's slow listener cannot stall another session"),
]


def run(cmd, cwd=REPO, timeout=1800):
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                          text=True, timeout=timeout)


def tests_fail(module):
    """True if the module's test suite reports any failure/error."""
    r = run(f"mvn -B -ntp -pl {module} test -Dspotbugs.skip -Djacoco.skip=true "
            f"-Dcheckstyle.skip=true 2>&1")
    out = r.stdout + r.stderr
    if "BUILD SUCCESS" in out:
        return False, out
    return True, out


def main():
    results = []
    for name, rel, old, new, module, guarantee in MUTANTS:
        if old is None:
            continue  # handled by the special-cases script
        path = REPO / rel
        original = path.read_text()
        if old not in original:
            results.append((name, "SKIPPED (anchor not found)", guarantee))
            print(f"!! {name}: anchor not found", flush=True)
            continue
        path.write_text(original.replace(old, new, 1))
        try:
            caught, out = tests_fail(module)
            first = ""
            for line in out.splitlines():
                if "<<< FAILURE" in line or "<<< ERROR" in line:
                    first = line.strip()[:150]
                    break
            status = "CAUGHT" if caught else "*** SURVIVED ***"
            results.append((name, status, guarantee))
            print(f"{status:18} {name:24} {guarantee}", flush=True)
            if caught and first:
                print(f"{'':18} └─ {first}", flush=True)
        finally:
            path.write_text(original)

    print("\n=== summary ===")
    for name, status, guarantee in results:
        print(f"{status:18} {name:24} {guarantee}")
    survivors = [r for r in results if "SURVIVED" in r[1]]
    print(f"\n{len(results) - len(survivors)}/{len(results)} mutations caught")
    if survivors:
        print("UNPINNED GUARANTEES:")
        for name, _, guarantee in survivors:
            print(f"  - {guarantee}  ({name})")


if __name__ == "__main__":
    main()
