# Mutation harness

Injects one semantic break at a time into the codebase, runs the tests, and restores the
file byte-for-byte. A mutation that *survives* means the guarantee it breaks is not pinned
by any test.

    python3 mutants/run.py        # per-module runs (fast, but see below)
    python3 mutants/wide.py       # re-check survivors against the whole reactor
    python3 mutants/coreteeth.py  # core-only checks for guarantees that live in core
    python3 mutants/fuzzteeth.py  # six breaks aimed at GeneratorInvariantFuzzTest
    python3 mutants/idateeth.py   # four breaks aimed at IDA*'s node budget
    python3 mutants/tourteeth.py  # eight breaks aimed at the tournament + its statistics
    python3 mutants/lensteeth.py  # seven breaks aimed at the heuristic lens

**Scope matters.** `run.py` runs only the Maven module owning the mutated file, which is
fast and can report false survivors: a guarantee may be pinned from a *different* module
than the code implementing it. Always confirm a survivor with `wide.py` before believing
it. Conversely, a mutation caught only by `wide.py` and not by the owning module's own
tests is a real (if narrower) gap — that is exactly how
`LeaderboardEntryOrderingTest` and `SearchRecorderFidelityTest` came to exist.

**`fuzzteeth.py` is aimed at one test.** `GeneratorInvariantFuzzTest` found zero violations
across every registered generator, which is indistinguishable from a test that cannot fail —
so this harness breaks Binary Tree six ways, once per property (asymmetric wall, off-grid
opening, non-determinism, seed ignored, cycles, stranded cells) and asserts the fuzz reports
the *specific* property each break violates, not merely that something went red. All six are
caught.

**Never leave a mutation harness unsupervised without a lock.** The first `fuzzteeth.py` run
was launched under a wrapper that was killed at a timeout; the Python process was orphaned and
kept mutating, and a second copy started against the same file. The "6/6 caught" the two
interleaved runs printed was worthless, and the tree was left holding a sabotaged generator.
`fuzzteeth.py` now writes a pristine sidecar before its first mutation (restored on startup, so
the *next* run repairs what a killed run left behind), restores after each mutation rather than
once at the end, restores on SIGTERM/SIGINT, and refuses to start while another run holds the
lock. `run.py`, `wide.py` and `coreteeth.py` already restore per mutation in a `finally`, which
covers an ordinary crash but not a SIGKILL — they have no lock or sidecar yet. Until they do:
run one harness at a time, and check `git diff` on the mutated file after any interrupted run
before trusting a result.

**A timeout can be a catch.** `idateeth.py` mutates a guard whose absence makes the suite run for
minutes — that is what the guard is for. Its first version used a 20-minute subprocess cap and
treated the resulting `TimeoutExpired` as a crash, so it aborted mid-run and lost the mutations
after it, having spent twenty minutes to learn what four proves. When the defect under test *is*
"this never finishes", cap the run short and count the timeout as evidence.

**Record survivors instead of quietly deleting them.** One `idateeth.py` mutation survived: an
early return inside IDA*'s neighbour loop that no test could distinguish, because every sibling
call hit the identical check one frame up. The right response was to delete the line from the
solver — it cost a comparison per neighbour and bought nothing — and leave the mutation in the
list as the evidence for why the code is not there.

**A survivor is usually a message about the test, not the code.** `tourteeth.py` produced two,
and neither meant the implementation was wrong. One test ran 21×21 dungeons, where IDA* refuses
from the first maze, so "excluded" and "collected no data" were the same state and a mutation
distinguishing them was invisible; moving to 19×19, where it finishes five mazes first, made the
case real. The other asserted `worstGap >= bestGap`, which a mutation satisfied by collapsing
both extremes onto one maze — `min >= min` is true. Both tests were strengthened rather than the
mutations dropped.

**An assertion that can only confirm one value cannot detect a dead counter.** `lensteeth.py`
found this: the heuristic lens reports how many cells A* expanded above the optimal cost, which
is zero for any admissible heuristic, and the test asserted zero. A mutation that never
incremented the counter survived, because zero was the only answer the test could ever see. The
fix was to add a deliberately inadmissible heuristic so the counter has a case that must fire —
the test gained teeth and the product gained a demonstration of why admissibility matters.
