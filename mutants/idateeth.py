#!/usr/bin/env python3
"""Teeth for IDAStarBudgetTest — the node budget that stopped IDA* running for minutes.

Four mutations, one per way the guard could be broken. Two of them reproduce the original
defect, and that is the wrinkle this harness exists to handle: **a timeout is a catch, not an
error.** The first version used a 1200-second subprocess cap and treated the resulting
TimeoutExpired as a crash — it aborted mid-run and lost the mutations after it, having spent
twenty minutes proving something a four-minute cap proves just as well. If removing the budget
makes the suite hang, the suite has teeth; that is the whole point.

One mutation SURVIVES by design and is recorded rather than papered over: an early
`if (remaining[0] <= 0) return INF;` inside the neighbour loop turned out to be inert, because
every sibling call lands on the identical check at the top of `search` and returns immediately.
The line was deleted from the solver. The mutation that proved it inert is recorded here
rather than in the list below: kept as a permanent SKIP it counted as an unresolved result on
every run, and a harness whose survivor list always has one entry in it teaches you to stop
reading the survivor list.

Usage:  python3 mutants/idateeth.py
"""

import pathlib
import verdict as V
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TARGET = REPO / "daedalus-core/src/main/java/com/daedalus/solver/solvers/IDAStarSolver.java"
PRISTINE = pathlib.Path("/tmp/idateeth-pristine.java")
CAP_SECONDS = 240

MUTATIONS = [
    ("budget never decremented",
     "        remaining[0]--;\n        stats.incExplored();",
     "        stats.incExplored();"),
    ("budget treated as unlimited",
     "long[] remaining = { nodeBudget <= 0 ? Long.MAX_VALUE : nodeBudget };",
     "long[] remaining = { Long.MAX_VALUE };"),
    ("throw replaced by empty path",
     "                throw new SolverBudgetExceededException(id(), nodeBudget);",
     "                return java.util.Collections.emptyList();"),
]


def restore():
    if PRISTINE.exists():
        TARGET.write_text(PRISTINE.read_text())


def main():
    if PRISTINE.exists():
        print("a previous run left a sidecar; restoring before starting")
        restore()
    PRISTINE.write_text(TARGET.read_text())
    original = PRISTINE.read_text()
    results = []

    try:
        for name, old, new in MUTATIONS:
            if original.count(old) != 1:
                results.append((name, f"SKIP (anchor matched {original.count(old)}x)"))
                print(f"{name:36s} -> SKIP, anchor matched {original.count(old)}x", flush=True)
                continue
            TARGET.write_text(original.replace(old, new))
            try:
                proc = subprocess.run(
                    ["mvn", "-B", "-ntp", "-pl", "daedalus-core", "test",
                     "-Dtest=IDAStarBudgetTest", "-Dsurefire.failIfNoSpecifiedTests=false",
                     "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Djacoco.skip"],
                    cwd=REPO, capture_output=True, text=True, timeout=CAP_SECONDS)
                failed = sorted({m for m in
                                 re.findall(r"IDAStarBudgetTest\.(\w+)", proc.stdout)})
                verdict = ("SURVIVED  <-- no test can see this change"
                           if proc.returncode == 0
                           else V.classify(proc.returncode, proc.stdout, failed))
            except subprocess.TimeoutExpired:
                verdict = (f"caught: still running after {CAP_SECONDS}s "
                           "— the unbounded behaviour this budget exists to stop")
            finally:
                restore()
                subprocess.run(["pkill", "-f", "[s]urefire"], capture_output=True)
            results.append((name, verdict))
            print(f"{name:36s} -> {verdict}", flush=True)
    finally:
        restore()
        PRISTINE.unlink(missing_ok=True)
        print("\nrestored", TARGET.name)

    survivors = [n for n, v in results if not V.is_catch(v)]
    print(f"\n{len(results) - len(survivors)}/{len(results)} accounted for; "
          f"survivors: {survivors or 'none'}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
