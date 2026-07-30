# Mutation harness

Injects one semantic break at a time into the codebase, runs the tests, and restores the
file byte-for-byte. A mutation that *survives* means the guarantee it breaks is not pinned
by any test.

    python3 mutants/run.py        # per-module runs (fast, but see below)
    python3 mutants/wide.py       # re-check survivors against the whole reactor
    python3 mutants/coreteeth.py  # core-only checks for guarantees that live in core
    python3 mutants/fuzzteeth.py  # six breaks aimed at GeneratorInvariantFuzzTest

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
