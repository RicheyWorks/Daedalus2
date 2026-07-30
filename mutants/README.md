# Mutation harness

Injects one semantic break at a time into the codebase, runs the tests, and restores the
file byte-for-byte. A mutation that *survives* means the guarantee it breaks is not pinned
by any test.

    python3 mutants/run.py        # per-module runs (fast, but see below)
    python3 mutants/wide.py       # re-check survivors against the whole reactor
    python3 mutants/coreteeth.py  # core-only checks for guarantees that live in core

**Scope matters.** `run.py` runs only the Maven module owning the mutated file, which is
fast and can report false survivors: a guarantee may be pinned from a *different* module
than the code implementing it. Always confirm a survivor with `wide.py` before believing
it. Conversely, a mutation caught only by `wide.py` and not by the owning module's own
tests is a real (if narrower) gap — that is exactly how
`LeaderboardEntryOrderingTest` and `SearchRecorderFidelityTest` came to exist.
