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
    python3 mutants/stompteeth.py # five ways to reopen the STOMP forgery hole
    python3 mutants/detteeth.py   # five ways to blind the cross-process determinism check
    python3 mutants/registryteeth.py # five ways to let a plugin become a built-in
    python3 mutants/unloadteeth.py # five ways to leak or over-delete on plugin unload
    python3 mutants/retentionteeth.py # four ways to unbound or mis-aim the leaderboard trim
    python3 mutants/sessionteeth.py # ten ways to break the session lock, flag gate or bounds
    python3 mutants/landmarkteeth.py # four ways to make the ALT heuristic inadmissible
    python3 mutants/gridteeth.py     # six ways to corrupt the grid every layer trusts
    python3 mutants/trafficteeth.py  # nine ways to leak a ticker or unbound a cost
    python3 mutants/livingteeth.py   # eleven ways to stall, overrun or leak a living run
    python3 mutants/campaignteeth.py # twelve ways to unrung the campaign ladder
    python3 mutants/genteeth.py      # thirteen ways to break the substrate everything commits through

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

**A red build is not a catch — and until 2026-08-01 every harness here thought it was.** The
verdict logic now lives in one place, `verdict.py`, and enforces one rule: *no named failing
test, no catch*. A build that dies before any test runs — unresolvable parent POM, empty local
repository, a fork killed for memory, a timeout — exits non-zero exactly like a caught mutation
and used to be reported as one. That is not hypothetical: `retentionteeth.py`'s first run printed
a confident **4/4 caught** while all four builds were failing in POM resolution, having executed
no tests at all. The old `if not failed and "COMPILATION ERROR" in stdout` guard (present in five
scripts, absent from the rest) misses every one of those failures, because none of them print
that phrase. The bug had a second storey, too: even after the per-mutation verdicts were fixed,
the summary line still counted anything not spelled `SURVIVED` as a catch and printed
"4/4 caught; survivors: none" under four `NOT A CATCH` verdicts. Both layers now go through
`verdict.is_catch`.

**Only Maven's own `[ERROR]` lines can name a catcher.** The rule above is only as strong as the
list of failing tests it depends on, and that list used to be built by matching `Class.method`
anywhere in stdout. A *passing* test that logs a stack trace names its own method in that trace:
`TrafficTickContractTest` deliberately makes a tick throw, the service logs it as designed, and
the resulting frame credited that test with catching all nine of `trafficteeth.py`'s mutations,
including ones it never runs. The verdicts were right by luck; the attribution was wrong, and a
build dying after the logging but before a real failure would have borrowed the name of a test
that passed — a false catch wearing a real test's name. Forked-JVM output arrives unprefixed and
Surefire's failure lines come through Maven prefixed `[ERROR]`, so `failing_tests` now reads only
prefixed lines. Read the catcher names: an implausible one (a test that cannot reach the mutated
code) means the harness is matching noise, not evidence.

**A test named after a bug is not the same as a test that catches it.** `genteeth.py` found that
`MazeGenerationStartGoalTest` — written to hold the fix for start/goal landing on solid rock —
passes with the fix deleted. Its dungeon case uses one seed where the corners happen to be carved;
its perfect-maze case asserts a length that corner-to-corner already clears. When a mutation at
the exact line a regression test was written for survives, do not assume the harness is wrong:
mutate, run that one class, and read the count. Three of three green is the answer, and it is
worth more than any number of new mutations elsewhere.

**Value-based mutations drift like anchors do.** `ratchetteeth.py` simulates a coverage regression
by setting the floor above actual coverage — 0.95, chosen when coverage was 94.63%. At 95.10% that
floor passes and the case silently tests nothing. Anchors report SKIP when they drift; a stale
constant reports a clean run. Re-check the numeric cases whenever the thing they compare against
moves.

**Read the catcher names for a second reason: a golden test is not a catch.** `campaignteeth.py`
reported 11 of 13 caught, and four of those were caught by `DeterminismGoldenTest` alone — a
digest comparison that fires on *any* output change. Re-running those four with the golden test
excluded from the class list, three survived: the campaign's target range, its candidate-pool
width, and its hazard ramp could all be reverted to configurations the code's own javadoc records
as broken, and every property test still passed. Golden digests are change detectors. They are
regenerated by whoever deliberately retunes a constant, which is exactly when the regression they
were accidentally covering walks through. When a mutation's only catcher is a digest, snapshot,
or approval test, treat it as a survivor and go find the property — the fix here was twenty seeds
instead of five in the monotonicity sweep, and a hazard assertion per rung instead of at the two
ends.

## Baseline: 2026-08-01, first full run

Every harness here executed against the tree for the first time on 2026-08-01, the repairs below
having been what made that possible at all. **14 harnesses, 78 mutations, 0 survivors.**

    authteeth  9/9   errteeth   9/9   tourteeth   8/8   lensteeth 8/8   notfoundteeth 7/7
    detteeth   5/5   registry   5/5   stompteeth  5/5   unload    5/5   deskteeth     4/4
    retention  4/4   auditteeth 3/3   idateeth    3/3   rlteeth   3/3

Read that as a starting line, not a victory lap. A suite that catches every mutation someone
thought to write is only as good as the mutations, and two of these were aimed at deleted code
until this same day. The number worth watching is what a *new* mutation does — the ones added
here caught real gaps in `LeaderboardService` and `RedisConfig` that 78 existing ones did not,
because nobody had pointed a mutation at those files before.

Since that baseline, seven harnesses have been added by pointing mutations at classes nobody had
attacked before — `sessionteeth` (10), `gridteeth` (6), `trafficteeth` (9), `livingteeth` (11),
`campaignteeth` (12), `genteeth` (13), `landmarkteeth` (4). **21 harnesses, 143 mutations, 0
survivors.** Every one of those five found
at least one real unpinned guarantee on its first run, which is the argument for writing the next
one rather than re-running these.

`livingteeth` is the clearest case for writing the next one. It was aimed at the *sibling* of a
class that had just failed badly — same shape, same scheduling, same bounds — on the theory that
holes come in pairs. They did: two of its seven survivors were the identical scheduling holes
found next door. And `LivingMazeServiceTest` is the better suite of the two, which is the useful
half of the result. A suite that tests outcomes thoroughly can still miss every boundary,
because a boundary lapse produces no outcome — an unbounded run finishes, a stalled erosion
reports itself settled, a duplicated ticker just works twice.

Timing, for planning: roughly 1–3 minutes of Maven per mutation, so the full suite is on the
order of two to three hours. Run it in batches.

**Audit the anchors before you trust a clean run.** A mutation whose anchor no longer matches
reports SKIP, which is not a catch and not a survivor — it is a check that silently stopped
happening. Two of `lensteeth.py`'s had been in that state since the lens moved to an epsilon
band. The cheap way to find them: run each harness with `subprocess.run` stubbed to return
success, so only the anchor checks execute. The whole suite audits in about two seconds, and the
`SKIP` lines are the entire output you care about.

**Beware the inert mutation.** A change that alters no behaviour survives every test and reads
identically to a real gap. `lensteeth.py`'s epsilon mutation first scaled `delta` by 1e-9 —
against integer path costs and EPSILON = 1e-9, that reclassifies nothing. It "survived", and the
obvious next move was to write an assertion for the hole it implied. There was no hole. Before
believing a survivor, confirm the mutation actually changes an observable: print the value it
touches, or check that the mutated build differs from the clean one at all.

**The scripts could not run at all.** Sixteen of them hardcoded
`REPO = pathlib.Path("/root/daedalus-work/repo")` — a path from the sandbox they were written
in, which exists on no machine anyone would run them from. Every command this README documents
died on `FileNotFoundError` before its first mutation. They now resolve `REPO` from `__file__`,
as `detteeth.py` and `stompteeth.py` already did. Worth stating plainly: a mutation harness that
cannot start is the same as a mutation harness that reports everything caught — both leave you
believing guarantees are pinned when nothing has checked.

**Never leave a mutation harness unsupervised without a lock.** The first `fuzzteeth.py` run
was launched under a wrapper that was killed at a timeout; the Python process was orphaned and
kept mutating, and a second copy started against the same file. The "6/6 caught" the two
interleaved runs printed was worthless, and the tree was left holding a sabotaged generator.
`fuzzteeth.py` now writes a pristine sidecar before its first mutation (restored on startup, so
the *next* run repairs what a killed run left behind), restores after each mutation rather than
once at the end, restores on SIGTERM/SIGINT, and refuses to start while another run holds the
lock. Every other harness restores per mutation in a `finally`, which covers an ordinary crash and
Ctrl-C but did **not** cover SIGTERM, whose default action ends the process before `finally`
runs — and SIGTERM is exactly what a wrapper `timeout` sends. That gap was not theoretical: on
2026-08-02 a two-minute wrapper killed `trafficteeth.py` mid-mutation and welded quiet-tick
retirement shut in the working tree. The failure is silent and self-reinforcing, which is what
makes it worth a paragraph. The next run snapshots the mutated file as its *own* baseline, so
it restores to the mutation, reports that mutation as `SKIP (anchor x0)` — the anchor being the
code it had replaced — and reports nearly everything else as caught, because the welded-in
defect fails tests by itself. It printed 8/9 against a broken tree. `verdict.restore_on_signal()`
now converts SIGTERM and SIGHUP into an exception so the `finally` runs, and every script here
calls it before its first mutation. SIGKILL still cannot be caught: run one harness at a time,
and after any interrupted run check `git diff` on the mutated file before trusting a result.

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

**"No handler of ours" is not "no handler".** The STOMP `SEND` hole survived a deliberate check:
somebody (me, earlier) confirmed no `@MessageMapping` exists and wrote a Javadoc paragraph
reassuring the next reader that clients therefore cannot send frames. Both halves were true
except the "therefore" — Spring's simple broker handles `/topic` sends itself, without consulting
any application code. The general form is worth carrying: when reasoning that some input path is
inert, enumerate the *frameworks* on that path as well as your own handlers, and then send the
input and watch. The probe took four minutes and the reasoning had stood for months.

**Mutate the registration, not only the implementation.** `stompteeth.py`'s first mutation leaves
`StompSendRejectionInterceptor` completely correct and simply omits it from `WebSocketConfig`.
Every unit test still passes, because a unit test constructs the class itself — it cannot tell a
registered interceptor from an unregistered one, which is precisely the state the codebase was in
before this batch. Any guard that has to be *wired in* to work needs a mutation that unwires it;
otherwise the suite is proving that a class nobody uses behaves correctly.

**The load-bearing mutation found an unfalsifiable assertion, again.** `stompteeth.py`'s
unregister-the-interceptor mutation survived its first run, which meant `WebSocketForgerySmokeTest`
was green with the hole wide open. The cause was a converter mismatch inside the test: the
attacker sent a JSON *string*, Jackson serialised it as a JSON string, and the spectator's `Map`
payload type could never deserialise it — so the forged frame could not arrive whether or not
anything was guarding the channel. Sending a `Map` fixed it and the mutation is now caught. Note
the shape: the assertion was `isNull()`, and an assertion that something did not happen passes
beautifully when you have accidentally made it impossible for it to happen. That is the third
distinct instance of this failure in this file (`lensteeth.py`'s dead counter, `deskteeth.py`'s
`contains(...)`, now this) and it is always found the same way — by a mutation that should turn
the assertion red and does not.

**When every assertion flows through one function, mutate that function.** `DeterminismGoldenTest`
compares 23 digests, and all 23 are produced by a single canonicaliser. Blind it — return an empty
object for every node — and every digest equals every other, the comparison succeeds, and the test
reports 23 verified endpoints while verifying nothing. Three of `detteeth.py`'s five mutations
therefore attack the canonicaliser rather than the product. The general rule: find the funnel every
assertion passes through, and break the funnel. Coverage of the product means nothing if the
measuring instrument can be switched off silently.

**A probe that cries wolf is worse than no probe.** The determinism audit reported three drifting
endpoints on its first run and a nondeterministic solver on its second. All four were the probe's
own fault — per-process UUIDs it forgot to strip, a wall-clock field, and a mistyped solver id
whose 404 body embedded the request path. Each false alarm cost a round of investigation, and the
fourth nearly had me editing a solver implemented entirely with int arrays. Two habits came out of
it and both are in the test now: canonicalise identifiers by *shape* rather than by field name,
since an id inside a URL string is not something an exclusion list can name; and read the actual
diff before believing the verdict, every time.

**Throw *after* the damage and the test still passes.** The algorithm-id collision guard is four
lines, and `registryteeth.py`'s first mutation keeps the `throw` exactly as written while changing
`putIfAbsent` to `put` — so the built-in is overwritten and *then* an exception is raised. Any test
asserting only "a DuplicateAlgorithmException was thrown" goes green while the registry has already
lost the generator it was defending. The assertion that kills it is the boring one underneath:
after the refusal, `require(id)` must return the *same instance* it returned before. Whenever a
guard's job is to prevent a state change, assert the state, not the exception.

**A guard nothing currently triggers is a guard nothing currently tests.** One mutation survived:
changing `GeneratorRegistry`'s constructor from `builtIn.forEach(this::register)` to a raw `put`,
bypassing the collision check entirely. Every test stayed green — correctly, because the shipped
generator set has no duplicate ids, so the bypass is unobservable today. It stops being
unobservable the day someone adds a generator whose id is already taken, and the symptom then is
one of them silently missing at startup. The fix was to stop testing the current contents and
start testing the path: hand the constructor a deliberately duplicated list and require it to
refuse. Same lesson as the unused `ALLOW_EMPTY_404` exemption, arriving from the opposite
direction — there, permission that nothing exercised; here, a guard that nothing exercised.

**Check that the mutation actually mutates.** One `unloadteeth.py` mutation reported SURVIVED and
had proved nothing: it was meant to move the attribution snapshot from "around the whole plugin
boot" to "around registerAlgorithms only", and what it actually did was re-read the same value at
the same point — a no-op. A no-op mutation survives by definition, and reads in the log exactly
like a genuine gap in the tests. The tell is that a survivor should always be *explicable*: if you
cannot say in one sentence which assertion ought to have caught it and why it did not, suspect the
mutation before the suite. Rewritten to insert the snapshot after `registerAlgorithms`, it was
caught immediately.

**Mutate in the direction the fix could overshoot.** The plugin-unload work adds a removal path,
so the risk is not only "removes too little" but "removes too much" — a teardown that takes a
built-in with it would be strictly worse than the leak it fixes. So `unloadteeth.py` drops the
built-in refusal from `unregister` as its own mutation. Every leak-fixing assertion still passes
under it, because nothing about removing the plugin's own algorithms changes; only the assertion
that `recursive-backtracker` is still there afterwards goes red. Whenever a fix hands out a new
capability, mutate away the limit on that capability, not just the capability itself.
