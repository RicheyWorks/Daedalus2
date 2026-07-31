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
    python3 mutants/auditteeth.py # three breaks aimed at the config + cache audits
    python3 mutants/rlteeth.py    # three breaks aimed at rate-limit coverage
    python3 mutants/deskteeth.py  # four breaks aimed at the desktop's background work
    python3 mutants/ratchetteeth.py # both directions of the JaCoCo coverage ratchet
    python3 mutants/authteeth.py  # nine holes in the prod authentication posture + its docs
    python3 mutants/errteeth.py   # nine holes in the RFC 7807 error contract
    python3 mutants/notfoundteeth.py # seven ways to lose the 404 bodies

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

**Tests that assert an absence need teeth most of all.** `ConfigCoverageTest` claims there are no
undocumented config keys and no dead ones; the cache scan claims there are no unbounded Caffeine
caches. Both pass trivially if the scanner silently finds nothing, so `auditteeth.py` puts the
original defects back — the dead `daedalus.cache.maze-cache-size` block, a mistyped key, an
unbounded cache — and confirms each is caught. Each scanner also asserts a non-zero find count on
its own, so a broken walk fails loudly instead of reporting a clean sweep.

**`contains(...)` is the assertion most likely to be unfalsifiable.** `deskteeth.py` found two
survivors and both were substring checks that could not fail. One asserted a returned Callable
was non-null, which says nothing about whether it had already done the work; the other asserted
an error string contained "ida-star", which is true whether or not the wrapper exception was
unwrapped, because `ExecutionException.getMessage()` is its cause's `toString()`. Both were
rewritten to assert the thing that actually differs — an event count, and string equality.

**A one-sided ratchet is a floor with good branding.** The JaCoCo gate enforced only a minimum,
so it caught regressions and never noticed that the server had drifted to 91% coverage against a
79% floor — twelve points of slack, accumulated by two roadmaps' worth of tests that nobody
paired with a threshold bump. `ratchetteeth.py` proves both halves now bite: set the floor above
actual and the minimum fires; leave the floor twelve points stale and the new maximum fires and
asks for the bump.

**A passing security test under default-deny proves the least.** Prod closes anything not
enumerated, so "every endpoint refuses an unauthenticated caller" is true before the test is
written and stays true if the test is broken. `authteeth.py` opens the holes a real change would
open — widening `/api/v1/maze/*` to `/api/v1/maze/**`, flipping `anyRequest()` to `permitAll`,
and adding an endpoint nobody classified — and confirms each is caught. The first is not
hypothetical: one extra asterisk publishes the entire analytical surface.

**A test written from observed behaviour cannot find a behaviour bug.** The first version of
`ProdAuthPostureTest` had its expectation table filled in from what the running server answered.
Every mutation above was caught, the suite was green, and the test was still wrong: four
endpoints the README documents as public were being refused in prod, so the spectator permalink,
the ghost racer and the agent re-poll did not work there at all. Writing `AUTHENTICATED` next to
them recorded the bug as the specification. Mutations survive a test like that by definition —
they perturb the system, and the test's expectations are a copy of the system. What fixed it was
a *second, independent* source for the same fact: the README's published table, cross-checked
against the enforced posture in both directions. That check found two more defects on its first
run (two live endpoints missing from the table entirely). When writing an assertion, the question
is not "does this pass" but "where did the expected value come from" — if it came from the code
under test, it is not an expectation, it is an echo.

**A crash is not a catch.** One mutation here — a bare `@GetMapping` added to `PluginController`,
which already has one — collided into an ambiguous-mapping error, so Spring refused to start and
the harness printed "caught" with no test name attached. It proved nothing about the assertion it
was aimed at. Moved to a controller where the new mapping is unique, it caught properly. When a
harness reports a catch, check *which* test caught it; a blank there means the build fell over
before any assertion ran.

**Mutate the safety net too, not just the thing it catches.** `errteeth.py` has one mutation that
removes the 405 handler *and* the roster entry in `ErrorContractTest` that names it, leaving only
the source-derived test able to notice. Without that pairing the harness would have proved the
roster works and said nothing about the generated test — which is the part actually claimed to
protect endpoints nobody has thought about yet. When a test file contains both a hand-written list
and a mechanism meant to outgrow it, a mutation that only the mechanism can catch is the only
evidence the mechanism does anything.

**A crash is not a catch, second helping.** The first `errteeth.py` run reported 9/9 with five
blank test names, because those five mutations renamed the handled exception class to something
that does not exist — javac failed, the build went red, and the harness counted red as caught.
This is the same lesson `authteeth.py` learned one batch earlier, relearned immediately in a new
disguise, which is worth recording as its own data point: the rule is not "avoid ambiguous
mappings", it is **a mutation must compile**. Commenting out the `@ExceptionHandler` annotation
does the same damage and builds cleanly, so the red is an assertion. Any harness line with no
test name next to it should be treated as a failed measurement, not a pass.

**Count what you parse.** The same scan-driven test missed two annotation forms — a bare
`@GetMapping` and `@GetMapping(value = ..., produces = ...)` — because its regex demanded a
parenthesised string literal. A scanner that skips a form reports a clean sweep of the subset it
understands, and one real endpoint (`GET /api/v1/plugins`) had no posture recorded anywhere as a
result. The fix generalises past this test: count the *occurrences* of the thing you are looking
for with a maximally permissive pattern, parse them with the precise one, and assert the two
counts agree. Then a form the parser cannot handle is a loud failure instead of a smaller sweep.

**An exemption that costs nothing to leave on will be left on.** `notfoundteeth.py` produced one
survivor and it was the most useful result in the run: flipping `ALLOW_EMPTY_404` back to `true`
changed nothing, because an exemption only ever *permits*, and by then there was nothing left to
permit. The flag was inert — switch it on, the suite stays green, and the next empty 404 walks
straight through a door somebody left open for a reason that expired. The fix generalises to any
temporary allowance: **count how often the exemption fires and fail when it is enabled but
unused**. A known gap can then be carried between batches in a named, greppable constant that
deletes itself the moment it stops being true, rather than accumulating as permanent permission
nobody remembers granting.

**Mutate in the direction of "nicer", not only "broken".** One mutation here replaces the 404 that
`join` returns when multiplayer is off — deliberately indistinguishable from "no such session" —
with a helpful `"Multiplayer is disabled; set daedalus.session.multiplayer=true"`. Every instinct
reads that as an improvement, and it is a disclosure bug: the 404 exists to make the endpoint look
absent rather than switched off, so the friendlier message turns it into a feature-flag oracle. A
harness that only ever degrades things cannot find the defects that arrive disguised as polish.
