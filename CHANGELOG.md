# Changelog

All notable changes to Daedalus are documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Versions before
`1.0.0` (the multi-module split + first audit pass) live in git history
under the `_migration/` portfolios.

## [Unreleased] — 2026-07-30

### Added

- **Campaign mode (ADR-006 idea #10) — completes the roadmap.** `GET /api/v1/campaign?seed=`
  returns a deterministic ladder of stages (omit the seed for today's shared campaign). Stage
  *n*'s maze seed derives from `(campaignSeed, n)` alone, so a campaign link replays
  byte-identical stages anywhere with no stored state. Each stage's difficulty is **measured,
  not assumed**: the service generates candidate mazes across three sizes, grades each with the
  new `DifficultyGrader`, and keeps the one nearest that stage's target that still clears the
  previous stage. Later stages declare hazards (`living`, `traffic`) but the service never
  starts a ticker — the client activates them through the existing opt-in endpoints, so their
  capacity caps and rate limits keep governing. Deliberately one endpoint: a campaign is a
  table of contents over the API that already existed, so every stage gets its own leaderboard
  partition (batch 2) and its own ghost (batch 3) for free, proven end-to-end in the tests.
  UI: a campaign panel with the stage ladder, per-stage boards, and hazards activating on entry.
- **`DifficultyGrader` in the theory module.** Grades a maze's playability from structure:
  detour factor (route length over perimeter), branchiness (dead ends per perimeter),
  scale, and a discount for braided alternate routes — reporting every measurement behind the
  score, so callers can audit it rather than trust it. Weights and label bands are *chosen*, not
  calibrated against human play, and the class says so; what it guarantees is **ordering**,
  which is what a ladder needs. Two ordering defects were caught by measurement while building
  it: normalizing dead ends per *cell* graded a trivial 3×3 above a 5×5 (tiny mazes spend a
  third of their cells on dead ends), and the original label bands put nearly every maze this
  project generates into "hard" or "brutal".

### Added

- **`ProdAuthPostureTest` — every endpoint's prod authentication posture, asserted rather than
  inherited.** Twelve endpoints were added across ADR-007 and not one of them made an
  authentication decision. They are all correctly closed, because `ProdSecurityConfig` ends in
  `anyRequest().authenticated()` — but "protected because nobody listed it" and "protected
  because somebody decided" look identical from outside, and only one of them survives a matcher
  being widened later. The chain already permits `GET /api/v1/maze/*`; **one extra asterisk**
  would publish the whole analytical surface — hardest route, distance field, sanctuaries,
  heuristic lens, fingerprint, tour, analysis, ghost — and nothing in the suite would have said a
  word. What existed before was `SecurityConfigProfileTest`, which checks `@Profile` annotations
  and no actual decision, and `ProdProfileBootTest`, which pins exactly one path, against a README
  that publishes an "Auth (prod)" column for the entire API.
  The test boots a real prod context and drives unauthenticated requests at all 32 endpoints,
  asserting each is refused or public per an explicit table — the README column made executable.
  A second test scans the controller sources and fails if any mapping is missing from that table,
  so a new endpoint cannot ship until somebody records which side of the line it belongs on. A
  third holds the README's published table to the same standard in both directions.

  **The first version of this test was written wrong, and the way it was wrong is the point.**
  Its expectation table was filled in from what the running server answered — which makes the
  test agree with the behaviour by construction, so it cannot find a behaviour bug, and it
  promptly failed to find three (see *Fixed* below). The second source of truth is what makes it
  work: the README says what the API promises, the boot test says what the server does, and the
  build now fails when they disagree. Teeth proven nine ways in `mutants/authteeth.py` —
  widening `maze/*` to `maze/**`, flipping `anyRequest()` to `permitAll`, closing the spectator
  permalink again, adding an unclassified endpoint, declaring one with a bare `@GetMapping` or
  the `value = ...` form, narrowing the source scanner back to its original regex, and both
  flipping and dropping a README row. All nine caught. A security test under default-deny passes
  before it is written and keeps passing if it breaks, so it needs the mutations more than most.

- **`ErrorContractTest` — every way the API can say no, held to one shape.** Twenty-one distinct
  failure modes driven at a running server, bodies compared against RFC 7807. The test that
  matters is the third one: it does not list failure modes, it *generates* them from the
  controller sources — every mapping gets the wrong verb and an uncoercible path variable, and
  any 4xx or 5xx that comes back without a `type` field fails the build. All five gaps found by
  this audit were on paths no test happened to visit, and a hand-written roster of failure modes
  is a list of the paths somebody thought of, which is the same blind spot in a different
  costume. A new endpoint is covered the day it is written. Teeth: `mutants/errteeth.py`, nine
  mutations. The load-bearing one removes the 405 handler **and** the roster entry naming it, so
  only the generated test can catch it — if that survives, the generated test is decorative.
- **`UnknownAlgorithmException` in the theory-facing core.** Carries the kind, the requested id,
  and every id that *is* registered, so a 404 tells the caller what to type instead of only that
  they were wrong. Deliberately a subtype of `NoSuchElementException` (source-compatible with
  what the registries threw before) rather than a reuse of it: mapping `NoSuchElementException`
  itself to 404 would have caught `Optional.get()` and `Iterator.next()` too, quietly turning
  genuine internal invariant failures into "not found".

- **`DeterminismGoldenTest` — determinism checked across a process, not across a cache hit.**
  Determinism is one of this project's loudest claims: a campaign link "replays byte-identical
  stages anywhere with no stored state", waypoints "derive from the maze alone", complexity fits
  reproduce exactly. Every test of that ran inside one JVM, and almost every one of those
  endpoints sits behind a Caffeine cache keyed on its inputs — so the second call returns the
  first call's object and the assertion passes whether the computation is deterministic or not.

  The bug class this cannot see is specific and real: anything reading `Object.hashCode()`
  identity, or `HashSet` iteration order over enums (enum `hashCode` is identity-based, so the
  order is stable within a run and arbitrary between runs). A tie-break fed by such an order
  gives every user a different "optimal" route depending on when the server last restarted.

  The oracle is a file of 23 digests recorded by a different JVM and committed to the repository,
  so every build is a cross-process comparison. Covered: seeded generation, the seeded campaign,
  all seven analytical endpoints, the tournament, a complexity fit, **all nine solvers**, and the
  algorithm catalogue. Teeth: `mutants/detteeth.py`, five mutations, three of them aimed at the
  canonicaliser rather than the product — blind that one function and every digest compares equal
  to every other and the test checks nothing.

  **The audit itself found nothing broken.** Sixteen endpoints captured, server restarted cold,
  all sixteen identical. Two false alarms along the way were both the probe's fault and are now
  the test's design constraints: identifiers are per-process (the first probe stripped only
  top-level keys and missed the daily maze's nested `maze.id`), and `elapsedMs` was 5 on the
  first solve after a cold start against 0–2 warm. A third apparent finding — "bidirectional-BFS
  is nondeterministic" — was a solver id typo producing a 404 whose `instance` field carries the
  request path, maze UUID included. That one changed the design: identifiers are now redacted by
  *shape* wherever they appear, because an exclusion list of field names cannot name an id
  hiding inside a URL.

### Changed

- **Off the Jackson 2 APIs Boot 4 marks for removal.** `MappingJackson2MessageConverter` →
  `JacksonJsonMessageConverter` in the STOMP smoke test, and `HttpStatus.UNPROCESSABLE_ENTITY` →
  `UNPROCESSABLE_CONTENT` (RFC 9110 renamed 422; the wire status is unchanged). With the Redis
  serializer below, the reactor now compiles with **zero** deprecation warnings — which is worth
  keeping at zero, because the one that mattered was invisible in a list of seven.

### Fixed

- **Two heuristic-lens mutations had been aimed at deleted code since the epsilon refactor.**
  Once the harness could start, an audit of every mutation anchor (run each script with
  `subprocess` stubbed, so only the anchor checks execute — a two-second pass instead of a
  multi-hour suite) found 17 of 19 harnesses aimed at live code and two that were not.
  `lensteeth.py`'s "must-expand uses <=" and "tie folded into must" still targeted
  `if (f < optimal)` / `f == optimal`, which the classifier replaced with an epsilon band
  (`delta < -EPSILON` / `delta <= EPSILON`). Both had been silently reporting SKIP ever since,
  and nobody saw it because the script could not run at all. Re-aimed; both caught.

  `idateeth.py`'s inert-cutoff mutation is retired to its docstring. It anchors on a line
  deliberately deleted from the solver, so it reported SKIP forever — harmless until the tally
  fix above started counting unresolved results as survivors, at which point it became a
  permanent phantom entry, and a survivor list that always has something in it is a survivor
  list nobody reads.

  **One thing this did not find, reported because the near-miss is the useful part.** A new
  mutation aimed at `EPSILON` first scaled `delta` by 1e-9 and survived, which reads exactly
  like an unpinned guarantee — the band bounds are all vacuously satisfiable when every cell
  lands in one band, so the conclusion was plausible enough to write a test for. The mutation
  was inert: path costs are integers and EPSILON is 1e-9, so every comparison landed where it
  already had. Re-aimed at the constant itself (`1e-9` → `1e9`) it is caught immediately, by two
  tests that already existed. The test written for the imagined hole was then measured against
  the harness — 8/8 mutations caught with it and 8/8 without — and deleted. An inert mutation is
  the most expensive kind of false negative: it does not merely fail to find a bug, it invents
  one and sends you writing assertions to cover it.

- **The mutation harness could not run, and called broken builds catches.** Two defects in the
  thing that verifies everything else. Sixteen of the nineteen scripts in `mutants/` hardcoded
  `REPO = pathlib.Path("/root/daedalus-work/repo")`, a path belonging to the sandbox they were
  authored in; every command `mutants/README.md` documents died on `FileNotFoundError` before
  its first mutation. And the verdict logic — thirteen near-copies of it — read "Maven exited
  non-zero" as "a test caught the mutation", which are different claims. A build that dies in
  POM resolution, or compilation, or an OOM-killed fork, exits non-zero having run no tests at
  all.

  Both were found the same way: `retentionteeth.py`'s first run reported a confident **4/4
  caught** while all four builds were failing before a single test executed. The five scripts
  that did guard against this checked for the literal string `COMPILATION ERROR`, which none of
  those failures print.

  The rule is now in one place, `mutants/verdict.py`, and it is *no named failing test, no
  catch*. Seventeen harnesses share it. Fixing the per-mutation verdicts turned out to be half
  the job — the summary line counted anything not spelled `SURVIVED` as caught, so a run whose
  every verdict read `NOT A CATCH` still printed "4/4 caught; survivors: none"; the tallies go
  through `verdict.is_catch` now too. Verified in both directions: with a deliberately unusable
  local repository the harness reports 0/4 and names all four as unresolved, and against the
  real build it still reports 4/4 with the specific test that caught each mutation.
  `rlteeth.py`, which could not start before this, now runs and catches 3/3.

- **The Redis leaderboard sets grew forever.** Only the per-maze key carried a bound (a 48h
  TTL). The global and per-generator sorted sets gained a member on every completed run and lost
  one never. The constructor's javadoc called that keeping "full history", and the phrase was
  doing a lot of work: `MazeController` caps `n` at 100 and every read is a `reverseRange` from
  rank 0, so rank 101 downwards was storage no request could reach. Twenty-two generators means
  twenty-two of these.

  The argument against it was already written down, one field away — the in-memory cap's own
  javadoc says retention past the deepest page anyone can request is pure growth, and the set was
  capped for exactly that reason. Only the Redis half was exempt from its own reasoning. `submit`
  now trims each set to `maxEntries` on write, so the config property that used to bound one
  backend bounds both.

  `removeRange(key, 0, -(maxEntries + 1))` deletes by *ascending* rank while every read here is
  descending, which means the correct call looks backwards and the wrong one looks right. That is
  why `LeaderboardRedisRetentionTest` asserts on **which entries survive** rather than on the
  arguments the call was made with: a trim aimed at the best end leaves the set exactly the right
  size while deleting exactly the wrong members, and `verify(zset).removeRange(...)` would wave it
  through. The test drives a fake with real sorted-set semantics — score order, inclusive rank
  windows, negative indices — so the assertions are about state. Teeth in
  `mutants/retentionteeth.py`: four breaks (no trim, partitions unbounded, wrong end, off by one),
  all four caught.

  The coverage ratchet earned its keep again here — the new tests pushed the server past its 0.94
  ceiling and failed the build until the threshold was re-pinned to 0.92/0.95, which is the point
  of pairing tests with a threshold move instead of banking slack a later regression can spend.

- **The Redis leaderboard backend wrote a format it could not read.** `RedisConfig` handed the
  template a hand-built `ObjectMapper` with `activateDefaultTyping(validator, NON_FINAL)`, and the
  two halves of that disagreed. Writing uses the value's runtime type, and `LeaderboardEntry` is a
  `record` — **final** — so no type header was emitted. Reading targets `Object`, which is
  non-final, so the deserializer demanded one. Every read threw `SerializationException`.

  The interesting part is how completely that hid. `LeaderboardService` catches read failures and
  falls back to its in-memory set, so with `daedalus.redis.enabled=true` the boards still answered
  — out of memory, one warn line per call — while every completed run kept appending unreadable
  JSON to sorted sets that no code path could read back. Two of those three keys carry no TTL, so
  the backend's only measurable effect was Redis growth. It looked like it worked and did nothing.

  Fixed by moving to Spring Data's Jackson 3 `GenericJacksonJsonRedisSerializer` with default
  typing enabled explicitly, which writes an `@class` property for every value regardless of
  finality. Enabling it *requires* a `PolymorphicTypeValidator` — Jackson 3 removed the
  laissez-faire default — and that requirement was worth having: the old configuration, asked to
  read `["javax.naming.InitialContext",{}]`, constructed one. The replacement allows
  `com.daedalus.*` and collections and refuses everything else.

  Nothing caught this because the only Redis test asserted the beans **exist**. A serializer bean
  that constructs is not a serializer that works, and the gap between those two claims was the
  bug's entire hiding place — `RedisSerializationRoundTripTest` now closes it by round-tripping
  through `RedisConfig`'s own factory method. Three of its four assertions fail against the old
  configuration; the fourth is documented in the test as not having teeth, because `ArrayList`
  is not final and therefore always did round-trip. That is the bug's shape in one line: it bit
  exactly the final types, and a fixture stored in a list would have missed it.

- **A stopped plugin's algorithms kept working.** `shutdownAll()` called `stop()` on each plugin
  and closed its `URLClassLoader` — and neither registry had any removal path, so everything the
  plugin had contributed stayed in the global maps. Closing a loader does not unload classes
  already loaded from it, so those objects were perfectly alive: a "stopped" plugin's generator
  was still listed by `/api/v1/algorithms`, still resolvable, and still able to serve a request.
  On Windows the JAR also stays locked while its classes are reachable, which is the file-handle
  problem the classloader hygiene work was supposed to have solved.

  Both registries now have `unregister(id)`, and it **refuses built-ins**. That refusal is the
  point rather than a detail: a removal path reachable from plugin teardown is a removal path a
  buggy teardown can aim at `recursive-backtracker`, which would undo the collision guard from
  the opposite direction — a plugin that cannot *replace* a shipped algorithm could otherwise
  simply delete one. A fix for a leak that deletes built-ins on shutdown is worse than the leak.

  Attribution was the awkward part. Every plugin shares one `PluginContext` and therefore one
  registry, and `register` takes only the algorithm, so nothing records who contributed what.
  `PluginManager` now diffs the registry's id set across each plugin's whole boot — not just
  `registerAlgorithms`, because a plugin can register from `start()` too — and unregisters
  exactly those ids on shutdown. It is honest about its limit: a plugin that registers later,
  from a thread it started, is unattributable and is left alone rather than guessed at. This
  needs no change to the SPI plugin authors compile against.

  Unloading covers **every** entry, not only the `STARTED` ones. A plugin that registered two
  algorithms and then threw in `start()` never reaches `STARTED`, and its contributions are in
  the registry all the same — an unload keyed on state would have leaked precisely the failure
  case while handling the healthy one.

  The coverage ratchet earned its keep here: the first version of the test registered only
  generators, and the floor dropped 1 point because the entire solver branch of the unload was
  dead code as far as the suite was concerned. Teeth in `mutants/unloadteeth.py`.

- **A plugin could silently become a built-in algorithm.** `PluginContext` hands every plugin the
  live `GeneratorRegistry` and `SolverRegistry`, and `register` was a bare `map.put` — so any
  third-party JAR dropped in the plugins directory could declare
  `id() == "recursive-backtracker"` and take the name. Measured with a hostile generator: the
  registry's size did not change (2 → 2), `/api/v1/algorithms` still advertised the id while
  carrying the impostor's description, `require(...)` returned the impostor, and neither registry
  has an unregister, so the substitution outlived the plugin for the life of the process.

  Everything this project claims about reproducibility resolves through that lookup — the daily
  challenge, campaign stages, the seeded waypoint tour, and the cross-process digests in
  `DeterminismGoldenTest`. A plugin could move all of them at once, and the only symptom visible
  from outside would be that yesterday's seed makes a different maze today.

  Both registries now refuse a collision with `DuplicateAlgorithmException`, naming the class
  that holds the id and the one turned away. Refusing rather than warning costs nothing:
  `PluginManager` already contains a throwing plugin, marks it `FAILED`, boots the rest, and the
  plugin subsystem's health indicator reports it — so a colliding plugin now fails by the same
  route as any other broken one, and the built-in it wanted keeps working. Built-ins register
  from the constructor, through the same guarded path, so a duplicate among the shipped set fails
  at startup instead of silently dropping one.

  The guard's first draft exempted re-registering the *identical instance*, on the theory that a
  double-boot should not fail. Writing the test for it showed nobody could name a path that
  reaches it, so the exemption was permission granted for a case that does not exist — the same
  shape as the `ALLOW_EMPTY_404` flag and the one-sided coverage ratchet. Removed: a taken id is
  taken. Teeth in `mutants/registryteeth.py`; the load-bearing mutation keeps the throw and moves
  the overwrite *before* it, so a test asserting only "an exception was raised" would pass while
  the built-in is gone anyway.

- **Any connected client could publish a forged frame onto any STOMP topic.** The client inbound
  channel had two interceptors: one authenticating `CONNECT`, one authorising `SUBSCRIBE` to an
  owned session's player feed. Neither looked at `SEND` — and because the broker is Spring's
  *simple* broker with `/topic` enabled, a client frame addressed to a `/topic` destination is
  never dispatched to application code at all. The broker relays it. Measured, not theorised: a
  second anonymous client sent one frame to another player's `/topic/session/{id}/player` and the
  spectator received it, indistinguishable in shape from a server-published move. The same worked
  on `/topic/maze/{id}`. `StompSendRejectionInterceptor` now refuses every client `SEND`.

  **Two things about how this hid.** First, `WebSocketConfig`'s own Javadoc said "do not read
  their presence as evidence that a client can send frames today" — a reassurance written after
  correctly confirming that no `@MessageMapping` exists. The observation was right and the
  inference was wrong: no mapping proves no code *of ours* handles a client frame, not that the
  frame goes nowhere. The simple broker is application code somebody else wrote, and it was
  listening. Second, note which direction got the attention. Real design work went into who may
  *read* an owned session's feed; nobody asked who may *write* to it. From the outside a guard on
  one direction of a channel is indistinguishable from a guard on the channel.

  What an attacker got was display, not state — `PlayerMovedEvent` is published by the server
  from its own record, so scores, the leaderboard and waypoint progress were never forgeable. But
  the spectator seam, the ghost racer and the multiplayer view all render what arrives on these
  topics, and "the number is right, the picture is a lie" is not a defensible place to stand.

  The refusal is **total** rather than per-destination, because this application has nothing for
  a client to say. That is a fact about the codebase rather than a principle, so
  `StompSendRejectionTest` scans for message-mapping annotations and fails the build if one
  appears — the day a real client-to-server message is added, the blanket rule becomes wrong and
  the build says so instead of the feature quietly not working.
- **The last 27 errors with no body at all.** `ResponseEntity.notFound().build()` appeared 27
  times across `MazeController`, `InsightController` and `AgentController`, each answering 404
  with nothing in it — the remaining hole after the error-contract audit, and a perverse
  inversion: a typo'd URL came back with a helpful problem detail while an expired maze id came
  back with silence. The expired maze is the common case by a wide margin (mazes live in a
  bounded Caffeine cache and get evicted) and the one the caller can act on. All 27 now throw
  `ResourceNotFoundException` and answer in the house shape, saying which kind of thing was
  missing and, for a maze, that regenerating with the same seed reproduces it exactly.

  A helper returning a populated `ResponseEntity` was the obvious repair and does not compile:
  `ResponseEntity<AnalysisResponse>` cannot carry a `ProblemDetail`, so every affected method
  would have had to widen its return type to `Object`. Throwing keeps the signatures.

  **Several of those 27 were never answering the same question.** `POST /session/{id}/move`
  404s both when the session is unknown *and* when the session is fine but its maze has been
  evicted — different problems, previously identical replies. `GET /maze/{id}/ghost` 404s for
  "no such maze" and for "nobody has finished this maze yet", which call for opposite reactions
  (regenerate, versus keep playing). `POST /maze/breed` named neither of the two parents it
  could not find. `GET /complexity` 404s for an unregistered generator and for an unmeasured
  metric; the first is now an `UnknownAlgorithmException` listing all 23 generators, the second
  names the metrics that exist. One case deliberately did *not* gain detail: `join` with the
  multiplayer flag off returns the same "no such session" body an unknown id produces, because
  the 404 is there to make the endpoint look absent rather than disabled, and a more helpful
  message would turn it into a feature-flag oracle. That is asserted, not just intended.
- **`ComplexityLabService` swallowed every runtime exception from its registry lookup.**
  `catch (RuntimeException unknown) { return null; }` collapsed "no such generator" into the
  same null as "no such metric" — and, being a catch-all, would have turned any unrelated
  failure in that lookup into a silent 404 too. The lookup now propagates.
- **A client typo answered 500.** `POST /api/v1/maze/generate` with a mistyped `generatorId` and
  `POST /api/v1/maze/{id}/solve/{solverId}` with a mistyped solver both returned **Internal
  Server Error** with a stack trace in the log, because both registries' `require(...)` threw a
  bare `NoSuchElementException` and `ApiExceptionHandler` had no handler for it. The two
  most-used endpoints in the API were the two reporting a user's typo as a server fault, while
  every analytical endpoint added later answered a clean 404. Both now answer **404** with a
  problem detail listing all 23 registered generators (or all 10 solvers). The underlying mistake
  is worth naming: `find` returns an `Optional` and `require` throws — the controllers called
  `require` on caller-supplied input, which is the method for internal invariants.
- **Three failure modes returned the right status with the wrong body.** A missing required query
  parameter, the wrong HTTP verb, and an unsupported `Content-Type` all fell through to Boot's
  default `{timestamp, status, error, path}`, as did an unmapped path. These are more dangerous
  than the 500s: the status code looks correct from the outside, so nothing goes red, while a
  client reading `detail` and `title` off the documented RFC 7807 contract silently gets nulls.
  Four new handlers, and the 405 now carries the `Allow` header RFC 9110 §15.5.6 requires.
- **Three shipped features did not work in prod at all.** The `#session=` spectator permalink,
  the ghost racer and the fog-of-war agent's free re-poll are documented public in the README's
  "Auth (prod)" column and were all being refused by `ProdSecurityConfig`'s default-deny rule —
  `GET /api/v1/session/{id}`, `GET /api/v1/session/{id}/tour`, `GET /api/v1/maze/{id}/ghost` and
  `GET /api/v1/agent/{id}` answered 401 to the anonymous caller they exist for. This system has
  exactly one account, so "authenticated" here meant "only the operator", which makes a spectator
  link nobody can spectate and a shareable ghost nobody can watch. All four are now permitted
  explicitly, with **single-segment** matchers: `/api/v1/session/*` deliberately does not reach
  `/session/{id}/join`, and `/api/v1/agent/*` deliberately does not reach `/agent/{id}/step` —
  both of those spend server state and stay closed. Found only because the README and the
  filter chain were finally compared to each other.
- **`GET /api/v1/session/{id}/tour` reached Held-Karp with no rate limit.** It reads like a cheap
  progress lookup and was metered as one — but `progressFor` calls `tourFor`, so a request that
  misses the tour cache runs the same `O(2^k · k²)` exact TSP that its sibling
  `GET /api/v1/maze/{id}/tour` carries a `mazeSolve` limiter for. Two routes to one computation
  and only one of them counted; the limiter had been placed by reading the method, not by
  following the call. Now on the `mazeSolve` budget, which matters more since the endpoint is
  also anonymously reachable as of this release.
- **The API table in the README was two rows short.** `GET /api/v1/complexity/metrics` and
  `POST /api/v1/session/{id}/join` were live and undocumented. The cross-check test found both
  on its first run.
- **The endpoint scanner could not see two annotation forms.** `ProdAuthPostureTest`'s
  completeness scan required a parenthesised string literal, so `PluginController`'s bare
  `@GetMapping` and `MazeController`'s `@GetMapping(value = ..., produces = ...)` were invisible
  to it — and `GET /api/v1/plugins` was consequently the one endpoint in the API with no posture
  on record, in the test whose entire job is that no endpoint lacks one. The scanner now counts
  annotations independently of parsing them and fails on any mismatch, so a form it does not
  understand is a build failure instead of a silently smaller sweep.
- **The coverage ratchet had stopped ratcheting.** `jacoco:check` enforced a floor and nothing
  else, so it caught regressions and never noticed the floors going stale as coverage climbed.
  Audited across all five modules:

  | module | floor was | actual | slack |
  |---|---|---|---|
  | daedalus-server | 0.79 | 0.910 | **+12.0 pts** |
  | daedalus-plugin-api | 0.00 | 0.130 | no guard at all |
  | daedalus-desktop | 0.00 | 0.105 | no guard at all |
  | daedalus-core | 0.87 | 0.901 | +3.1 pts |
  | daedalus-plugin-runtime | 0.84 | 0.870 | +3.0 pts |

  Server coverage could have fallen by a ninth of the codebase before the build objected, and the
  README's claim of "a per-module JaCoCo coverage ratchet that fails the build on regression" was
  only meaningfully true for two of five modules. `TESTING.md` had prescribed exactly the right
  policy — pin each module a few points under actual, "raising it as coverage rises" — and, like
  most conventions that rely on someone remembering, it was not followed.
  The rule now carries a **maximum** alongside the minimum: drift more than 3 points above the
  floor and the build fails asking for the bump, which makes the ratchet mechanical rather than
  aspirational. Floors raised to 0.90 (server), 0.89 (core), 0.85 (plugin-runtime), and real
  non-zero floors set for the two modules that had none. The cost is honest: improving coverage
  now occasionally means a one-line pom edit, paid by the person who improved it rather than by
  whoever regresses it six months later. Both directions proven by `mutants/ratchetteeth.py` —
  set the floor above actual and the minimum fires, leave it 12 points stale and the maximum does.
- **The JavaFX desktop froze for up to 1.8 seconds per click, on an assumption that used to be
  true.** `MainController` ran generation and solve inline on the JavaFX Application Thread, and
  said so in a Javadoc that also named its own trigger for change: *"fast enough at the
  Spinner-bounded sizes (≤ 128² = 16 384 cells) that we don't background them; if a later change
  pushes that into the multi-second range, wrap the calls in a Task."* Nobody re-measured it
  across twenty features. Re-measured now, at the spinner's own maximum:

  | operation at 128×128 | on the FX thread |
  |---|---|
  | hunt-and-kill generate | **1101 ms** |
  | IDA\* solve, perfect maze | **1783 ms** (spends its node budget, then refuses) |
  | IDA\* solve, dungeon | **1518 ms** |

  Every millisecond of that is a frozen window — no repaint, no input, and on some desktops the
  "not responding" overlay. The assumption was true when written; the code that invalidated it
  lives in another module, which is exactly why a documented assumption needs re-measuring rather
  than re-reading. Both operations now run on a `javafx.concurrent.Task`, the buttons disable
  while one is in flight (two concurrent Generates could otherwise race to assign the current
  maze), and the worker thread is a daemon so it cannot outlive the window.
- **The desktop was a second, unhandled consumer of `SolverBudgetExceededException`.** When IDA\*
  gained its node budget, only the REST layer learned to translate it. The desktop happened to
  catch `RuntimeException` and print the message, which reads acceptably by luck rather than
  design — the exception's text was written to make sense outside the API. That is now explicit:
  `DesktopWork.describeFailure` reports a budget refusal in its own words with no "Solve failed:"
  prefix, since it is a cost guard rather than a crash, and unwraps `ExecutionException` because
  that is how a Task hands a failure back.

- **`POST /session/{id}/move` had no rate limit, and it is the most expensive write on the
  surface.** Counting annotations across the API found 10 of 32 endpoints unmetered. Most are
  cheap reads and deliberately stay that way; this one is not. A move mutates the session, feeds
  traffic tracking and ghost recording, and publishes a `PlayerMovedEvent` to every plugin
  listener **synchronously, inside the session lock** — the project already reasoned carefully
  about a 60 ms listener serialising a session's moves, but never bounded how fast moves could
  arrive. Measured against the running server on the default profile:

  | endpoint | result |
  |---|---|
  | `POST /session/{id}/move` | **1206 accepted in 6.0 s (201/s), never throttled** |
  | `POST /agent/{id}/step` | 1200 accepted, then 429 — `agentStep` budget working |

  The two are the same shape of traffic, and the agent endpoint's own config comment says so:
  "a blind walk is hundreds of tiny requests by design". Its twin would have sustained roughly
  ten times the rate that reasoning allowed. A new `sessionMove` budget gives moves the same
  1200/min; re-measured after the fix, the endpoint accepts exactly 1200 and then answers 429
  with the standard ProblemDetail. Nobody removed the annotation — it was simply never added,
  which is why the fix below matters more than the annotation does.
- **`application.yml` documented a maze cache that did not exist.** A post-ADR-007 configuration
  audit found the file declaring `daedalus.cache.maze-cache-size: 256` and
  `maze-cache-ttl-minutes: 30`, while `MazeGenerationService` reads `daedalus.maze.cache.max-size`
  and `daedalus.maze.cache.idle-ttl` — different keys entirely. The real cache therefore held
  **5,000 mazes for two hours** against the 256-for-30-minutes the file advertised, a twentyfold
  difference in footprint, and an operator tuning the documented knob changed nothing at all.
  Undocumented configuration is a nuisance; configuration that is documented and inert is worse,
  because the value looks deliberate and survives review. Behaviour is unchanged — the defaults
  were always the live ones — but the file now describes reality and the knob works.
- **Five config blocks the code reads were missing from `application.yml` entirely** — the play
  session store, the leaderboard cap, the distance-field/lens payload cap, and the tournament's
  four bounds. All are now documented alongside the rest, with the environment overrides the
  other blocks use.

### Added

- **`DesktopWork` — the desktop's long operations as plain `Callable`s, so they are testable.**
  A `javafx.concurrent.Task` cannot run headless (its state transitions go through
  `Platform.runLater`), and this module deliberately carries no TestFX or Monocle — the existing
  tests say so outright. Splitting the work from the wrapper keeps the part with behaviour under
  test and leaves only glue in the controller. Six tests, including one that the job is *lazy*:
  if building it did the generating, moving to a Task would have relocated the freeze to the
  button click rather than removing it.
- **`RateLimitCoverageTest` — three scans over the controller sources.** Every state-changing
  endpoint (POST/PUT/PATCH/DELETE) must carry `@PerKeyRateLimit`; every budget named in code must
  exist in `application.yml`, since one naming a missing instance silently limits nothing; and
  every configured limiter must be named by some endpoint, since one guarding nothing is dead
  weight that reads as protection. The allowlist for unmetered writes is empty and documented as
  worth keeping empty. The rule is deliberately scoped to writes: extending it to GET would force
  a dozen annotations whose only effect is noise, and a rule everyone waives is worse than none.
- **`ConfigCoverageTest` — the durable fix, checked in both directions.** It scans the server's
  sources for `${daedalus.*}` references and cross-references them against `application.yml`,
  failing the build on a key the code reads and the file omits *or* a key the file declares and
  nothing reads. Keys bound wholesale by `@ConfigurationProperties` are exempted by prefix rather
  than by name, and a third test pins that the exemption stays narrow — a single prefix of
  `daedalus` would silently forgive the entire tree.
- **`BoundedStoresTest` now scans for caches rather than naming three.** The audit counted
  **nine** Caffeine caches in the server against three named eviction tests. All nine declared a
  `maximumSize`, so the "bounded everywhere" rule held — but it held because everyone remembered,
  which is a run of luck rather than a property. The new test walks the sources and fails on any
  `Caffeine.newBuilder()` without a `maximumSize`, so a tenth cache is covered the moment it
  exists. Same reasoning as the registry-driven generator fuzz: a hand-written roster is correct
  the day it is written and quietly incomplete afterwards.

### Added

- **Heuristic lens (ADR-007 idea 8) — completing the roadmap, and not the way it was written.**
  `GET /api/v1/maze/{id}/heuristic-lens?heuristic=MANHATTAN|LANDMARK|INFLATED` partitions a maze
  into the three bands that *explain* A\*'s work, with an overlay in the UI.
  The ADR asked for "measure where A\*'s heuristic lies most, and overlay it". That was measured
  first and rejected: per-cell heuristic error against wasteful expansion correlated anywhere from
  **+0.42 to −0.17** across perfect, braided and dungeon mazes — inconsistent in magnitude and
  unstable even in sign. An overlay built on it would have been a convincing picture that explains
  nothing. What A\* actually obeys is exact, not statistical: it expands a cell only when
  `f = g* + h` is at most the optimal cost `C*`. So the lens reports **must expand** (`f < C*`, no
  tie-breaking can avoid these — this region *is* the heuristic's cost), **tie decides**
  (`f = C*`, where measured on a 21×21 dungeon the band holds 88 cells against a mandatory 30, so
  tie-breaking matters more than the heuristic there), and **never touched** (`f > C*`, of which
  A\* expanded **zero** across every configuration measured — reported as a live check rather than
  assumed).
  That makes "a better heuristic" a measurable claim: the four-landmark ALT heuristic drops the
  mandatory band from 925 cells to **0** on a 31×31 perfect maze and cuts real expansions by 1.8×
  to 5.5×.
- **A deliberately inadmissible heuristic, because a check that can only report zero cannot be
  tested.** `INFLATED` (Manhattan × 3) was added after a mutation survived: the test asserted
  `expandedAboveOptimal == 0`, so a mutation that never incremented the counter was invisible.
  An overestimating heuristic gives the counter something it must detect — and demonstrates the
  weighted-A\* trade honestly. Measured on a 31×31 dungeon it cuts expansions from 341 to 213 and
  returns a **96-step route where the optimum is 88**. The response says so outright.
- **SpotBugs caught float equality in the new lens, and it was a real trap.** The band logic
  compared `f == C*` exactly. That happens to be correct for all three heuristics wired up —
  they return integral values on a unit-cost grid — but the code accepts an arbitrary
  `ToDoubleBiFunction`, and `Heuristics.EUCLIDEAN` already exists in the codebase: with it, a cell
  whose `f` is exactly `C*` would fall into the tie band or the never band depending on the last
  bit of a square root. Now compared against an epsilon, the same fix this project applied once
  before to float comparison of cell costs.

- **Solver tournament with confidence intervals (ADR-007 idea 10) and adversarial seed search
  (idea 7).** `GET /api/v1/tournament?generator=&size=&mazes=&braid=&seed=` runs every registered
  solver over a deterministic sample of mazes and reports, per solver, mean work with a
  **Student-t** 95% interval, the median, the spread as a coefficient of variation, mazes won,
  and how often it found a shortest route. The UI adds a **Solver tournament** panel.
  **The headline is not the ranking — it is how much the ranking can be trusted.** ADR-007 sold
  this as "a tournament says which solver is *actually* better"; measurement says that depends
  entirely on the maze. On perfect mazes dead-end filling won 30 of 30, so one race already gave
  the right answer, and the response says so. On braided mazes the winner split four ways out of
  16 and wall-follower's spread reached **94% of its own mean** — a single race there is close to
  a coin flip, and no single race would reveal the instability. So the report leads with spread
  and with **statistically indistinguishable pairs**: BFS, Dial and Dijkstra come out tied because
  all three explore essentially every cell, and printing them as 1st, 2nd and 3rd would be a
  ranking invented out of rounding error.
  Idea 7 falls out of the same sample: the maze where the leader does worst against the runner-up
  is reported by **seed**, and because the sample is deterministic that seed regenerates exactly
  that maze — the UI offers a link to load it. Verified in the sweep by regenerating it.
  A solver that spends its node budget is excluded after three refusals and its statistics are
  **withheld rather than averaged**: measured on 19×19 dungeons IDA\* finishes five mazes before
  its third refusal, and a mean over those five would be survivorship bias with an error bar on
  it. The count of finished mazes is reported so a reader can see what was discarded.
- **`SampleStats` in `daedalus-core`** — mean, median, sample standard deviation, coefficient of
  variation, Student-t intervals and paired differences, with the statistics kept out of the
  Spring layer so they can be tested in a pure JVM against hand-computed values. Three decisions
  worth naming: the interval uses **t, not 1.96** (at n = 8 the normal quantile is 21% too
  narrow, which is exactly the error that manufactures a difference); comparisons are **paired**,
  though the docs record that pairing bought nothing on this project's own A\*-versus-BFS data
  because BFS is nearly constant; and skew is flagged by the standard **nonparametric skew**
  coefficient rather than a threshold picked to look strict — the first version demanded half a
  standard deviation and failed to notice `{10, 11, 12, 13, 900}`, because an outlier inflates
  the standard deviation faster than it moves the mean off the median.

### Fixed

- **IDA\* could run for minutes on a maze the API happily accepts — it now gives up in about a
  second.** Probing solver workloads for the tournament idea turned up an unbounded request on a
  public endpoint. Measured on dungeons: 15×15 instant, **21×21 nine to sixteen seconds** (~90
  million node expansions), **25×25 abandoned after 300 seconds still running**. Every other
  solver finishes the 21×21 dungeon in under 40 ms, and the UI's "Compare all solvers" runs IDA\*
  alongside the other nine, so four extra rows of maze turned a slow page into one that never
  loads. Iterative deepening re-searches from scratch under each new f-bound, and a rock-heavy
  looped graph makes every pass expensive — no traversal tuning fixes that, only a bound.
  `IDAStarSolver` now carries a 5,000,000-expansion budget (~1 s at the measured ~5.7 M/s) and
  throws `SolverBudgetExceededException`, which the API answers as **422** with the solver id and
  the budget in the ProblemDetail. Measured after: the 21×21, 25×25 and 41×41 dungeons all refuse
  in 0.8–1.4 s, a 51×51 perfect maze still solves optimally in 0.13 s, and compare-all on a
  dungeon fell from over 16 s to **0.94 s** with nine solvers answering and one honestly refusing.
  A 512×512 perfect maze also now refuses in under a second instead of driving the recursive
  search toward the stack limit.
  **This is a deliberate behaviour change:** the 21×21 dungeon used to return a correct answer
  after 16 seconds. It was never given the option of returning an empty path instead — the
  `MazeSolver` contract reads an empty list as "unreachable", so a budget-exhausted search
  reporting one would put a confident false claim into the compare table, the arena and the
  sweep. Refusing loudly is the only answer that does not lie in a data structure.
- **`sweep/api-sweep.py`'s `call()` had an `expect=` parameter that was never used.** It looked
  like a status assertion and asserted nothing — three call sites passed `expect=400`, `422`,
  `None` and got no checking whatever. Removed rather than implemented, since every caller
  already compares the status it got. Error bodies are now parsed as JSON so a check can assert
  on a ProblemDetail's fields instead of substring-matching a truncated string.

### Added

- **Distance heat map (ADR-007 idea 6) and sanctuary placement (ADR-007 idea 5).**
  `GET /api/v1/maze/{id}/distance-field?from=GOAL|START` returns every cell's walking distance
  from a landmark, and the UI shades the maze with it — one hue, monotone in lightness, the
  near-zero end receding into the floor. `GET /api/v1/maze/{id}/sanctuaries?k=` solves metric
  k-center by farthest-first greedy (a 2-approximation, and the best guarantee available unless
  P = NP), reporting the covering radius, how many cells are actually served, and *which* cell
  is served worst — drawn as a ring, the loneliest place in the maze. Measured on a 21×21 perfect
  maze the radius falls 203 → 149 → 90 → 48 → 39 as k goes 1 → 8. Unreachable cells report `-1`
  rather than being omitted, so a dungeon's rock stays unshaded instead of being drawn as
  distance zero. The field is payload-capped at 16,384 cells and **refused with a 400 that
  explains itself** above that — the sweep stays linear at 512×512, the 1.5 MB of JSON does not,
  and silently downsampling a per-cell overlay would be a lie told in colour.
- **`DistanceOracle` stays dormant on purpose, with a measurement behind it.** ADR-007 justified
  the heat map as "revives `DistanceOracle`". It does not, and shouldn't: the oracle tabulates
  all-pairs distances for O(1) lookups, caps itself at 4,096 cells (the table is `V²` shorts —
  32 MB at 64×64), and a heat map needs one source, not all pairs. It also loses on its own
  ground — computing every cell's eccentricity measured **1,738 ms** precompute-then-scan against
  **1,485 ms** for running the same sweeps directly, allocating nothing. It only pays for many
  random-pair queries, which nothing here does. Eight of the nine `theory` classes are now
  reachable from the product; the ninth is unreferenced by decision rather than neglect.

### Fixed

- **The heat map looked broken on first render and was not — the legend now says why.** The
  overlay showed no smooth halo around the goal: bright patches mid-maze, sharp discontinuities
  everywhere. Checking the numbers rather than the picture, the field is 0 at the goal and its
  four *physically adjacent* cells measure 201, 1, 189 and 157. A maze distance field is walking
  distance, so touching cells are remote when a wall stands between them, and every abrupt change
  of shade marks a wall doing that work — the most informative thing the overlay shows. Both the
  legend and a test now pin it, so the next reader does not "fix" the correct behaviour.

### Added

- **Hardest-route mode (ADR-007 idea 3) — and the roadmap entry for it was wrong.**
  `GET /api/v1/maze/{id}/hardest-route` returns the longest simple route from start to goal
  alongside the shortest, the ratio between them, the maze's independent loop count, and whether
  the answer is a proven optimum or a lower bound (longest-simple-path is NP-hard, so the search
  is budget-bounded and says which it gave you). The UI adds **Hardest route**, drawing the walk
  in gold. ADR-007 proposed this as a start/goal *placement* mode — "put them on the longest
  simple path instead of the extremes" — and ten minutes of measurement killed that: a perfect
  maze is a tree, a tree has exactly one simple path between any two cells, so on 22 of the 23
  generators the proposed mode changes nothing (measured: 145 and 145 steps on a 15×15). What
  is worth shipping is the *measurement*, which is zero on a tree and large once loops exist —
  the same 21×21 braided at 0.5 goes 203/203 → 56/260 (**×4.6**), a dungeon measures 40 against
  122, and thirty erosion ticks took a living maze from ×1.00 to ×2.69 while opening 31 loops.
  On a tree the response says so outright and names the operations that open loops, because a
  feature that is honest about being inert beats one hiding it behind a number.

### Fixed

- **`LongestPath` threw `StackOverflowError` on every perfect maze from 200×200 up.** The search
  recursed, and a 512×512 tree — a size `GenerateRequest` explicitly permits — has a unique
  start-to-goal route tens of thousands of cells deep. That is an `Error`, not an exception,
  escaping a public core API and surfacing as a 500. Braided mazes hid it completely, because
  the visit budget ran out at shallow depth long before the stack did, which is how this
  survived a green suite for so long. The frames now live in arrays sized from the grid, with
  identical traversal order and identical results; a 512×512 perfect maze returns a
  proven-optimal 74,268-step route in 74 ms. Pinned by a 300×300 regression test that fails with
  `StackOverflowError` against the previous implementation.
- **`LongestPath` answered "there is no route" about mazes anyone can walk.** On a 41×41 at
  braid 0.5 (and a 61×61 at braid 1.0) the DFS spent its entire two-million-visit budget in the
  cycle-rich middle of the maze without once reaching the goal, and returned `length = -1` with
  an empty path. The incumbent is now seeded with the BFS shortest path, so the result is a real
  route at worst and the budget is spent improving rather than hunting for a first success;
  `exact` is untouched, so a seeded-but-unimproved answer is still correctly labelled a lower
  bound. This changed a documented contract — the old test asserting `-1` for a starved search
  was rewritten rather than deleted, and it explains why.

### Added

- **Generator invariant fuzzing (ADR-007 idea 9) — 23 generators go from "presumably fine" to
  measured.** `GeneratorInvariantFuzzTest` property-tests every registered generator against the
  invariants that hold whatever the algorithm — dimensions honoured, walls agreed on from both
  sides, no opening leading off the grid, every carved cell mutually reachable, identical output
  for an identical seed, different output for a different seed, and *if* a generator fills the
  grid then it must be a spanning tree. 506 generations across 11 shapes (1×1, 1×7, 7×1, 2×9,
  9×2, 16×24 and friends — the degenerate and lopsided inputs where generators actually break)
  and 2 seeds. **Result: zero violations.** Driven by the injected `GeneratorRegistry` rather
  than a hardcoded roster, so a newly wired generator is covered the moment it is registered;
  the spanning-tree rule is likewise stated as a conditional, so the Dungeon generator opts out
  by being half rock rather than by being named in an exclusion list. That is the difference
  from core's existing `PerfectMazePropertyTest`, which checks the same tree contract over a
  hand-listed **8** generators at one size and one seed — it stays (pure-JVM, no Spring, faster
  signal), and this is the wider net over the other 15.
- **`mutants/fuzzteeth.py` — six deliberate breaks proving the fuzz can fail.** Zero violations
  is exactly what a vacuous test reports, so the harness sabotages Binary Tree six ways (a
  one-sided opening, an opening off the grid edge, the seed mixed with the clock, the seed
  ignored entirely, cycles from carving both directions, a walled-off two-cell island) and
  checks the fuzz names the *specific* property each one violates. All six caught. One is
  informative beyond passing: carving both directions unconditionally also makes output
  seed-independent, so it trips two properties — the net overlaps rather than partitions.

### Fixed

- **`WebSocketOwnershipSmokeTest` was flaky — and the flake was in the assertion, not the
  server.** `anotherSubjectsSubscriptionIsRefusedWithAStompError` failed about one run in three
  (measured: 1 of 3, then 1 of 4 in isolation) during the full `verify`. Rather than re-running
  until green, the latch was instrumented to record what happened when it timed out; the answer
  was `ConnectionLostException: Connection closed`. The server refuses a non-owner by sending a
  STOMP ERROR frame **and then closing the socket**, and those two race — the test was waiting on
  one of two legitimate outcomes. Both mean refused. The latch now trips on the ERROR frame, a
  conversion failure reading it, or the transport dying, and reports which. Because accepting a
  bare close would weaken the check, both refusal tests now also assert the stronger property:
  the refused subscriber receives **no frames** while the owner's events are republished at it.
  Teeth confirmed by disabling the interceptor — both tests fail, and the new diagnostic reads
  "nothing at all was observed", which is the message the old assertion could not produce.
  Stable 5 of 5 afterwards.
- **The first `fuzzteeth.py` result was contaminated and is not the one reported above.** The
  harness was launched under a wrapper that hit a timeout; the wrapper was killed, the Python
  process survived orphaned and kept mutating, and a second copy started against the same file.
  Two interleaved runs printed a confident "6/6 caught" and left a sabotaged generator in the
  working tree — caught only because `git status` was checked before committing. The harness now
  holds a lock file, writes a pristine sidecar that the next run restores from, reverts after
  every mutation instead of once at the end, and reverts on SIGTERM; the 6/6 above was
  re-measured from a verified-clean tree. `mutants/README.md` records the trap and notes that
  the three older harnesses restore per mutation in a `finally` but still have no lock.

### Added

- **Maze fingerprint + generator classifier (ADR-007 idea 4) — name the algorithm from the
  shape alone.** `MazeFingerprint` reduces a maze to eight scale-invariant structural ratios
  (degree shares, directional bias, straight-run length, edge density), and
  `GeneratorClassifier` does nearest-centroid over signatures learned from the registered
  generators. `GET /api/v1/maze/{id}/fingerprint` returns the signature and the verdict; the UI
  adds **Identify generator**. Measured on held-out seeds it names the exact generator **58.9%
  of the time against 4.3% chance**, and the right *family* of algorithm **87.4%** of the time.
  The gap is the interesting part rather than a shortfall: the residual error is concentrated in
  algorithms that are equivalent by construction — Aldous-Broder and Wilson's both sample
  uniform spanning trees, so no statistic of a single maze can separate them, and counting that
  as an error would be scoring the classifier against mathematics. Most usefully, **confidence
  is calibrated**: verdicts at ≥0.25 confidence are ~89% accurate against ~45% below it, so a
  caller can trust the confident answers and read the unsure ones as "one of these two
  families". Disagreement with the recorded generator is surfaced rather than hidden — an eroded
  maze legitimately stops looking like its author (measured: dead-end ratio 0.106 → 0.042 after
  30 erosion ticks, and the verdict changes with it).
- **Complexity Lab (ADR-007 idea 2) — measure the algorithms instead of asserting them.**
  `GET /api/v1/complexity?generator=&metric=` runs a generator across a capped size sweep, fits
  the recorded work against candidate growth curves, and returns the winner with its exponent,
  R², and the measured points. The web UI plots it log-log, where a power law is a straight line
  whose slope *is* the exponent. Counters are fitted and wall-clock deliberately is not — timing
  measures the machine, while cell counters are deterministic per `(generator, size, seed)`, so
  any fit reproduces exactly. Two results worth the price of admission: **Prim's peak frontier
  measures O(√n)** (the frontier of a growing blob is its perimeter) while Kruskal's is linear,
  and **Aldous-Broder explores 266,830 cells to carve 9,216** — 29× overdraw, the cover-time
  cost of a uniform spanning tree. Sweeps never touch the maze cache or fire generation events.
- **Waypoint Tour mode (ADR-007 idea 1) — the exact TSP solver, made playable.** `GET
  /api/v1/maze/{id}/tour` places waypoints and returns the *provably optimal* order collecting
  them all: Held-Karp over the waypoint set plus the goal as a compulsory final stop. Collect
  them in the UI ("Waypoint hunt") and the finish line scores your walk against a number that is
  not an estimate — *"tour complete in 360 steps; the optimal route is 264 (136% of optimal)"*.
  Placement uses k-center farthest-first, so waypoints spread instead of clumping, which means
  the mode revives **two** dormant theory classes rather than one. Everything derives from the
  maze alone, so the daily challenge, per-maze leaderboards, ghosts and campaign stages all work
  in this mode without a line of change in any of them. Progress is observed server-side from
  real moves (the same event seam traffic uses) rather than accepted from the client, so the
  count that scores cannot be claimed.
- **ADR-007** (`docs/adr/ADR-007-theory-as-product.md`), from an audit with an uncomfortable
  finding: **six of nine `theory` classes had zero references from any user-facing module** —
  exact TSP, k-center placement, longest-simple-path, all-pairs distance oracles, and empirical
  complexity fitting, all built and tested and invisible. The ADR proposes ten ideas that close
  that gap, weighs three designs for the first, and records why waypoints must be server-owned
  (a comparison against "optimal" is meaningless if the client picks the instance).

### Fixed

- **The regression sweep hid rate-limit failures behind a `TypeError`.** Its maze-generating
  helper returned the error body on a non-200, so a 429 surfaced downstream as
  `TypeError: string indices must be integers` — a message that says nothing about the cause.
  It now raises with the status and body, and a sustained 429 explains that a full sweep exceeds
  the default 30-generations-per-minute budget and should run against the generous `test`
  profile. A helper that hides the real failure costs more than the failure.

- **The Complexity Lab's default metric was degenerate, and said so.** Measuring `cellsVisited`
  reports O(n) at R²=1.000 for all 23 generators — a spanning-tree generator carves every cell
  exactly once, so the metric *is* the cell count and the chart would have said the same thing
  about everyone. It is kept as a real invariant check (it catches a generator that skips or
  double-counts cells) and now labels itself as one, steering to `cellsExplored` and
  `maxFrontierSize` where generators actually differ.
- **A metric a generator never increments no longer poses as zero growth.** Fitting a curve
  through all zeros yields a NaN exponent that rounded to a confident-looking `0.0`; those cases
  now report `not reported` with an explanation instead of inventing a growth class.
- **An over-large waypoint count answered 500 instead of capping.** The count was clamped to
  `WaypointTour.MAX_WAYPOINTS` and *then* the goal was appended as the compulsory final stop,
  handing Held-Karp one stop more than it accepts. Caught by the mode's own bounds test.
- **A stale poll response could reinstate the maze you just navigated away from.** With STOMP
  unavailable, living and traffic mazes refresh by polling, and `refreshLivingMaze` assigned the
  fetched maze to `state.maze` *after* an await without re-checking that the maze was still
  current. Switch mazes during that window — click Daily, load a campaign stage, hit Generate —
  and the in-flight response put the old maze back: reproduced deterministically by delaying the
  old maze's fetch, leaving `state.maze` on the previous maze under a "Daily leaderboard"
  heading, where a session opened next would play a different maze than the one being scored.
  Every await in that function now drops its result if the player has moved on. Found by chasing
  a one-in-three flake in the new sweep rather than re-running until green.

### Changed

- **Added an end-to-end regression sweep (`sweep/`).** Every ADR-006 feature exercised against a
  running server — 14 API checks and 16 browser checks, each reporting evidence and continuing
  past failures. It exists because features were verified individually in the batch that built
  them, while later consolidation modified services those earlier features depend on
  (`LivingMazeService`, `TrafficService`, `MazeBreeder`); nothing had ever exercised all ten
  together. Current state: **14/14 and 16/16**, stable across repeated runs and with the
  multiplayer flag both on and off.
- **The per-session lock's isolation is now a tested guarantee.** A move's event listeners run
  while its session lock is held — deliberately, so listeners see moves in the order they were
  applied — and the listener chain has grown over this roadmap to include a STOMP send, traffic
  occupancy, the ghost recorder, and any installed plugin. That is only tolerable because the
  lock is *per session*, so a blocked listener can delay nobody but the player who triggered it.
  Changing `tryMove`'s `synchronized (s)` to `synchronized (this)` — one word, queueing every
  player in the server behind a single lock — broke exactly **one test out of 186**, and only
  after that test was written. New `SessionLockIsolationTest` pins both halves: a listener
  blocked on one session cannot stop another session moving, and moves on the *same* session
  still serialise. `GameSessionService` now records what the design costs, measured rather than
  asserted: a move is ~1.4µs with no listeners and ~1.3µs with traffic tracking (in-tree
  listeners are free within noise), while a listener that blocks for 60ms serialises that
  session's next ten moves into 579ms — so a listener needing slow or I/O-bound work should hand
  off to its own executor rather than borrowing the request thread. Added to the mutation
  harness, with a note on the anchoring trap below.
- **Mutation-tested the headline guarantees.** Six semantic breaks were injected one at a time
  — players able to walk through walls, BFS made LIFO so its paths stop being shortest,
  generators ignoring their seed, the leaderboard comparator inverted, rate limiting disabled,
  and half of all recorded search expansions dropped — each followed by a full test run and a
  byte-for-byte restore. **All six were caught**, so the suite has real teeth on the properties
  the project is sold on. (Harness at `mutants/run.py`; two apparent survivors turned out to be
  artifacts of running only the module that owned each file, which is worth stating rather than
  reporting as findings.)
- **Two core guarantees now defend themselves in core.** That module-locality point was a real
  gap, not just a harness quirk: `LeaderboardEntry`'s ordering and `SearchRecorder`'s fidelity
  live in `daedalus-core`, but every test of them lived in `daedalus-server`, so
  `mvn -pl daedalus-core test` stayed green with the leaderboard ranking worst-first and with
  half of every recorded search thrown away. A developer iterating on core got false confidence.
  New `LeaderboardEntryOrderingTest` and `SearchRecorderFidelityTest` close that, verified by
  re-running the mutations core-only — including one that drops a *single* expansion.
  `SearchRecorderFidelityTest` also documents a metric trap found while writing it:
  `cellsVisited` looks like the count to compare a recording against and disagrees with it by up
  to 17 on a 31×31 DFS solve; `cellsExplored` is the right one, and the true invariant
  (`cellsExplored - recorded ∈ {0, 1}`, measured over 324 solves) is what the arena's
  expansion-count verdict rests on.

### Fixed

- **`LivingMazeService` still compared a cell cost with `==` in one place.** The previous batch
  fixed the two sites SpotBugs flagged and left an identical third in `hotspotsOf`, where a
  weight a hair off `1.0` would be reported as a hotspot and shaded red. Now uses the same
  `WEIGHT_EPSILON` as its neighbours. Consistency rather than a live bug — traffic's decay snaps
  to exactly `1.0` — but it is the same defect class, one function away from the fix.
- **`TrafficService.quietTicks` was a `volatile int` being incremented.** The same
  read-modify-write pattern SpotBugs flagged on `LivingMazeService`'s tick counter, which it
  happened not to flag here. The fix goes the opposite way, because the field is genuinely
  different: it is touched only by the single-threaded ticker, so it is now a plain `int` with
  the confinement documented, rather than advertising cross-thread sharing that does not exist.
- **Campaign planning polluted the maze cache and lied to plugins.** Candidates were graded by
  generating them through `MazeGenerationService.generate`, which caches every maze and
  publishes `MazeGeneratedEvent`. A 6-stage campaign evaluates 54 candidates and serves 6, so
  **89% of them** were landing in the bounded maze cache — evicting mazes real users were
  playing, up to 2,400 junk entries at the default `max-campaigns` — while every plugin and
  STOMP subscriber was told 48 mazes had been generated that nobody could fetch. Candidates are
  now graded off the generator registry directly and only the winner enters the world;
  determinism makes that exact rather than approximate. Planning also got 58% faster as a side
  effect (411ms → 171ms), and the regression is pinned by a test, since nothing in the campaign
  response revealed it.
- **Dungeon crossbreeds came out with no dungeon left in them.** The connectivity repair ran
  Kruskal over every closed wall, which connects uncarved rock as eagerly as rooms: breeding two
  21×21 dungeon parents that were 49% and 50% rock produced children that were **0% rock on
  every seed** — connected, and unrecognisable as either parent. Repair now works on the
  habitable subgraph and tunnels a shortest corridor through rock only where leaving it would
  orphan a room; dungeon crossbreeds measure 46–50% rock and stay fully playable. Habitability
  is decided by each patch's donor parent rather than read off the stitched grid — the
  distinction matters, because a cell's four edges are inherited independently and the lottery
  can seal a cell both parents had carved, which the first version of this fix silently
  abandoned as rock (caught by spanning-tree parents, which contain no rock at all, producing
  children that did).
- **Campaign hazards silently 404'd.** The UI built hazard paths by interpolating the hazard
  name, but the `living` hazard is served by `POST /live` — every late-stage hazard failed. The
  hazard→path mapping is now explicit, with the mismatch noted.
- **Living and congested mazes changed in silence without STOMP.** Tick and pulse narration
  came only from broker frames, so with the CDN unreachable the polling fallback updated the
  maze with no explanation — worst exactly on late campaign stages, where hazards are the point.
  The polling path now reports walls opened and congestion changes.
- **`LivingMazeService.tick` incremented a `volatile int`.** `done++` is a read-modify-write and
  is not atomic even with a single writer thread; it is now an `AtomicInteger`. Pre-existing,
  surfaced by re-enabling SpotBugs (below).
- **Cell costs were compared with `==`.** `TrafficService` and `LivingMazeService.drift` tested
  computed doubles for exact equality to decide "did anything change?". Both now compare against
  a tolerance — the old code happened to work because a snap forces exactly `1.0`, which is one
  tuning change away from spinning on invisible deltas.
- **Verification gap owned:** batches 2–4 of this roadmap work were verified with
  `-Dspotbugs.skip`, so they never passed the project's own static-analysis gate. The full gate
  is green again, and the findings it had been hiding are fixed above (plus two documented
  `DMI_RANDOM_USED_ONLY_ONCE` false positives excluded with justification, per the project's
  convention of targeted exclusions over lowering the threshold).

- **Maze crossbreeding (ADR-006 idea #5).** `MazeBreeder` in core: two equal-sized parents
  produce a child by a patch-inheritance genome (3×3 blocks assigned to a parent by seeded
  coin flip, so offspring visibly wear both lineages — a Hilbert curve's discipline melting
  into a backtracker's rivers at the seams), then a seeded repair pass carves the minimum set
  of openings that makes every room mutually reachable while leaving genuine rock intact. That
  repair is load-bearing and proven so: disabling it leaves cells unreachable and fails the
  connectivity test immediately.
  `POST /api/v1/maze/breed?a=&b=&seed=` adopts the child as a first-class maze via the new
  `MazeGenerationService.adopt` (same metadata, cache entry, and `MazeGeneratedEvent` as a
  generated maze) — so a child can be solved, played, analyzed, brought to life, and bred
  again. Mismatched parents answer 400 with the dimensions. UI: **Crossbreed with previous**.
- **Spectator mode (ADR-006 idea #6).** `GET /api/v1/session/{id}` returns a read-only
  session snapshot, and the web UI gained a `#session=<id>` permalink: it loads the maze
  plus live positions and follows the same `/topic/session/{id}/player` frames the players
  produce (polling fallback when STOMP is unavailable). Spectators are genuinely read-only
  — keyboard and click input are refused client-side, verified in-browser (a spectator
  mashing arrow keys leaves `moveCount` at 0) — and owned sessions keep their existing
  per-destination STOMP authorization. Opening a session now logs its shareable link.
- **Chokepoint analytics (ADR-006 idea #9).** `GET /api/v1/maze/{id}/analysis` finally
  surfaces the `theory` module on the product surface: start↔goal min-cut (the actual
  chokepoint passages from `MazeFlow` — exactly 1 on every perfect maze, pinned at the
  HTTP seam), dead ends, and shortest-route length, computed on the maze's *current*
  snapshot. The web UI's **Analyze structure** button draws the cut passages as glowing
  violet gaps and dead ends as quiet dots, with a metrics banner — and re-analyzes on
  every living-maze tick, so you can watch a chokepoint dissolve as erosion braids it
  away. Shares the `mazeSolve` budget (comparable cost).
- **Ghost runs (ADR-006 idea #8).** Sessions now record the opening player's timed trail
  (`GameSession.TimedMove`, capped at `MAX_TRAIL`); on completion a new
  `SessionCompletedEvent` fires and `GhostService` keeps the best-scoring run per maze
  (bounded Caffeine store, `daedalus.ghost.*`) — the seat only changes hands on a
  strictly better score (teeth-proven: last-write-wins fails exactly the incumbent
  test). `GET /api/v1/maze/{id}/ghost` serves the recording; opening a session in the
  web UI summons it as a translucent racer replaying with its original pacing,
  hesitations included, and the finish line announces whether you beat it. Second
  players never pollute the recording.
- **Traffic simulation (ADR-006 idea #3).** `POST /api/v1/maze/{id}/traffic` closes the
  loop between play and routing: every cell a player or fog-of-war agent enters
  accumulates occupancy, a scheduled pulse applies it as cost (clamped at
  `daedalus.traffic.max-cost`) and decays every raised cost back toward uniform — so
  weight-aware solvers route around the crowd, and the shortcut reopens as it disperses.
  Both occupancy sources count identically (new `AgentSteppedEvent` alongside
  `PlayerMovedEvent`). Single-writer copy-on-write like the living ticker: moves only
  bump counters; the pulse thread copies, applies, swaps, and publishes a `TrafficFrame`
  (third frame shape on `/state`). Uniform grids are wrapped `WeightedMazeGrid` on
  enable; congestion mirrors into the response's `hotspots` list so cost shading just
  works. Bounded trackers (409 at capacity), self-retiring when fully decayed and quiet.
  UI: **Simulate traffic** button — pace back and forth and watch the floor heat up
  under your feet.
- **Solver arena (ADR-006 idea #2).** **Race solvers** in the web UI: two algorithms'
  REAL recorded expansion orders (the existing replay seam — observation, never
  reenactment) replay simultaneously at the same expansions-per-second, so the one that
  found the route with less work visibly finishes first; both routes then draw in lane
  colors and the verdict names the winner with the work ratio. Honest by construction:
  a solver that legitimately gives up loses by default, stated as such.
- **Per-maze leaderboards.** `GET /api/v1/leaderboard?maze={id}` — `LeaderboardEntry`
  gained a `mazeId` partition key (legacy null-maze entries stay global-only, pinned by
  `LeaderboardPartitionTest`, teeth-proven by disabling the filter). The daily
  challenge's board is now its own partition: the UI shows **Daily leaderboard** when
  today's maze is on screen, so a run on an easy 5×5 can never outrank daily runs.
  Redis backend keeps true per-maze sorted sets with a 48h TTL (time bounds key growth).
- **API errors now explain themselves in the web UI.** The server has always answered with
  RFC 7807 `ProblemDetail`, but the client's `api()` helper logged only the status line, so
  every failure looked identical. It now surfaces the server's `detail` — "400 … — parents
  must share dimensions: 15x15 vs 7x7" instead of a bare "400".
- **Fog-of-war agent API (ADR-006 idea #7).** The maze as a benchmark anything that
  speaks HTTP can compete on. `POST /api/v1/maze/{id}/agent` opens a *blind* walk: the
  agent sees only its position, the goal's coordinates, and which of the four directions
  are open from its current cell — the grid is never in any response (asserted on every
  response of the endpoint test's full walk). `POST /api/v1/agent/{id}/step?direction=…`
  moves; walking into a wall answers 400 *without consuming budget* (the view already told
  you the openings); `GET /api/v1/agent/{id}` re-polls visibility for free. Visibility is
  recomputed from the maze cache's **live** grid on every step and view, so a living maze
  erodes under the agent's feet mid-walk — the composition ADR-006 predicted, proven by
  `AgentWalkServiceTest` (swap an eroded snapshot in; the walled direction becomes open
  and walkable). Bounded everywhere: Caffeine agent store (`daedalus.agent.max-agents` /
  `idle-ttl`), per-walk step budget (default `4·rows·cols`, capped by `max-steps`), and a
  new `agentStep` rate budget (1200/min — a blind walk is hundreds of tiny requests by
  design). Verified end-to-end: a right-hand wall follower written against nothing but
  the HTTP surface solved the daily maze blind in 475 of its 1764 budgeted steps.
- **Daily maze (ADR-006 idea #4).** `GET /api/v1/maze/daily` — one shared challenge per
  UTC day. The seed derives from the date alone (epoch day × 64-bit golden ratio), so
  every instance, restart, and replica serves the *identical topology* with zero
  coordination or storage; teeth-proven by breaking the seed with `nanoTime()` and
  watching exactly the cross-instance determinism test fail. Lazily generated, self-
  pruning date map (no unbounded store), regenerates identically if the maze cache evicts
  it, and the literal `/maze/daily` path is pinned to outrank the `/maze/{id}` UUID
  template. The web UI grew a **Daily challenge** button; the daily maze is a first-class
  maze — solve it, bring it to life, or walk it blind.
- **Living mazes (ADR-006).** `POST /api/v1/maze/{id}/live` brings a maze to life:
  scheduled erosion ticks copy the cached grid, open a fraction of its dead-end walls
  (`Braider` reused as the erosion primitive), drift hotspot costs on weighted grids
  (clamped to the API's `[1, 1000]` domain), and atomically swap the new immutable
  snapshot into the maze cache — readers keep consistent old snapshots, no locking
  anywhere. Safe by construction: erosion only ever *opens* walls, so a live maze can
  never become unsolvable and a mid-run player can never be walled in. Deterministic:
  same maze + same seed erodes identically (default seed derives from the maze id).
  Bounded everywhere: ticks per run (`daedalus.living.max-ticks`), concurrent runs
  (`max-concurrent`, capacity answers 409), a new `mazeLive` per-caller rate budget
  (base/test/prod), and every run self-terminates — ticks exhausted, maze settled
  (nothing left to erode), or maze evicted (`replace` never resurrects). Each tick
  publishes `MazeMutatedEvent` (new plugin-api event), bridged as a `MutationFrame` on
  `/topic/maze/{id}/state`; the web UI's new **Bring to life** button re-fetches and
  quietly re-solves on every frame, so the drawn route visibly adapts as walls open —
  with a polling fallback at the server-reported tick interval when STOMP is absent.
  Chosen from a ten-idea deep audit recorded in ADR-006 (solver arena, traffic
  simulation, daily maze, fog-of-war agents, ghosts, chokepoint analytics, and more —
  now the roadmap). New core seam: `MazeGrid.copy()` / `WeightedMazeGrid.copy()`
  (weights preserved — teeth-proven: removing the override flattens weighted mazes to
  uniform cost and `LivingMazeServiceTest` fails on exactly that). Tests:
  `MazeGridCopyTest`, `LivingMazeServiceTest` (mutation, snapshot isolation,
  connectivity, determinism, settling, capacity, drift clamp),
  `LivingMazeEndpointTest`, `MazeWebSocketMutationBridgeTest`, and the templates test
  now pins `mazeLive`.
- **`application-prod.yml` now lists `sessionOpen` and `mazeLive` explicitly** with
  env-var-tunable limits and health indicators, matching their sibling budgets (they
  previously inherited base-yml defaults silently).

### Fixed

- **`WebSocketOwnershipSmokeTest` teardown race** — the refused-subscription tests
  provoke a server-side ERROR + close; `disconnect()` could race the socket into
  CLOSING and fail the test that had just passed. Teardown now tolerates that close.

### Changed

- **Server coverage ratchet raised 0.67 → 0.79** — measured 82.2% instruction (up from
  70.3% when pinned; the UI-sprint and audit tests), re-pinned ~3 below per the ratchet's
  own rule. Core (90.3%) and plugin-runtime (87.0%) barely moved; their pins stand.

### Fixed

- **Wiring audit (2026-07-29): the plugin subsystem's configuration was wired to nothing.**
  `PluginConfig` read `daedalus.plugin.dir` while every profile configured
  `daedalus.plugins.directory` — the configured plugin directory and the
  `DAEDALUS_PLUGIN_DIR` env var were silently ignored (plugins loaded from `./plugins`
  relative to the working directory). And `daedalus.plugins.scan-on-startup`, set in every
  profile and `false` under test, was read by nothing: startup scanning ran unconditionally,
  and the test profile only *appeared* to disable it. Both properties are wired now, pinned
  by `PluginSpiEndToEndTest` — the suite's first true SPI proof: a JAR packaged at test time,
  discovered from the configured directory by a booting server, its generator listed in the
  catalog, generating over HTTP, visible on the ops endpoint, and reported STARTED by
  `/api/v1/plugins`. Fails against the old property name.
- **The glyph projection lied about dungeons — at the source.** `toTileGrid()` marked every
  cell PASSAGE whether or not anything carved it, so rock rendered as floating floor specks
  in every JVM consumer (JavaFX desktop, ASCII art) — the web UI had patched it client-side,
  which was the tell the fix belonged in core (ADR-003 rule 1). Two honesty rules now:
  uncarved cells project as WALL, and a wall post surrounded by four open segments is room
  interior. Perfect-maze output is byte-identical (pinned), so spanning-tree consumers see
  no change; dungeons render honestly everywhere at once. `TileGridProjectionTest`.

### Fixed (earlier this day)

- **Back-end audit: every in-memory store the server accumulates into is now bounded.**
  Three had the same slow leak the rate-limiter buckets had before their Caffeine bound
  (BACKLOG, 2026-07-19): the **maze cache** (one full grid per generation, up to 43k/day
  inside the base rate limit, kept forever), the **session store** (never evicted, not even
  after completion), and the **in-memory leaderboard** (one entry per completed session,
  forever). Maze cache and sessions now sit in Caffeine caches (size + idle-TTL bounds,
  `daedalus.maze.cache.*` / `daedalus.session.*`); the leaderboard trims from the worst end
  past `daedalus.leaderboard.max-entries` (default 100 — `top(n)` caps at 100, so deeper
  retention was pure growth; the Redis backend keeps full history independently). Eviction
  rides the APIs' existing "unknown id" 404 paths, and the idle TTLs (2h) far outlive any
  game actually being played. `BoundedStoresTest` pins all three bounds.

### Added

- **Weighted mazes over the API** — the load-balancer thesis made demonstrable.
  `GenerateRequest.hotspots` raises per-cell traversal costs (validated `[1.0, 1000.0]`,
  ≤64 spots, out-of-bounds → 400 via a new `IllegalArgumentException` handler); the served
  grid becomes a `WeightedMazeGrid` and the response echoes the applied spots. Dijkstra,
  A\*, and Dial route around expensive cells wherever the topology offers a choice —
  `WeightedMazeApiTest` proves the detour by pricing Dijkstra off its own best route on a
  dungeon. The web UI grew hotspot controls and cost-shaded floors; combined with search
  replay, the detour happens on screen. This fires the last dormant ADR-004 trigger
  (weighted-floor shading), and honestly: the API creates the data now, not a constant.
  The circuit-breaker fallback preserves hotspots and rethrows caller errors instead of
  swallowing them into a silently different maze.
- **The prod profile boots under test for the first time.** `ProdProfileBootTest`
  assembles the full application under `prod` (env contract satisfied with test values,
  Redis off) — a prod-only wiring break now fails CI instead of the first production start.
  It also pins the prod actuator posture: health open, unexposed endpoints answer 401.
  `RateLimiterTemplatesTest` pins that every `@PerKeyRateLimit` budget has its yml instance.
- **Mazes over `curl`** — `GET /maze/{id}` content-negotiates `text/plain` into terminal
  ASCII art (core `AsciiMazeVisualizer` on the product surface), with `?solve=<solverId>`
  overlaying a route. Dungeons render honestly thanks to the projection fix.
- **ADR-005: single-instance posture.** The audit's design-level observation, written down:
  sessions, the maze cache, and the leaderboard's serving path are process-local on purpose,
  a second instance today would misbehave in specific enumerated ways, and the
  externalization path (Redis sessions with a distributed replacement for the tryMove lock,
  recipe-based maze regeneration, STOMP broker relay) is recorded now with the existing
  concurrency test named as its acceptance bar. Trigger: a real deployment wanting a second
  instance.
- **`docs/handoff/`** — the three LoadBalancerPro issues as paste-ready files, the Dependabot
  re-triage as a dry-run-first PowerShell script over `gh`, and Codecov activation steps:
  the full GitHub-side chore list reduced to a fifteen-minute pass.
- **`sessionOpen` rate-limit budget** on `POST /maze/{id}/session` and
  `POST /session/{id}/join` (60/minute/caller at the base config) — session creation feeds
  every bounded store downstream, so the inflow gets the same per-caller budget the other
  write endpoints already had.

## [1.1.0] — 2026-07-29

**The web UI grew up, and it caught a released bug on day one.** A visual audit
(headless-browser screenshots of all 23 generators through the real UI) drove
five rounds of front-end work — and the deepest find wasn't cosmetic.
Suite: 398 → **416 tests**.

### Fixed

- **Every REST-served dungeon was unsolvable (shipped in 1.0.0).**
  `MazeGenerationService` pinned start at `(0,0)` and goal at the far corner —
  carved cells for every spanning-tree generator, solid rock for a BSP dungeon.
  Every solver returned `success=false` and a play session opened inside a
  wall. Found by looking at the rendered output; the same corner assumption the
  07-19 audit removed from `theory`, one layer up. Fixed with
  `MazeMetrics.placeStartAndGoalAtExtremes` (largest-component-seeded,
  deterministic) — dungeons work, and every maze now gets the maximum-challenge
  diameter-endpoint placement the core recommends. `MazeGenerationStartGoalTest`
  fails against the pre-fix service.
- **Player names reached `innerHTML` unescaped** in the UI's log (and would
  have in the leaderboard) — stored XSS via a 64-char player name. Untrusted
  text now renders via `textContent`/escaping everywhere.

### Added

- **`MazeReplay` (ADR-004's deferred item, its trigger now fired).**
  `SearchRecorder` is the single interception point the design note called
  for: a thread-confined observer decorating the `Graph` that
  `AbstractMazeSolver.graphOf` hands out. Solvers run untouched — replay is
  observation, never simulation. `?replay=true` on the solve endpoint ships
  the expansion order (omitted otherwise: pre-replay clients see byte-identical
  JSON); off-seam solvers (IDA\*, wall follower) return empty expansions
  rather than a fake. The UI plays it in two acts: the real exploration front
  spreads cell by cell, then the route draws over it — BFS visibly floods,
  A\* visibly leans.
- **Web UI, five rounds.** Renderer rewrite (wide light corridors on thin dark
  walls; rock and interior wall-posts detected so dungeons read as rooms, not
  polka-dot noise); algorithm descriptor cards from the live catalog; solve
  stats readout; **compare-all-solvers** table (best path / fewest visits
  highlighted, hover previews each route, honest "gave up" rows); leaderboard
  panel over the existing API; click-to-move; illegal-move feedback; victory
  ring + session-complete banner; breadcrumb trails; maze permalinks
  (`#maze=<id>`); PNG export; `prefers-reduced-motion` support; graceful
  degradation when the STOMP CDN is unreachable (play still works via local
  position fallback).

### Decided

- **Weighted-floor shading stays unbuilt** — examined and the trigger has
  genuinely not fired: no REST-served maze carries cell weights (wall weights
  are consumed during Weighted-Prim's construction; `WeightedMazeGrid` is an
  embedding-only tool). Recorded in ADR-004; re-fires when the API can serve
  genuinely weighted mazes.

## [1.0.0] — 2026-07-28

**The audit's to-do lists are now empty.** One day, nine pushes: TESTING.md's
gap audit written and then fully executed (P1 through P3), the BACKLOG's last
hardening item and all four stretch goals shipped, and the engine audit's §2
recommendations either implemented or declined with reasons (ADR-004). The
suite grew 347 → **398 tests**, and — keeping the 07-19 through-line honest —
one of the new tests surfaced a live production bug (a check-then-act race in
`tryMove`) that was fixed before it shipped anywhere.

### Added

- **Example modules now build in CI.** `ci.yml` builds `loadbalancer-topology`,
  `dungeon-layout`, and `benchmark-harness` after the reactor `install` —
  before this, 17 test methods across those modules (including the one that
  caught the Hilbert forest) never executed on any push. (TESTING.md P1.)
- **`WebSocketSmokeTest`** — the realtime counterpart of `ApplicationSmokeTest`
  and the first test to construct a real `WebSocketStompClient`: connect
  without credentials in the advisory profile, valid-token accept, forged-token
  reject (proving the interceptor is *installed*, which the unit test cannot),
  and one broker frame round-trip per topic family. The simple broker sends no
  RECEIPTs, so tests republish their idempotent event until the first frame
  arrives — never `Thread.sleep`. (TESTING.md P1.)
- **Structural roster guards.** `PackageScan` (test-only, ~30 lines over
  `ClassLoader.getResources`) makes the solver and generator rosters
  completeness-checked against the package contents: a new concrete
  implementation left off the sweep now fails the build instead of silently
  shipping untested — the exact hazard that hid Trémaux. `DungeonGenerator`'s
  exclusion became visible code. (TESTING.md P2.)
- **JaCoCo ratchet.** `jacoco:check` fails `verify` below per-module
  instruction thresholds pinned 2–3 points under measured coverage — core
  0.87 (was 90.1%), plugin-runtime 0.84 (87.0%), server 0.67 (70.3%) — with
  desktop and plugin-api exempted as explicit `0.00` properties. Before this,
  a PR that deleted tests passed CI with a quietly shrinking badge.
  (TESTING.md P2.)
- **`PluginControllerTest` + `SpringPluginContextTest`** — the two zero-
  reference classes from the audit. The context test pins fail-fast
  `NoSuchBeanDefinitionException` for unavailable beans as plugin contract.
  (TESTING.md P2.)
- **Session ownership + STOMP per-destination authorization** — the second
  half of the BACKLOG auth item. Sessions opened by an authenticated request
  record the token's subject (`GameSession.owner()`, null for anonymous);
  `StompSubscriptionAuthorizationInterceptor` refuses SUBSCRIBE to an owned
  session's `/topic/session/{id}/player` unless the principal is the owner.
  Deliberately open: unowned sessions, unknown ids (no existence oracle), and
  the shared maze/plugin topics. Integration tests replayed against a build
  without the interceptor registered: exactly the two refusal tests fail.
- **Multiplayer sessions** behind `daedalus.session.multiplayer` (default off
  — off is byte-for-byte the pre-flag behavior). Per-player positions,
  `POST /session/{id}/join` (404 with the flag off; rejoin keeps position),
  `MoveRequest.player`, additive `player` on `PlayerMovedEvent`/`MoveFrame`.
  Any player reaching the goal completes the session exactly once.
- **Web UI** — one file of vanilla JS at `static/index.html`, served at `/`:
  generate/solve/play over REST, live frames over STOMP via SockJS, canvas
  rendering with path overlay and per-player markers. No build step, no npm;
  it exercises the public surfaces exactly as an external integrator would.
- **`ChaosGenerator`** (`id: chaos`, generator #23): splits the grid into 2–3
  bands, delegates each to a seeded random pick from four algorithms, joins
  bands with single doors — trees joined by single edges are a tree, so the
  spanning-tree contract holds and the roster guard forced it into the full
  connectivity/awkward-shape sweep automatically. Band doors are guaranteed
  chokepoints: deliberate stress texture for routing policies. (Audit §2.1.3.)
- **`MazeVisualizer` + `AsciiMazeVisualizer`** in `com.daedalus.visualize`,
  with `MazeGrid.toString()` now rendering ASCII art through the same
  `TileType` projection the REST surface ships. (Audit §2.1.1 + §2.3.)
- **`/actuator/algorithms`** — live registry observability (counts +
  descriptors, plugin contributions included); visible in dev, absent from
  prod's include list, JMX for free via actuator. (Audit §2.1.2.)
- **Codecov upload** in CI, guarded on the `CODECOV_TOKEN` secret — absent
  the secret, CI is unchanged. (BACKLOG, last piece of the original CI item.)
- **`TESTING.md`**, **ADR-003** (desktop testing policy: thin shell, logic
  moves to core, no TestFX, ratchet exemption as visible code), **ADR-004**
  (disposition of audit §2: Octile declined — the grid is 4-connected;
  parallel generation and `MazeReplay` deferred with named triggers).

### Fixed

- **`GameSessionService.tryMove` had a check-then-act race.** `ConcurrentHashMap`
  protects the map, not compound operations on one session: two racing moves
  could both validate against the same stale position (illegal transition),
  lose `moveCount` increments (`long++`), or double-complete a session — two
  leaderboard rows for one win. Now guarded by a per-session lock; the
  4-thread × 500-round hammer in `GameSessionServiceConcurrencyTest` fails
  against the pre-fix code on every run tried and passes deterministically
  after. Found because TESTING.md P3 said "test only if inspection finds
  check-then-act" — it did. This guard becomes ownership-critical now that
  sessions have owners.

### Changed

- **ADR-001 is Accepted** — items 1–5 and 7 done with measurements inline;
  item 6's remaining step (pasting the prepared LoadBalancerPro issues into
  their tracker) is a GitHub-side action, as are the Dependabot re-triage
  pass (commands recorded in BACKLOG.md) and the Codecov token.

## [1.0.0] — 2026-07-18 → 2026-07-19 (released with 1.0.0)

**Framework migration, three correctness fixes, and the test gaps that hid
them.** Repo is live at `RicheyWorks/Daedalus2`. Spring Boot moved 3.3.1 → 4.1.0
for four coordinates and one import; the graph seam finished absorbing the
solvers; and `theory` grew the pieces the ecosystem work needs.

The through-line of 07-19 is worth stating once, because three separate bugs
shared it: **the test fixtures were all the easy shape.** Every solver fixture
was a *perfect* maze — a spanning tree, where exactly one route exists between
any pair of cells, so a solver can be badly wrong and still look right. That hid
an inadmissible `LandmarkHeuristic` (A\* still returned the only path there was)
and a `TremauxSolver` missing one of Trémaux's three rules (it could not solve a
looped maze at all). Every generator fixture was a *square* grid, and every
`theory` caller assumed `(0, 0)` was part of the maze — false for a BSP dungeon,
whose corners are solid rock, which made `diameter` return 0 and put a generated
level's entrance and exit on the same square. Separately, every server test was
a *slice*, so a springdoc major version bump sailed through 267 green tests
without anything ever requesting `/v3/api-docs`.

Each fix therefore ships with the property test that would have caught it:
braided mazes across every solver, awkward grid shapes across every generator,
and one full-context smoke test that boots the real application. Where a
decision was measured rather than argued, the numbers are in the entry.

### Added

- **`MazeMetrics.largestComponentCell`, and the corner assumption it removes —
  found by building the ai-dungeon-master example.** Four call sites seeded
  themselves at `new Point(0, 0)`: `MazeMetrics.diameter`,
  `FacilityPlacement.kCenter` / `kCenterAcrossComponents`, and
  `LandmarkHeuristic.precompute` (twice). That is safe for a maze generator —
  every cell is carved, so the top-left is always in the single component — and
  silently wrong for anything sparser.

  A BSP dungeon has **solid rock in its corners**. Running the new
  `examples/dungeon-layout` against a 33² dungeon, the first output was:

  ```
  exact diameter   99 steps
  fast estimate     0 steps        <- measured a one-cell component
  rooms served      1 of 529 floor cells
  entrance (0,0)   boss (0,0)      <- same square of rock
  ```

  `diameter` seeded at an isolated rock cell, returned 0, and
  `placeStartAndGoalAtExtremes` therefore put the entrance and the boss room in
  the same place. `FacilityPlacement` collapsed the same way. After seeding from
  the largest connected component instead — one extra O(V + E) flood fill, so
  `diameter` stays linear — the same level reports diameter 99 (agreeing with
  `exactDiameter`), a hardest route 2.5× the direct one, and **529 of 529 floor
  cells served**.

  On a fully carved maze `largestComponentCell` returns `(0, 0)`, so nothing
  changes for existing callers. This is the same defect class as the Trémaux and
  ALT bugs: an assumption about graph shape that every maze fixture satisfies.

- **`FacilityPlacement.kCenterAcrossComponents` — k-center that survives a
  partitioned graph.** Found by auditing `theory` for a second shape assumption:
  not loops this time but **disconnection**, which the vision docs' own
  chaos-engineering pitch creates ("inject 15% node failure").

  Nothing in `theory` throws on a fragmented graph — `DistanceOracle` reports
  `UNREACHABLE`, `WaypointTour` reports `feasible=false`, `MazeFlow` correctly
  gives edge connectivity 0 across a cut. But `kCenter`'s greedy scores an
  unreachable cell as `-1` and compares with `>`, so it can never leave the
  component it started in. Measured on a 16×16 tree severed along one column
  (16 cut edges in a spanning tree ⇒ 17 components):

  | k | `kCenter` radius / served | `kCenterAcrossComponents` radius / served |
  |---|---|---|
  | 1 | 82 / 114 of 256 | 82 / 114 of 256 |
  | 2 | 44 / 114 | 82 / 126 |
  | 3 | 25 / 114 | 82 / 169 |
  | 8 | 12 / 114 | 82 / 212 |
  | 12 | **7** / 114 | 82 / 254 |

  Adding facilities drives the covering radius steadily down — 82 to 7, a
  placement that looks better and better — while coverage never moves off
  **114 of 256 cells**. Every extra facility refines service inside the one
  component the greedy can see; the other 142 cells are no closer to anything.
  Nothing lies; `servedCells` is in the result. But a quality metric that
  *improves* while more than half the graph stays unreachable is worth naming
  explicitly.

  **Both behaviours are kept, because both have a real consumer.** For a dungeon
  — placing treasure, save points or boss rooms — unreachable cells are solid
  rock, genuinely not places, and `kCenter` is correct. For a partitioned
  network, every fragment still holds real nodes, and `kCenterAcrossComponents`
  is. The new variant ranks unreachable cells as infinitely badly served, which
  is simply what the k-center objective says: the cost of a placement is the
  distance from the worst-served node, and for an unreachable node that is
  infinite. The 2-approximation still holds per component; across components no
  ratio is claimed, since with fewer facilities than components the objective is
  unbounded. On a connected grid the two are asserted to agree exactly, so the
  generalisation cannot disturb the ordinary case.

- **`MazeMetrics.exactDiameter` — the true diameter, for when the estimate
  isn't good enough.** Came out of auditing the `theory` package for the same
  defect class that bit the solvers: code that is only correct on a tree. The
  two prime suspects both turned out to be **already honest** —
  `MazeMetrics.diameter` documents itself as "exact for perfect (tree) mazes; a
  lower-bound heuristic if the maze has cycles", and `LongestPath` names its own
  NP-hardness and states outright that "the problem only becomes hard once the
  maze is braided". No bug to fix.

  What neither did was *quantify* the caveat, which is what a caller actually
  needs. Measured over 15 mazes at 20² per setting, double-BFS against the true
  diameter:

  | braid factor | mean error | worst error |
  |---|---|---|
  | 0.0 (perfect) | 0.0% | 0.0% |
  | 0.1 | 0.5% | 9.6% |
  | 0.3 | 0.6% | 8.4% |
  | 0.5 | 1.4% | **20.0%** |
  | 0.7 | 3.4% | 9.5% |
  | 1.0 | 2.5% | 13.6% |

  Tight on average, but **up to 20% low on an individual looped maze**. The
  two-sweep argument needs the farthest cell from an arbitrary source to be an
  endpoint of some diameter, and one cycle breaks that — a shortcut can land the
  first sweep somewhere lying on no diameter at all.

  That distinction is use-case dependent, so both are now available and the
  javadoc says which to reach for. Ranking generators or placing a start and
  goal far apart: keep the O(V + E) estimate — `placeStartAndGoalAtExtremes`
  deliberately still uses it. Capacity or latency planning over a braided
  topology, where the diameter *is* the worst-case route length: use
  `exactDiameter` and pay the O(V²).

  Tested against an independent brute-force implementation at four braid
  factors, plus a directional assertion that the fast estimate is **never an
  over-estimate** — that direction is the one that matters, since an
  over-estimate would understate worst-case route length in planning use.

- **Generator shape sweep — every generator against awkward grid shapes.**
  Third shape assumption audited today, after loops and disconnection: **grid
  shape itself**. Every generator fixture in the repo used a square grid, yet
  several generators carry an implicit assumption about dimensions — the
  space-filling curves want a power of two, `EllersGenerator` works a row at a
  time, `DungeonGenerator` needs room to split BSP leaves.

  `GeneratorConnectivityTest` already covered this for `HilbertCurveGenerator`
  specifically, since that is where the forest bug was found. It now sweeps all
  21 spanning-tree generators across eight shapes: `1×1`, `1×10`, `10×1`, `2×3`,
  `7×13` (both prime), `33×17`, `5×64` (extreme aspect ratio) and `20×20`
  (square but not a power of two). `DungeonGenerator` gets its own case at the
  same shapes, asserting the property that survives its contract — rock is meant
  to be unreachable, but the **carved** space must be a single connected level,
  or the layout contains rooms the player can never enter.

  **The audit found nothing**: 22 generators × 9 shapes, zero violations. Worth
  having anyway — it converts "the square-grid tests happen to pass" into an
  enforced property, and a generator that quietly dropped the last column of a
  lopsided grid, or divided by zero on a single row, would now fail loudly.

- **`examples/benchmark-harness` — timings for all 22 generators and 10
  solvers.** Standalone `main`, configurable sizes and seeds, writing
  `docs/benchmarks/benchmark-<date>.csv` alongside a console summary with a
  "vs fastest" column.

  The design decisions are mostly about **not producing misleading numbers**.
  Every CSV carries its JVM, OS, CPU count and heap in the header, because a
  timing without its machine is an anecdote rather than a measurement — during
  this project's own optimisation work, repeated runs of identical code varied
  by more than 2× on a loaded host. So the column worth acting on is relative
  cost within a single run. Timings are **medians**, not means, so one GC pause
  cannot move a published figure. And an algorithm that exceeds a 2-second
  budget is measured once and flagged `single-sample` instead of being warmed up
  and repeated five times — IDA\* costs roughly 300× BFS, and without that rule
  the sweep simply never finishes. It is deliberately outside the reactor and
  outside CI: a timing assertion on a shared runner fails for reasons that have
  nothing to do with the code. Its own tests assert structure — full algorithm
  coverage, well-formed rows, median-over-mean behaviour — and never a duration.

  Two self-inflicted bugs fixed during the build, both worth noting because both
  were silent. `exec:java` runs with the *module* as its working directory, so
  the original relative output path created a second, invisible
  `examples/benchmark-harness/docs/benchmarks/`; results now resolve to the
  repository root. And an XML comment cannot contain a double hyphen, so
  documenting the `--sizes` flag inside the pom's comment block made the pom
  unparseable.

- **`PluginSubsystemHealthIndicator` — plugin state as actuator detail, never
  as a verdict.** Reports `loadedPlugins`, `failedPlugins` and a `lastFailure`
  description, listening for `PluginFailedEvent` to keep the count.

  It is **deliberately incapable of reporting DOWN**, and that is the whole
  design. Boot folds component statuses into the aggregate, and the aggregate
  is what a load balancer or Kubernetes readiness probe acts on — so an
  indicator that condemned the instance because an *optional* plugin failed to
  boot would pull a healthy server out of rotation. That is not hypothetical:
  the stock Redis indicator did exactly that earlier the same day, dragging
  `/actuator/health` to 503 on an application working fine on its in-memory
  backend. The fix there was to stop it contributing; the lesson applied here
  is to not contribute a failure status at all. Failures surface as details for
  a human or dashboard, and the engine, REST API and solver registry keep
  serving — which is the point of loading plugins in isolation.

  Tested twice over, deliberately. A unit test hammers 250 failures across every
  `Phase` and asserts the status never budges; the smoke test then asserts the
  bean is actually **registered in the booted context**, because a unit test can
  only prove the indicator would answer UP if asked, not that Spring ever asks.
  That second assertion goes through the `ApplicationContext` rather than the
  health payload — component detail is hidden by default, and a test that
  tolerated its absence would have asserted nothing at all.

- **`SolverBraidedMazePropertyTest` — every solver, over mazes with loops.**
  Closes the gap that let two separate correctness bugs ship behind a green
  suite this month: **every solver fixture in the repository was a perfect
  maze**. A perfect maze is a spanning tree, which makes it a uniquely
  forgiving subject — exactly one route exists between any pair of cells, so a
  solver can be badly wrong and still look right. `LandmarkHeuristic` was
  inadmissible yet A* still returned the optimal path (there was only one to
  return); `TremauxSolver` could not solve a looped maze at all and no fixture
  contained a loop.

  The test sweeps 10 solvers × 4 generators × 5 seeds × 4 braid factors and
  asserts three properties: every returned path is a legal traversal (starts at
  the start, ends at the goal, never crosses a wall), every *complete* solver
  finds a route wherever BFS does, and every *optimal* solver still returns a
  shortest one once route choice actually exists. Runs in ~1.2 s.

  **The audit behind it found no further defects** — nine of ten solvers are
  correct at every braid factor, and the tenth, `wall-follower`, fails only
  where its own javadoc says it will (wall following is provably complete only
  on simply-connected mazes; it gives up via an iteration cap rather than
  hanging, and never returns a wrong path). Its exclusion is scoped to
  completeness alone — it is still held to the legality contract, and a separate
  case pins the guarantee it *does* make. Asserting that it fails on loops would
  forbid anyone from later improving it.

  Verified to have teeth rather than assumed: replaying the pre-fix
  `TremauxSolver` against this exact matrix fails **21 of 80** cases. There is
  also a tripwire asserting the solver list is complete, since silently omitting
  a new solver is precisely how Trémaux went untested.

- **`ApplicationSmokeTest` — the first test that boots the whole application.**
  Until now every server test was a slice (`@WebMvcTest` for controllers,
  `ApplicationContextRunner` for `RedisConfig`), which left a blind spot: no
  test ever assembled the full context, and nothing whatsoever exercised what
  the starters contribute for free. The springdoc **2.6.0 → 3.0.3** major bump
  went through a fully green 267-test suite without a single assertion touching
  `/v3/api-docs`. This adds one `@SpringBootTest(webEnvironment = RANDOM_PORT)`
  covering the joins: the context loads with the engine registries wired across
  the module boundary, `/actuator/health` is `UP`, `/v3/api-docs` serves a
  document whose `paths` cover the contract endpoints, and `/swagger-ui` is
  served. Path coverage is asserted as a *subset* (`containsAll`), not an exact
  count — adding an endpoint shouldn't fail the test, but silently losing one
  should.

  It paid for itself on the first run by failing on the 503 health bug recorded
  under **Fixed** below — a defect no slice test could have observed, and one
  that had been latent in the default profile.

  Implementation note for anyone extending it: this uses Spring Framework 7's
  `RestTestClient`, because **Boot 4 removed `TestRestTemplate`** from
  `spring-boot-test`. `WebTestClient` is the usual alternative but pulls in
  `spring-webflux`, which this module deliberately does not depend on.

- **`theory.ComplexityAnalyzer` — empirical complexity harness.** Revives the
  long-stubbed `com.daedalus.theory.ComplexityAnalyzer` (last seen in the v1.x
  portfolio) against the current engine API. Runs every registered generator
  at a fixed seed across configurable square sizes (default 32²/64²/128²),
  capturing the work each reports through `MazeStats` (cells visited, peak
  frontier, backtracks, path length) plus a wall-clock timing. `analyzeAll()`
  sweeps a `GeneratorRegistry` and returns a stably-sorted `Report` (a
  generator that throws is recorded as `success=false` rather than sinking the
  sweep). `Report.toCsv()` / `toJson()` emit only the deterministic,
  seed-stable columns — no wall-clock — so the report is a committable golden
  file for regression detection; timing stays on each `Measurement` for live
  inspection. Hand-rolled CSV/JSON, so daedalus-core gains no new dependency.
  Covered by 10 tests (determinism, no-stats and throwing-generator paths,
  a sweep over all 20 built-in generators, and the serialized shape). Clears
  the item from `BACKLOG.md` "New surfaces".
- **`theory.GrowthEstimator` — empirical Big-O labelling.** Turns a
  `ComplexityAnalyzer` sweep into a growth verdict per generator: fits each
  `metric(n)` against candidate classes (`O(1)` … `O(n^2)`) by
  least-squares-through-origin plus R² model selection, and reports the
  log-log power-law exponent alongside. Deterministic (rides the seed-stable
  counters); metrics that stay at zero or fewer than two distinct sizes return
  `UNKNOWN` rather than a fabricated class. Covered by 8 tests over synthetic
  known-growth data plus a live sweep. Implements idea **T1** from
  `AUDIT_CLRS_IDEAS_2026-07-18.md`.
- **`theory.MazeMetrics` — diameter & auto start/goal placement.** Double-BFS
  over the passage graph (CLRS Ch. 22) finds the maze's two farthest-apart
  cells — exact for perfect (tree) mazes, a lower-bound heuristic when the maze
  has cycles — and `placeStartAndGoalAtExtremes` drops the start and goal there
  for a maximal-challenge layout. Also exposes `farthestFrom` and
  `distancesFrom` (BFS distance field, `-1` for unreachable) for heat-maps.
  Deterministic (row-major tie-break on the farthest cell). Implements idea
  **T3** from the CLRS audit; 6 tests over hand-built mazes and a real
  perfect maze.
- **`theory.MazeFlow` — min-cut chokepoints & edge connectivity.** Edmonds-Karp
  max-flow (CLRS Ch. 26) over unit-capacity passages: the minimum start→goal
  cut is the fewest passages that would seal the goal off, and the cut edge set
  is exactly those bottleneck passages. Equivalently the start↔goal edge
  connectivity — `1` for a perfect maze (single route), `≥2` once braided.
  `minCutStartToGoal` / `edgeConnectivity` convenience; deterministic.
  Implements idea **X1** from the CLRS audit; 6 tests (perfect vs. braided,
  cut-edges-actually-disconnect, determinism).
- **`solver.solvers.DialSolver` — bucket-queue (Dial's) shortest path.** Dijkstra
  with a bucket priority queue keyed by integer distance (CLRS Ch. 24, and the
  bounded-key idea of Ch. 20): `O(C·V + E)` instead of `O((V + E) log V)`,
  near-linear on a grid. Reads the same `weightOf` hook as `DijkstraSolver` and
  returns an identical optimal path on uniform and integer-weighted mazes; it
  refuses fractional weights (bucketing is ill-defined — use Dijkstra there).
  Registered in `AlgorithmConfig` as solver id `dial`. Implements idea **S1**
  from the CLRS audit; 7 tests (matches Dijkstra on uniform + integer-weighted
  grids, detours around costly cells, rejects fractional weights, determinism).
- **`theory.LongestPath` — hardest route (longest simple path).** Budget-bounded
  DFS backtracking for the longest simple start→goal path: exact for small mazes,
  an honest lower bound (`exact=false`) when the budget is hit — never a wrong or
  non-simple path. The class javadoc documents why this is NP-hard (Hamiltonian
  path reduces to it, CLRS Ch. 34) and why no polynomial exact algorithm is
  attempted (Ch. 35). Trivial on perfect mazes (unique path), interesting once
  braided. `hardestRoute(grid)` convenience. Implements idea **T2** — the last of
  the CLRS-audit top five; 5 tests (braided longest > shortest, perfect == unique
  path, inexact-under-budget, determinism).
- **`engine.Braider` — dead-end braiding.** Seeded, deterministic post-process
  that opens one wall on a configurable fraction of dead ends, turning any
  generator's perfect maze (a spanning tree) into a braided one with real loops
  and route choice. This is the keystone for the structural metrics: min-cut
  (`MazeFlow`) is always 1 on a tree and longest-path (`LongestPath`) always
  equals shortest, so both only become meaningful once braided. Implements idea
  **G4**; 6 tests (full braid leaves zero dead ends, edge count exceeds `V-1` so
  cycles exist, exact fractional targeting, determinism, no-op at factor 0).
- **`solver.LandmarkHeuristic` — ALT (A\*, landmarks, triangle inequality).** BFS
  distance fields from a few greedily-spread landmarks give the bound
  `h(a,b) = max_L |d(L,b) - d(L,a)|`, admissible by the triangle inequality (the
  same potential-function reasoning as Johnson's reweighting, CLRS Ch. 25).
  Unlike Manhattan — which measures straight-line distance and is oblivious to
  walls — these distances are measured through the actual passages, so the bound
  reflects the detours a solver really has to make. Plugs straight into
  `AStarSolver`'s existing heuristic constructor. **Measured: ~55% fewer A\*
  expansions than Manhattan** (58,799 → 26,167 cells across 45 mazes at 25², 40²
  and 60²). Unit-cost grids only — hop counts would over-estimate on a
  `WeightedMazeGrid` and break optimality, which the javadoc states plainly.
  Implements idea **S2**; 5 tests (admissibility checked on *every* cell,
  optimality vs BFS, the aggregate expansion win, deterministic landmark choice).
- **`engine.generators.WeightedPrimsGenerator` — Prim's as an actual MST.**
  Weights every wall up front and always carves the cheapest frontier wall via a
  priority queue (CLRS Ch. 23), where the existing `PrimsGenerator` pulls a
  *uniformly random* frontier wall — a different algorithm with a different bias,
  so the two yield different mazes from the same seed. Registered as generator id
  `weighted-prims` (the built-in roster is now 21).
  **Correction to the original idea:** it proposed weight *variance* as a texture
  knob, but that cannot work — an MST depends only on the relative *order* of edge
  weights, and any strictly monotone reweighting (scaling, powers, variance
  changes) leaves the order, and hence the tree, identical. i.i.d. weights from
  any continuous distribution give the same family of mazes. What genuinely
  changes texture is breaking isotropy, so the knob shipped is a
  `horizontalBias` subtracted from east–west walls, which stretches the maze into
  long horizontal corridors. Implements idea **G1**; 5 tests (spanning-tree
  property, determinism, differs from random-frontier Prim's on the same seed,
  the bias measurably increases east–west passages, stats populated).
- **`theory.MazeFlow.vertexDisjointPaths` — route redundancy via Menger.** Counts
  the routes between two cells that share no intermediate cell, using the
  vertex-splitting reduction to max flow (CLRS Ch. 26): every cell becomes
  `v_in → v_out` joined by a capacity-1 arc, so no single cell can carry two
  routes. By Menger's theorem that count is also the fewest intermediate cells
  you'd have to block to sever the two. It is always `<=` the edge connectivity
  from X1 — blocking cells is at least as powerful as blocking passages — and is
  exactly `1` on any perfect maze, since a tree has one route; `Braider` is what
  creates genuine alternatives. Implements idea **X2**; 8 tests, including the
  vertex `<=` edge invariant checked across 15 braided mazes.
- **`theory.WaypointTour` — optimal "collect all the coins" routes.** Shortest
  route from a start cell visiting every waypoint, solved exactly by the
  Held–Karp dynamic program (CLRS Ch. 15's subset DP applied to the TSP-path
  variant of Ch. 34). Visiting waypoints nearest-first is *not* optimal — picking
  the order is the hard part — so the DP keys on *(set already collected, cell
  you're standing on)* instead of the full ordering, trading factorial time for
  `O(2^k · k²)`. That's exponential in the waypoint count but independent of maze
  size, which is exactly the right shape for a game mode: a handful of coins in a
  large maze. Waypoints are capped at 16 with a clear error beyond that, and the
  chosen order is stitched back into a real cell path. Also adds
  `MazeMetrics.shortestPath`. Implements idea **T5**; 7 tests, the key one
  cross-checking the DP against brute-force enumeration of every visiting order.
- **`util.TileGridCodec` — run-length wire encoding for tile grids.** Encodes the
  rendered `char[][]` the REST/STOMP surfaces ship as `<rows>x<cols>:` plus
  row-major runs. Since no `TileType` glyph is a digit, a count-prefixed run
  parses with no separators or escapes, and a run of one is written as the bare
  glyph so the encoding can never expand the payload. Runs cross row boundaries,
  which is where the border and corridor stretches collapse.
  **Measured saving: 36–38%** (encoded is 62–64% of raw, stable from 16² to
  128²). Implements idea **X3**; 7 tests covering round-trip on real mazes, every
  glyph, malformed input and ragged grids.
  **Worth knowing before using it:** a rendered maze alternates cell/wall at
  nearly every column, which is close to the worst case for run-length coding, so
  36% is about all it can give. The far bigger win is not compressing this grid
  but *not sending it* — the rendered grid is `(2r+1) x (2c+1)`, roughly four
  times the cell count, while the maze itself is two wall bits per cell. Measured
  side by side at 64² and 128², sending cell bits is **~16× smaller** than the
  rendered glyph grid. This codec is the drop-in that needs no API change; the
  16× needs a client-side renderer.
- **`examples/loadbalancer-topology` — the integration made runnable (ADR-001, item 5).**
  A standalone module (not a reactor child, matching `examples/biome-plugin`) that
  demonstrates the three LoadBalancerPro integrations needing no changes to either
  project: generate a topology, measure its capacity with min-cut, and place replicas with
  k-center — plus latency-aware routing done the corrected way, with load in the edge cost
  and an admissible heuristic. A fifth section builds a spine-and-leaf `CsrGraph`, a
  degree-3 topology no `MazeGrid` could express, to show the seam taking a real network
  shape. Seven tests pin the claims, because an example that only prints is documentation
  that can rot.
  **It also surfaced a defect the vision documents miss:** `HilbertCurveGenerator`'s raw
  output is **not connected**. At 32² the edge connectivity from `(0,0)` to `(31,31)`
  measures **0** — no route exists — with 396 dead ends. Since both the vision document and
  the integration guide recommend Hilbert as *the* topology generator and then route across
  it with A\*, anyone following that advice gets an empty path back, silently, in the same
  way the heuristic bug was silent. Measured across braid factors: `0.0` → connectivity 0,
  `0.6` → 1, `1.0` → 2. The example therefore braids fully and says why, and a test pins
  the raw generator's disconnectedness so the finding cannot quietly regress.
- **`theory.FacilityPlacement` — k-center placement (ADR-001 appendix, item 1).** Where to
  put `k` edge caches / replicas / rack anchors so the worst-served node is as close as
  possible, by the farthest-first greedy (CLRS Ch. 35): take any node, then repeatedly add
  the node currently worst served. That is a **2-approximation**, and since no polynomial
  algorithm can guarantee better than 2 unless P = NP (Ch. 34), the simple algorithm also
  carries the best available guarantee. The greedy step turns out to be
  `MazeMetrics.farthestFrom` generalised to a set — the same rule `LandmarkHeuristic`
  already uses to spread landmarks, which is not a coincidence: both want points far from
  each other and from everything else.
  Also exposes `coveringRadius(grid, facilities)` for scoring a placement you already have.
  Unreachable cells (a dungeon's solid rock) are simply unserved rather than distorting the
  radius. 8 tests, the load-bearing one **verifying the 2-approximation against brute-force
  enumeration of every k-subset** on small mazes — the guarantee is checked, not asserted.
- **`com.daedalus.graph` — the graph seam (ADR-001, phase 1).** `Graph` is the abstraction
  that lets Daedalus route over any topology rather than only a rectangular maze:
  dense integer node ids, and adjacency delivered into a **caller-owned buffer**
  (`neighbors(node, int[] out)`) so a search loop allocates nothing. Two
  implementations ship: `MazeGraph`, a zero-cost **live view** over `MazeGrid` that
  reads wall flags directly, and `CsrGraph`, a compressed-sparse-row snapshot built
  from caller-supplied edges — the entry point for a service mesh or rack layout that
  was never a maze, with in-place `setEdgeWeight` so live latency/load can move
  without rebuilding the structure.
  `BfsSolver` is retargeted onto it as the proving spike, and the seam paid for
  itself immediately: **2.39–2.75× faster** (58–64% less time over 12 mazes at 80²)
  against a faithful copy of the previous implementation. That beats even D2's
  1.42–1.72×, because BFS shed the per-node `ArrayList` from `openNeighbors` on top of
  the hashing. Every existing test passed **unchanged**, including the cross-solver
  agreement checks that compare bidirectional and A\* against BFS — which is the
  evidence the retarget is behaviour-preserving.
  **Phase 2** moved `DijkstraSolver` and `AStarSolver` onto the same seam, removing the
  last per-expansion `List` from their loops. Benchmarking that change was
  **inconclusive** — 1.44×, 1.21×, then 0.86× across reps, i.e. inside the noise — and it
  is recorded as such rather than dressed up. The reason is that D2 already took the big
  win here by removing the hash collections; what remains is priority-queue work plus the
  `Point` that `MazeGraph.edgeWeight` still allocates, so the list was a small share of
  the total. **This phase is justified by architecture, not performance**: one adjacency
  contract across every solver, and the ability to run them on a topology that was never a
  maze. A node-indexed weight accessor would remove the last allocation and is the obvious
  next measurement.
  **`DialSolver`** followed, and is worth recording as a worked example of predicting
  wrong. It was the last `HashMap<Point,…>` solver, so a BFS-sized win was predicted. The
  first retarget delivered **1.14× / 1.28× / 1.00×** — barely anything. The cause was in
  the new code, not the old: buckets were still a `Map<Integer, IntBucket>`, so every
  relaxation did a `computeIfAbsent` on a **boxed distance key** and put hashing straight
  back on the hottest path — the exact cost the seam exists to remove. Indexing buckets by
  distance directly (a plain `IntBucket[]`, grown on demand) delivered
  **1.94× / 2.36× / 1.99×**, the win originally predicted. Behaviour is unchanged
  throughout: `dial` still returns paths identical to `dijkstra`, and still rejects
  fractional weights.
  **`theory.MazeMetrics`** moved onto the seam last, chosen by measurement rather than by
  working down the solver list: it is the one class on everything's hot path, because
  `DistanceOracle.precompute` runs a BFS *per cell* and `LandmarkHeuristic` and
  `WaypointTour` sit on it too. Removing the per-cell neighbour list there compounds
  across all of them — `DistanceOracle.precompute` on a 48² maze (2,304 BFS runs) went
  from ~239 ms to ~146 ms, a steady **1.59–1.73×**. The remaining six solvers all still
  use `HashMap`/`HashSet` and are candidates on the same evidence, but each should be
  measured rather than assumed, since Dijkstra and A\* showed the seam pays nothing where
  hashing was already gone.
  **`theory.MazeFlow`** followed, picked by the same rule and giving the largest win yet:
  **2.46× / 3.21× / 5.59×** on eight braided 64² mazes. It was the heaviest hasher left — a
  `Map<Long, Integer>` residual table keyed by packed `(from, to)` pairs, boxing a `Long` on
  every residual lookup, and max-flow performs one per edge per BFS. That is now a
  compressed-sparse-row residual network (`offsets` / `targets` / `twin` / `capacity` arrays)
  with an `int[]` BFS queue, so the inner loop boxes nothing. Cut sizes and cut edges are
  unchanged — both `MazeFlow` suites pass untouched, including the test that verifies removing
  the reported edges genuinely severs source from sink. This matters beyond microbenchmarks:
  min-cut is what capacity analysis calls in the LoadBalancer example, so it is on the
  ecosystem's hot path rather than the maze game's.
  `vertexDisjointPaths` followed in the same file, replacing its
  `List<List<Integer>>` adjacency and `Map<Long, Integer>` residual with an arc-indexed
  split graph — every arc paired with a zero-capacity reverse twin, grouped by tail, which
  is the textbook max-flow representation in flat arrays. **2.02× / 3.04× / 3.74×**, with
  the vertex `<=` edge invariant and every other assertion unchanged. `MazeFlow` now holds
  no hash structures at all, and the dead `key()`, list-based `addArc` and
  `findAugmentingPath` helpers are gone with their imports.
- **`engine.generators.DungeonGenerator` — rooms and corridors (C3).** Binary
  space partitioning: split the grid recursively, carve a room in every leaf,
  then join sibling regions with L-shaped corridors on the way back up. The
  recursion order is what guarantees connectivity — each subtree is joined to its
  sibling exactly once. Registered as generator id `dungeon` (the roster is now
  22).
  This is the first generator here that is **deliberately not a perfect maze**,
  and it inverts all three of the usual properties: rooms are open areas (interior
  cells open on all four sides), rooms are dense blocks of cycles so routes are
  never unique, and the rock between rooms is never carved and stays unreachable.
  Callers that assume full reachability must not use it — the `MazeGenerator`
  contract allows this explicitly ("unless their theoretical contract says
  otherwise"). A pleasant side effect: the structural metrics that need `Braider`
  to become interesting on a maze — `MazeFlow`'s min-cut, `LongestPath` — are
  non-trivial here for free. 8 tests covering room openness (measured against a
  perfect maze of the same size), loop presence, unreachable rock, connectivity
  of everything carved, and statelessness across reuse.
- **`theory.DistanceOracle` — all-pairs distances, O(1) queries.** BFS from every
  cell tabulated into a flat `short[]`, so any later "how far is A from B" — a
  leaderboard scoring against the optimal route, arbitrary start/goal queries,
  ranking cells by eccentricity — is a single array read (CLRS Ch. 25, unweighted
  special case). Also exposes `eccentricity` and `diameter`.
  The binding constraint is memory, not time: the table is `V²`, and `V` is
  itself quadratic in the maze's edge length, so 32² needs 2 MB, 64² needs 32 MB
  and 128² would need 512 MB. Rather than quietly exhaust the heap it caps at
  4,096 cells and throws with a pointer to `MazeMetrics.distancesFrom` (one BFS,
  one row of this table) for larger mazes. Implements idea **S4**; 8 tests,
  including an exhaustive every-pair check against BFS and a diameter
  cross-validation against `MazeMetrics`, which derives the same number by
  double-BFS instead of exhaustive scan.

### Changed

- **ADR-002 — CSRBT `RankedSet` behind `TailLatencyPowerOfTwoStrategy`:
  evaluated and declined** (ADR-001 item 7). Measured against the real classes
  from both sibling projects — `ServerStateVector` / `ServerScoreCalculator`
  from LoadBalancerPro 2.4.2, `OrderedSet` / `RedBlackStrategy` from csrbt-core
  0.1.0 — over a simulated 64-server fleet. Harness committed at
  `docs/evaluations/CsrbtRoutingEval.java`.

  Reading the strategy first changed the question. It samples exactly **two**
  servers at random and takes the better one; its only O(n) step is a boolean
  health filter, and `ServerStateVector` already carries per-server `p95`/`p99`.
  **There is no order statistic in it to accelerate**, so adopting a ranked
  structure necessarily means changing the *policy* — to "gate to the best q%
  of the fleet, then power-of-two inside that pool".

  The decisive variable turned out to be **how stale the balancer's view is**,
  which is also the entire reason power-of-two-choices exists. Benchmarking
  against a perfectly fresh view measures a system nobody runs:

  | view refreshed every 25 requests | mean ms | p99 ms | max in-flight | ns/decision |
  |---|---|---|---|---|
  | **uniform po2 (shipped)** | **6.03** | **19.13** | **5** | **48** |
  | greedy least-score | 33.77 | 52.77 | 19 | 200 |
  | RankedSet-gated po2 | 7.86 | 22.32 | 13 | 5 870 |
  | quickselect-gated po2 | 7.78 | 21.52 | 10 | 417 |

  Three findings, any one sufficient to decline. The gating policy **herds** —
  29% worse mean, 17% worse p99, double the peak in-flight — because
  concentrating the sample pool on whatever looked best in the last snapshot
  sends every request to the same place; greedy, the limiting case, is 9× worse.
  Where gating *did* win (fresh view only), an O(n) quickselect matched the tree
  at **1/9th the cost**, so the gain came from the policy, not the structure.
  And `RoutingStrategy.choose(List<ServerStateVector>)` hands over a **fresh
  list per call**, so an order-statistic tree — whose whole advantage is
  incremental maintenance — must be rebuilt every time: **5.8–9.1 µs per
  decision against 46–185 ns**, 30–125× more expensive, on the per-request hot
  path.

  That last point is a fact about the call shape rather than about CSRBT, and it
  produced a concrete upstream request (ADR-001 item 6, request 3): give
  `RoutingStrategy` an optional stateful form, since the current signature
  obliges every strategy to be stateless and O(n) per decision.

- **`LongestPath` moved onto the graph seam — the last hot hashed structure in
  the engine (ADR-001 item 3).** Its backtracking DFS held membership in a
  `HashSet<Point>` and the path in an `ArrayDeque<Point>`, probed and mutated
  once per neighbour of every visited node, up to the two-million-visit default
  budget per call. Now a `boolean[]` and an `int[]` stack over dense node ids.
  **Measured 3.56–3.76× faster** on braided 14² mazes — the case that is
  actually hard, since a perfect maze has exactly one simple path and no search
  to do. Equivalence checked over **192 A/B cases** across four generators, four
  braid factors and two sizes: identical paths throughout.

  One detail that would have been a silent corruption: the recursion needs **one
  adjacency buffer per depth level**, not a shared one. Every frame holds a live
  neighbour iteration, so a child call reusing the parent's buffer would
  overwrite the list the parent is still walking. Depth is bounded by the cell
  count — a *simple* path cannot revisit a cell — so `V` buffers is an exact
  bound rather than a guess.

  `WaypointTour`'s remaining `Set<Point>` was deliberately left alone: it
  de-duplicates at most 16 waypoints once, and is not on any hot path.

- **`DeadEndFillingSolver` moved onto the graph seam — the last solver where it
  pays (ADR-001 item 3).** Both phases retargeted: the cascade's `HashSet` of
  filled cells and `ArrayDeque` frontier, and phase two's BFS maps.
  **Measured 1.60–2.75× faster** over 12 mazes at 80².

  One deliberate simplification. The old cascade could enqueue the same cell
  several times and discarded the duplicates at poll time, which meant no exact
  capacity bound existed. Enqueueing each cell at most once is equivalent — a
  cell is filled the first time it is polled and never unfilled, so later
  enqueues were always no-ops — and it makes V an exact bound rather than a
  guess. That is the kind of "obviously equivalent" reasoning worth distrusting,
  so it was checked: **1024 A/B cases identical** on path, `cellsVisited` and
  `cellsExplored`.

  The nested neighbour scan needs **two** adjacency buffers, not one — the inner
  loop counting a neighbour's surviving exits would otherwise clobber the outer
  loop's contents mid-scan. Sharing one buffer compiles and passes casually
  written tests; it silently corrupts the cascade.

- **`BidirectionalSolver` and `DfsSolver` moved onto the graph seam (ADR-001
  item 3).** These were the two largest remaining holdouts — bidirectional
  carried **seven** hashed-`Point` collections (two parent maps, two seen sets,
  two `ArrayDeque` frontiers, plus a `LinkedList` for reconstruction), DFS
  carried three. Both now run on `MazeGraph` adjacency into a reused buffer,
  with `int[]` parent arrays, `boolean[]` seen flags and `int[]` frontier
  storage sized at exactly V (each node is enqueued at most once, so that bound
  is exact rather than a guess).

  | | before | after | speedup |
  |---|---|---|---|
  | `bidirectional` | 11.97–13.14 ms | 4.88–5.86 ms | **2.12–2.69×** |
  | `dfs` | 10.71–11.20 ms | 3.46–3.51 ms | **3.09–3.19×** |

  Measured over 12 mazes at 80², mean of 5 reps after warm-up. Both land in the
  band BFS got (2.39–2.75×), which is the fourth consecutive confirmation of the
  rule this phase established: **the seam pays exactly where hashing survived,
  and nowhere else.** Every solver that had already been moved onto cell-id
  arrays showed no further gain; every one still hashing `Point` gained 2–3×.

  Equivalence was verified rather than argued: **1024 A/B cases each**, across
  four generators × eight seeds × four braid factors × two sizes × four random
  start/goal pairs, comparing path *and* stats (`cellsExplored`, `cellsVisited`)
  against a verbatim copy of the previous implementation. All 2048 identical.
  Random start/goal pairs matter for bidirectional specifically — its
  smaller-frontier balancing rule is only exercised when the two searches are
  unbalanced, which corner-to-corner runs never do.

- **`TremauxSolver` moved onto the graph seam; edge marks are a flat `byte[]`
  (ADR-001 item 3).** Diagnosed before being touched, which changed the fix.
  Trémaux was among the slowest solvers, and the intuitive read — "it's a walk,
  walks are long" — is wrong: it takes **1.04 × V steps against BFS's
  1.00 × V**, essentially identical work. The whole gap was **cost per step**,
  so no algorithmic tuning would have moved it.

  The culprit was the mark table. Marks lived in a `Map<Edge, Integer>` where
  `Edge` was a record wrapping two `Point` records, so every lookup allocated a
  composite key — and lookups ran once per neighbour **and again inside a
  `Comparator` during a per-step `sort`**, so each step allocated edge keys
  O(d log d) times plus a comparator, a neighbour `List`, and boxed `Integer`
  values, all to choose between at most four options.

  Marks are now `byte[V * 4]` addressed by `cell * 4 + direction`, with both
  halves of a passage incremented together so the pair acts as one undirected
  mark. Neighbours come from `MazeGraph` into a reused buffer, and the sort is
  replaced by a linear min-scan. **Measured 3.3–6.8× faster** over 12 mazes at
  80², which puts Trémaux at roughly BFS's cost (0.8–1.45×) instead of several
  times it. Selection is provably equivalent — `MazeGraph` yields neighbours in
  the same `Direction` order and the old sort was *stable*, so "first minimum
  wins" reproduces the previous choice exactly.

- **`MazeGrid.weightOf(Point)` is now `final`** — closing a silent-failure hazard
  the coordinate-indexed accessor introduced. Once the graph seam started asking
  for weights by `(row, col)`, a subclass overriding the older `Point` form
  would still compile but be **bypassed entirely**: its costs would vanish and
  A\* would quietly optimise the wrong thing. Sealing the delegate turns that
  into a compile error naming the method to override instead. Nothing in the
  repo was affected — only `WeightedMazeGrid` overrode it, and that had already
  moved — but `daedalus-plugin-runtime` loads third-party jars that may subclass
  `MazeGrid`, so the failure mode was reachable from outside.

- **`MazeGrid.weightOf(int row, int col)` — coordinate-indexed entry cost.**
  The graph seam addresses nodes by dense integer id, so
  `MazeGraph.edgeWeight(int, int)` was building a `Point` on every edge
  relaxation purely to hand it to `weightOf(Point)`, which immediately unwrapped
  it again — one allocation per relaxation, in the hottest loop the engine has.
  Subclasses now override the `(row, col)` form and `weightOf(Point)` delegates
  to it, so there is a single implementation point and both forms cannot drift.
  This is ADR-001 item 4's "add `EdgeWeightedGraph`" resolved without adding a
  type: `Graph.edgeWeight` was already node-indexed, so a parallel interface
  would have been ceremony around a one-method change.

- **Spring Boot 3.3.1 → 4.1.0 (with Framework 7).** The server, plugin runtime
  and desktop modules now build on the Boot 4 line. Four coordinate changes and
  a single import were the entire migration:

  | | before | after |
  |---|---|---|
  | `spring-boot-starter-parent` | 3.3.1 | **4.1.0** |
  | `resilience4j.version` | 2.2.0 | **2.4.0** |
  | resilience4j artifact | `resilience4j-spring-boot3` | **`resilience4j-spring-boot4`** |
  | `springdoc.version` | 2.6.0 | **3.0.3** |

  The lone source change is in `RedisConfigConditionalTest`: Boot 4 split the
  monolithic `spring-boot-autoconfigure` jar into per-technology modules, which
  both moved *and* renamed the class —
  `org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration`
  became `org.springframework.boot.data.redis.autoconfigure.DataRedisAutoConfiguration`
  (now in `spring-boot-data-redis`). Nothing in `src/main` needed touching in
  any module.

  **Verified, not assumed.** The migration was first run in a throwaway copy of
  the tree. The initial `mvn test` reported **28 errors** — a mix of
  `NoSuchMethodError` on `MockHttpServletRequestBuilder.contentType(String)` and
  `IncompatibleClassChangeError: HttpHeaders does not implement MultiValueMap`.
  Every one of those was an artifact of Maven's *incremental* compilation
  leaving Boot 3 test bytecode on disk to run against Boot 4 jars; return types
  and interface sets are part of a JVM method signature, so stale classes fail
  exactly this way. A `clean` rebuild reduced 28 errors to **one** — the Redis
  import above. The lesson generalises: when a dependency bump produces
  `NoSuchMethodError` for a method that plainly still exists in source, rebuild
  clean before reading it as an API break.

  After the fix, the full reactor is green on Boot 4: **267 tests, 0 failures,
  0 errors, 0 Checkstyle violations, 0 SpotBugs findings** (core 183,
  plugin-api 7, plugin-runtime 16, server 57, desktop 4). The per-key rate
  limiter and its 429 path pass unchanged, so `RequestNotPermitted` handling
  survived both the Boot and the Resilience4j bump.

  **springdoc's major bump was checked at runtime, not by test.** Nothing in
  the suite exercises `/v3/api-docs`, so the packaged jar was booted and probed
  directly: it starts clean, `/v3/api-docs` returns **HTTP 200** with all **10**
  paths documented, and `/swagger-ui/index.html` returns 200. One behavioural
  change worth knowing about downstream: springdoc 3 emits **OpenAPI 3.1.0**
  where 2.x emitted 3.0.x. Nothing in this repo consumes the spec —
  `Code/daedalus-api-dtos.ts` is hand-written against the Java records rather
  than generated — but external clients running codegen against the published
  document will see the version change.

- **Solvers index state by cell id instead of hashing `Point` (D2).**
  `DijkstraSolver` and `AStarSolver` now hold distance / parent / closed state in
  flat arrays addressed through the new `solver.GridIndex` (`row * cols + col`),
  replacing `HashMap<Point,…>` / `HashSet<Point>`. **Measured 1.42–1.72× faster**
  (29–42% less time) over 12 mazes at 80², A/B'd against a faithful copy of the
  previous implementation with identical stats bookkeeping. Behaviour is
  unchanged by construction — queue ordering, neighbour iteration and
  tie-breaking are all identical — and the full suite passes untouched, including
  the assertions that `dial` equals `dijkstra`, that weighted routing picks exact
  known paths, and that A\* matches BFS. This is the item the D3 benchmark
  redirected effort toward.

### Fixed

- **`TremauxSolver` was missing Trémaux's third rule and could not solve mazes
  with loops.** The implementation carried only "never enter a twice-marked
  passage" and "prefer the least-marked passage". The rule it lacked — **on
  re-entering a junction you have already stood on, having arrived along a
  previously unmarked passage, turn straight back** — is the one that retires
  that passage and guarantees a retreat route stays open. Without it the walk
  strands itself: it reaches a cell whose every passage is already twice-marked
  while the goal sits unvisited elsewhere. The old code read that state as
  "unreachable" and returned an empty path, under a comment asserting it was
  *"impossible on connected maze"*.

  It was not impossible. Measured at 20² over 40 seeds per setting:

  | braid factor | mazes failed (old) | mazes failed (fixed) |
  |---|---|---|
  | 0.0 (perfect) | 0 / 40 | 0 / 40 |
  | 0.25 | **19 / 40** | 0 / 40 |
  | 0.5 | **20 / 40** | 0 / 40 |
  | 1.0 | **10 / 40** | 0 / 40 |

  BFS finds a path on every one of those grids, so the mazes were plainly
  solvable. Only perfect mazes were ever safe — a spanning tree has no loop to
  strand you — and **every fixture in the suite was a perfect maze**, which is
  why 183 passing tests never saw it. `TremauxSolver` had no test of its own at
  all until now; the new `TremauxSolverTest` braids deliberately and asserts the
  walk is a legal traversal (starts at start, ends at goal, never crosses a
  wall) across four generators and four braid factors.

  Perfect-maze behaviour is unchanged: 64/64 A/B fixtures produce a walk
  identical to the previous implementation's, since a tree never triggers the
  restored rule.

- **`LandmarkHeuristic` was inadmissible on weighted grids, so A* returned
  suboptimal routes (ADR-001 item 4).** The heuristic stored BFS **hop counts**
  regardless of the grid's costs. Hop counts bound cost from below only while
  every edge costs at least one hop's worth, so the class documented a "keep
  weights `>= 1.0`" rule — which `WeightedMazeGrid.setWeight` never enforced
  (it accepts any non-negative value). Violate it and A* still returns a path;
  it just isn't the cheapest one.

  Measured on twelve fully-braided 24² mazes with weights drawn from
  `[0.05, 0.35]`:

  | | before | after |
  |---|---|---|
  | cells where `h` exceeded true cost | **575 / 576** | **0 / 576** |
  | worst over-estimate (true distance ≈ 32) | **132.1** | 0 |
  | seeds where A* beat by Dijkstra on cost | **12 / 12** | **0 / 12** |
  | worst excess cost | **+36%** | 0 |

  **Why the suite never caught it:** every existing fixture was a *perfect*
  maze. A spanning tree has exactly one route between any pair of cells, so
  every heuristic — admissible or not — returns it. The defect only becomes
  reachable once the topology has redundancy, which is why these tests braid
  the maze first, and why it matters: braided multi-path meshes are precisely
  what the LoadBalancer integration guide tells users to build.

  `precompute` now chooses its metric from the grid rather than assuming.
  Uniform-cost grids keep the BFS fields (O(V + E) per landmark). Any grid
  carrying a non-`1.0` weight gets Dijkstra fields **in both directions** — and
  the second sweep is not redundancy. `MazeGrid` charges the weight of the cell
  being *entered*, so `d(a,b) − d(b,a) = w(b) − w(a)`: the graph is directed
  even though its passages are not, and the familiar symmetric
  `|d(L,b) − d(L,a)|` bound quietly assumes otherwise. Weighted mode uses the
  directed pair `d(L,t) − d(L,s)` and `d(s,L) − d(t,L)`, each of which follows
  from the triangle inequality without a symmetry assumption.
  `MazeMetricsWeightedDistanceTest` asserts the two sweeps genuinely disagree,
  so nobody deletes one as duplication.

  The fix is also a win, not just a tax: on 64² braided weighted topologies A\*
  with the corrected heuristic uses **5.79× fewer expansions and searches 1.9×
  faster** than plain Dijkstra. Precompute costs ≈ 8 ms per topology against
  ≈ 2 ms for a single Dijkstra solve, so it repays after roughly four queries —
  the normal case, since a topology is routed over many times between updates.
  No API change; existing callers get the correction for free.

- **The server reported itself unhealthy (`/actuator/health` → 503) whenever
  Redis was disabled — which is the default.** `spring-boot-starter-data-redis`
  is unconditionally on the classpath, so Boot's `DataRedisAutoConfiguration`
  contributes a `RedisConnectionFactory` even when `daedalus.redis.enabled` is
  `false` and `RedisConfig` is correctly gated off. The health
  auto-configuration then registered an indicator against that factory, its
  `PING` failed, and the failure propagated to the **aggregate** status:

  ```
  "redis": { "status": "DOWN",
             "details": { "error": "...Unable to connect to Redis" } }
  ```

  Everything else — `diskSpace`, `ping`, `livenessState`, `readinessState`,
  `ssl` — was `UP`, and `LeaderboardService` was logging *"in-memory backend
  (Redis disabled or unavailable)"*, i.e. the application was working exactly
  as designed. But `dev` is the default profile and sets
  `daedalus.redis.enabled: false`, so **anyone who cloned the repo and ran it
  had an app that answered its own health check with 503** — precisely the
  signal a load balancer or Kubernetes readiness probe uses to pull an instance
  out of rotation.

  Fixed in `application.yml` by binding the stock indicator to the same flag
  that gates the config:

  ```yaml
  management:
    health:
      redis:
        enabled: ${daedalus.redis.enabled:false}
  ```

  Note this is a *binding*, not a blanket disable — with
  `daedalus.redis.enabled=true` (the prod default) the indicator returns and
  Redis is monitored as before. `RedisHealthBindingTest` pins that direction
  specifically, because the tempting "simplification" to a literal `false`
  would silently blind production monitoring. It also closes the first half of
  the standing BACKLOG item for custom `HealthIndicator`s, with no custom code:
  Boot's indicator was already correct, it was merely registered
  unconditionally.

- **`HilbertCurveGenerator` emitted a forest, not a maze.** Found by auditing all 22
  generators for the spanning-tree contract after the LoadBalancer example produced an
  impossible result. At 32² it yielded **953 edges for 1024 cells — 71 disconnected
  components — with only 66 cells reachable from the origin**. Two causes, both silent: the
  hand-rolled recursive quadrant split did not compose into a real Hilbert curve, so
  consecutive cells were sometimes not adjacent; and when a cell arrived with no visited
  neighbour the code did `if (!candidates.isEmpty())` and simply **skipped carving it**,
  orphaning the cell without any error. The traversal is now the canonical `d2xy` Hilbert
  mapping (guaranteeing adjacency on power-of-two grids), and cells that cannot attach
  immediately are deferred to a repair pass instead of dropped. This mattered beyond
  aesthetics: both vision documents name Hilbert as *the* topology generator for
  LoadBalancer work, so anyone following that advice was routing over a disconnected graph
  and getting empty paths back with no error.
- **The "Hilbert has the best locality" recommendation is measurably false.** Having fixed
  Hilbert's connectivity, the obvious next question was whether it is actually the curve it
  claims to be — connectivity and fidelity are different properties. Measuring **stretch**
  (maze distance ÷ straight-line distance, 20,000 random pairs at 32²) inverts the vision
  document's comparison table:

  | generator | mean stretch | p95 | max | diameter |
  |---|---|---|---|---|
  | **prims** | **2.48** | 5.50 | 57 | 110 |
  | archimedes-spiral | 2.50 | 5.60 | 59 | 95 |
  | gauss | 2.60 | 6.33 | 69 | 123 |
  | morton-curve | 3.06 | 7.50 | 77 | 123 |
  | **hilbert-curve** | **4.62** | 11.00 | 115 | **235** |
  | recursive-backtracker | 9.31 | 25.40 | 289 | 436 |

  Hilbert scores **worse than Morton**, the reverse of the documented ranking, with more than
  double Prim's diameter. The cause is a conflation: the Hilbert *curve* does have excellent
  locality, but `HilbertCurveGenerator` walks the grid in curve order and then attaches each
  cell to a **random visited neighbour** — so the spanning tree is not the curve and inherits
  none of its locality. The vision document and the example now carry the measured table and
  recommend `prims` or `archimedes-spiral` for topology work.
  **The obvious fix was then tested and is worse.** Carving strictly *along* the curve — the
  maximally curve-faithful generator — measures **16.69** mean stretch with a diameter of
  1023, i.e. **3.6× worse than today's version and 6.7× worse than Prim's**. A space-filling
  curve carved end to end is a Hamiltonian *path*, and a path is the spanning tree with the
  worst possible diameter: two cells touching in 2-D can be a thousand steps apart along the
  snake. The relationship is therefore inverted from the intuition — greater curve fidelity
  makes maze locality *worse*, because curve locality is about ordering while maze locality is
  about tree diameter. What actually predicts it is **bushiness**, which the generator
  descriptors already record ("bushy texture; many short branches" for Prim's; long winding
  corridors for the worst performer). Topology generators should be chosen on that axis rather
  than on mathematical pedigree.
- **Connectivity is now verified for every generator.** `PerfectMazePropertyTest` covered
  8 of 22, which is how the above hid. `GeneratorConnectivityTest` asserts the full
  spanning-tree contract (reachable everywhere, exactly `V-1` edges) across all 21
  generators that claim it, plus Hilbert specifically on non-power-of-two and rectangular
  grids where the enclosing-square filter can break curve adjacency. `DungeonGenerator` is
  excluded by contract and keeps its own connectivity test.

### Verified

- **Uniform-spanning-tree cover times measured (G2 + T4).** Aldous-Broder and
  Wilson's sample the *same* distribution — a uniform spanning tree — so they
  differ only in cost, and the audit wanted that shown empirically. At first it
  couldn't be: both generators counted only cells *added to the maze*, which is
  exactly `n` for both, so `MazeStats` was blind to the random walking that
  actually dominates them. Both now count walk steps into `cellsExplored`, and
  the picture is stark (averaged over 7 seeds):

  | cells | Aldous-Broder steps | Wilson's steps | ratio | AB per cell | W per cell |
  |------:|--------------------:|---------------:|------:|------------:|-----------:|
  | 256   | 4,938   | 1,204  | 4.1x | 19.3 | 4.7 |
  | 1,024 | 27,492  | 6,925  | 4.0x | 26.8 | 6.8 |
  | 4,096 | 144,699 | 27,671 | 5.2x | 35.3 | 6.8 |

  Wilson's cost *per cell* stays flat (~5–7) while Aldous-Broder's climbs
  steadily (19 → 35) — the signature of blind cover-time walking versus
  loop-erased hitting-time walking — and the gap widens with size, as theory
  predicts. Locked in `RandomWalkCoverTimeTest`.
- **`GrowthEstimator` caveat found and documented.** Classifying those same
  random-walk series exposed a real limitation in the T1 tool: fitted from a
  *single seed*, Aldous-Broder's label swung between `O(n)` and `O(n^2)` across
  seeds and Wilson's once came back `UNKNOWN`, despite their true behaviour being
  stable and clearly separated once averaged. The javadoc now warns to average a
  randomized metric over several seeds before fitting.
- **DSU certified near-constant amortized (D1).** `util/DSU` already carried both
  optimizations — union by rank *and* two-pass path compression — so no
  production change was needed. Added structural guards that behaviour alone
  can't provide: if someone simplified `find` into a plain root walk, every
  correctness test would still pass while the structure silently degraded from
  inverse-Ackermann to `O(n)`. The new tests read `parent` directly to assert the
  path really is rewritten, and that rank ordering survives (CLRS Ch. 21 + 17).
- **Reservoir-sampled frontier declined (G3).** The idea was to cut frontier
  memory, so the frontier was measured first — using the `maxFrontierSize` the
  generators already record. Randomized Prim's peaks at 561 walls on a 64² maze
  and only 4,866 on a 512² one: **1.9% of cells, about 0.22 MB**, and the share
  *falls* as mazes grow, because the frontier tracks the perimeter of the grown
  region rather than its area. There is no pressure to relieve. Independently,
  the technique doesn't fit: Algorithm R samples one pass over a stream, whereas
  Prim's frontier is live mutable state that must persist across steps, so using
  a reservoir would mean rescanning the grid every step — O(n²) instead of the
  current O(frontier). Noted the real lever if it ever matters: encode each wall
  as one `int` rather than a two-`Point` object, ~10× smaller, no algorithm change.
- **Consistent hashing declined (X4).** The maze cache is a single-process
  bounded map; Redis is wired for the leaderboard, not for sharding mazes. A hash
  ring would be distribution infrastructure for a system that isn't distributed —
  and if it ever becomes one, Redis Cluster already shards by hash slot with
  minimal reshuffling, so doing it in the application would duplicate the
  datastore's mechanism and add a second thing to get wrong.
- **Parallelism trio measured; C1 and C2 declined, C3 reframed.** Generation was
  timed before any thread pool was written: 1.96 ms at 64², 5.01 ms at 128²,
  18.3 ms at 256², 106 ms at 512² (Borůvka). At the sizes this project actually
  serves — ≤128² — generation is **2–5 ms**, which fork/join setup would simply
  consume. The decisive objection is not speed but the contract: `MazeGenerator`
  promises *"same seed ⇒ same maze"*, and `ComplexityAnalyzer`, `GrowthEstimator`
  and much of the suite depend on that determinism; parallel rounds would put it
  at risk to save milliseconds. **C2** falls harder still — after D2 a full
  Dijkstra over an 80² maze runs in under a millisecond, so there is nothing to
  parallelise. **C3** was reframed rather than dropped: its speed rationale dies
  with C1, but quadrant generation with doorways punched through the seams is how
  rooms-and-corridors dungeon layouts get built, and that's a real gap — every
  current generator makes uniform perfect mazes. It belongs in the backlog as a
  single-threaded feature, judged on the layouts it produces.
- **`DeadEndFillingSolver`: a `Stream` removed from the cascade's inner loop.** Profiling put
  this solver second-worst at 14.66 ms, and the cause was not hashing. Its cascade counted a
  neighbour's surviving exits with
  `openNeighbors(n).stream().filter(...).count()` — a full stream pipeline built once per
  neighbour of every filled cell, which on a recursive-backtracker maze (almost entirely dead
  ends) is the hottest line in the solver. Replaced with a plain counting loop.
  Measured on the cascade phase in isolation, with both variants asserted to fill an identical
  set of cells: **1.13× / 1.24× / 2.77×**. The spread is wide because stream pipelines are
  exactly the shape JIT behaviour varies most on, so the honest reading is "consistently
  faster, magnitude unstable" rather than a headline multiple. Worth recording that the first
  attempt at this benchmark was **invalid** — it compared the legacy cascade alone against the
  full new solver including its BFS phase, which measures nothing; the numbers above come from
  the corrected like-for-like version.
- **Solver costs profiled before optimising, which redirected the work entirely (ADR-001).**
  With six solvers still using `HashMap`/`HashSet`, the plan was to move them onto the graph
  seam. Timing them first over 12 mazes at 80² changed the answer:

  | solver | time | | solver | time |
  |---|---:|---|---|---:|
  | wall-follower | 2.55 ms | | bidirectional | 6.94 ms |
  | bfs | 2.70 ms | | dead-end-filling | 14.66 ms |
  | dial | 4.83 ms | | tremaux | 20.01 ms |
  | dfs | 5.26 ms | | **ida-star** | **875.91 ms** |

  **IDA\* costs ~300× BFS and 44× the next-worst solver.** De-hashing it would have been
  rearranging deck chairs: the cost is inherent to iterative deepening, which re-searches from
  scratch each pass under a slightly larger f-bound — with unit costs the bound rises by 1 per
  pass, so a maze with a path hundreds of steps long is re-explored hundreds of times.
  The fix turned out to be a heuristic already built for another purpose. Swapping Manhattan
  for `LandmarkHeuristic` (ALT): **342.7 ms → 8.4 ms, a 41× speedup**. The same swap saves A\*
  only ~55% of expansions; IDA\* gains far more because re-expansion multiplies every saving.
  No code changed — `IDAStarSolver` already accepts a heuristic. Its javadoc now carries the
  measurements and says plainly when to use it: ALT when a maze is solved repeatedly, A\*/BFS
  for one-shot queries (ALT's precompute costs about as much as just solving the maze), and
  IDA\* itself only when `O(d)` memory is the actual constraint. It is a memory-optimised
  algorithm, not a time-optimised one, and the default heuristic makes that trade steeply.
- **d-ary heap benchmarked and declined (D3).** A 4-ary heap was measured against
  `java.util.PriorityQueue` inside a real Dijkstra loop (12 mazes at 80², warmed
  up, three reps) and came in at −1.5% / −8.5% / −1.8% — inside the noise, with a
  d=2 control swinging 11.8ms→22.7ms across reps. The heap simply isn't the
  bottleneck: the loop is dominated by `HashMap`/`HashSet` lookups on `Point`
  keys. No code was shipped rather than add a placebo optimization. The follow-up
  measurement is the useful part — swapping those maps for flat arrays indexed by
  `row * cols + col` ran **1.47–2.00× faster** on the identical workload, so idea
  **D2** was upgraded to High impact and is now the top performance item.
- **Bidirectional termination audited (S3).** `BidirectionalSolver` stops at the
  first frontier touch, and textbooks warn that this can return a path one step
  longer than optimal. Rather than assume it, the concern was measured: across
  **4,320** randomized braided mazes (sizes 6–20, three braid factors, random
  start/goal pairs) it never disagreed with BFS on path length, so the solver was
  left alone and the termination rule documented instead. A braided-maze sweep
  now lives in the suite as a regression guard — worth noting the previous tests
  could never have caught this, since a perfect maze has only one route.

### Security (2026-07-19)

- **STOMP `CONNECT` frames are now authenticated.** HTTP security guarded the
  `/ws/**` upgrade under `prod`, but nothing inspected STOMP frames, so the
  messaging layer had **no notion of who was connected**. Two consequences: a
  deployment exposing the endpoint without that HTTP rule — a misconfigured
  profile, or a proxy terminating the upgrade — had no second line of defence,
  and there was no principal on which any per-destination rule could ever be
  built. `StompAuthChannelInterceptor` validates the bearer token from the
  `CONNECT` frame's native headers and attaches a `Principal` carrying the JWT
  subject, sharing `JwtTokenService`'s decoder so issuance and verification
  cannot drift.

  Required under `prod`, advisory elsewhere — matching how `SecurityConfig` and
  `ProdSecurityConfig` already split the HTTP surface, so a dev or embedded
  desktop client still connects without minting a token. **A token that is
  present but invalid is refused in every profile**, including the permissive
  ones: "no credentials" and "bad credentials" are different situations, and
  only the first is something a relaxed profile should wave through.

  **Scope, stated plainly: this is authentication, not authorization.** A client
  can still subscribe to another user's frames. The broker's destinations are
  not scoped to an owner, and nothing in the domain records which subject owns a
  session, so "may this principal subscribe here?" is not yet answerable —
  closing that needs session ownership modelled first. The BACKLOG entry has
  been rewritten to say so rather than marked done.

  Per-frame validation was deliberately omitted: the principal is established
  once at `CONNECT` and carried on the session, so re-decoding the token on
  every `SEND` would cost thousands of verifications for no extra guarantee.
  The trade-off is that a connection outlives its token's expiry.

- **Per-key rate-limiter buckets are now bounded — and bounding them carefully.**
  The interceptor created a Resilience4j instance per distinct caller key and
  never evicted it, so anyone able to mint keys — forged subjects, or forged
  source IPs when `daedalus.ratelimit.trust-forwarded-header` is on — could grow
  the `RateLimiterRegistry` without limit. Buckets now live in a Caffeine cache
  capped by `daedalus.ratelimit.max-keys` (default 10 000) and expiring on
  `daedalus.ratelimit.idle-ttl` (default 10 minutes).

  **The obvious implementation would have been a bypass.** Evicting a bucket a
  caller has already drained hands them a full budget the moment they return, so
  a naive LRU turns "cycle keys fast" into "no rate limit at all" — trading a
  memory-exhaustion bug for an authentication-adjacent one. Each bucket's
  effective TTL is therefore raised to at least its own `limitRefreshPeriod`:
  past that point it would have refilled anyway, so discarding it is
  unobservable. That requires a per-entry Caffeine `Expiry` rather than a
  cache-wide `expireAfterAccess`, since base limiters configure different refresh
  periods (`mazeGenerate` and `authLogin` do not agree). Size-based eviction
  keeps the property too — Caffeine evicts approximately LRU, so a key flood
  discards the attacker's own idle entries rather than an active caller's
  drained bucket.

  Bucket creation also moved off `RateLimiterRegistry.rateLimiter(name, config)`
  to standalone `RateLimiter.of(...)`, because the registry retains every
  instance it creates — which is the leak being closed.

  Two things caught during the work, both by tests that already existed for
  other reasons. Widening `RateLimitProperties` broke four call sites at compile
  time (good — loud). Adding a convenience constructor then gave the record two
  constructors, and Spring's binder will not choose between them: it looks for a
  no-arg constructor, fails, and **the entire application context stops
  starting**. `ApplicationSmokeTest` — added earlier the same day precisely
  because no test booted the real context — turned that into a clear failure
  instead of a broken deployment. Fixed with an explicit `@ConstructorBinding`.

### Security

- **Per-key rate limiting on the throttled endpoints.** The three limiters
  (`mazeGenerate`, `mazeSolve`, `authLogin`) were global — a single
  Resilience4j bucket shared across every caller, so one noisy client could
  spend everyone else's quota (and one IP could burn the whole `authLogin`
  brute-force budget). Replaced the method-scoped `@RateLimiter` annotations
  with `@PerKeyRateLimit(...)` plus a `PerKeyRateLimitInterceptor` that
  resolves a caller key — authenticated subject (`Authentication.getName()`),
  else client IP — and throttles each key against its own bucket, cloned from
  the named instance's config in the `RateLimiterRegistry`. The YAML
  instances now serve as per-caller *templates*. `X-Forwarded-For` is trusted
  only when `daedalus.ratelimit.trust-forwarded-header` is set (off by
  default; on in `application-prod.yml`, which runs behind an ingress) so a
  direct client can't spoof the header to mint a fresh bucket per forged IP.
  The `429` wire contract is unchanged: `ApiExceptionHandler` collapses the
  composite instance name (`mazeGenerate::ip:…`) back to the base
  `mazeGenerate` for the body's `limiter` property, so no caller IP or subject
  leaks into the response, and `Retry-After` still resolves from the base
  instance's refresh period. New code lives under
  `com.daedalus.server.ratelimit` (`PerKeyRateLimit`, `RateLimitNaming`,
  `RateLimitKeyResolver`, `PerKeyRateLimitInterceptor`) plus
  `RateLimitProperties` / `RateLimitWebConfig` in `…server.config`; covered by
  18 new tests (naming round-trip, key resolution, per-key bucket isolation,
  and an end-to-end MockMvc 429 path). Clears the "per-key rate limiting" item
  from `BACKLOG.md`.

### Infrastructure

- **CI fixed and verified green.** Run #1 failed because `ci.yml` ran
  `mvn clean verify`, which never installs reactor artifacts into `~/.m2`,
  so the standalone `examples/biome-plugin` build couldn't resolve
  `daedalus-plugin-api:1.0.0-SNAPSHOT`. Switched the reactor step to
  `clean install` (commit `2519a1f`, 2026-07-02); also bumped actions for
  the Node 24 cutover (`checkout@v6`, `setup-java@v5`, `upload-artifact@v7`)
  and fixed the README badge URL. Run #2 (2026-07-03) passed — 56s total,
  reactor + biome-plugin both green.
- **`.gitattributes` added.** `* text=auto` with explicit `eol=crlf` for
  `*.bat`/`*.cmd`, `eol=lf` for `*.sh`, and `binary` for PDFs, images, and
  archives. Ends the CRLF churn that made untouched files (`.gitignore`,
  `_migration/migrate.bat`) show up as fully-rewritten phantom diffs on
  Windows. Tree renormalized with `git add --renormalize .`.
- **`.gitignore` cleaned.** Removed two literal `ECHO is on.` lines — an
  artifact of the batch script that originally generated the file (`echo`
  with no argument prints its own status instead of a blank line).
- **Coverage.** JaCoCo agent + per-module report wired into the reactor at
  `verify`. CI regenerates `.github/badges/jacoco.svg` on pushes to main
  (cicirello/jacoco-badge-generator) and commits it back `[skip ci]`; README
  shows the badge next to CI status.
- **Static analysis gates.** Checkstyle (minimal hygiene ruleset,
  `config/checkstyle.xml`, runs at `validate`) and SpotBugs (medium threshold,
  runs at `verify`) now fail the build. First run over the codebase surfaced
  and fixed four real issues: an unused import in `JwtTokenService`, a dead
  local (`ideal`) in `GameSessionService.complete`, a swallowed exception on
  classloader close in `PluginManager.shutdownAll` (now debug-logged), and a
  missing null guard on Micrometer’s `@Nullable Timer.record` return in
  `MazeGenerationService.generate`. Intentional-design findings
  (EI_EXPOSE_REP on events/DTOs/DI, CT_CONSTRUCTOR_THROW, MS_EXPOSE_REP on
  the static context accessors) are excluded with per-block justifications
  in `config/spotbugs-exclude.xml`.
- **Dependabot.** Weekly update PRs for the Maven reactor, the standalone
  biome-plugin pom, and the GitHub Actions used by the workflows; minor/patch
  bumps grouped into a single PR.
- **Issue & PR templates.** Bug report and feature request forms
  (`.github/ISSUE_TEMPLATE/`) plus a PR checklist template.
- **Container image.** Multi-stage `Dockerfile` (Maven build layer → slim
  Temurin 21 JRE, non-root user) for `daedalus-server`; the release workflow
  gained a job that publishes `ghcr.io/richeyworks/daedalus2:{version,latest}`
  on every `v*` tag.
- **CHANGELOG de-binarified.** The 2026-05-05 entry documenting OneDrive
  null-byte corruption contained a literal `\0` character, which made grep
  and diff tools treat this whole file as binary. Replaced with the escaped
  text form.

## [1.0.0] — 2026-05-11 (released with 1.0.0)

**Reference plugin + CI + core consolidation.** Four BACKLOG items closed
in this pass: the worked example plugin (`BiomeGeneratorPlugin`), GitHub
Actions CI, the Lightning policy decision, and the final newest-pick
generator (Recursive Backtracker) folded onto the shared Growing-Tree
engine. The example plugin lives in `examples/biome-plugin/` (deliberately
not part of the main reactor so `mvn clean verify` at the root keeps its
current scope) and demonstrates every interesting touchpoint of the SPI:
manifest declaration, algorithm registration, programmatic event
subscription, and stop-time disarm. The core changes finish what the
2026-05-07 Growing-Tree unification started — every member of the
newest / oldest / random / norm / state-machine family now plugs into
`GrowingTreeEngine` through a `GrowingTreePolicy`, with no bespoke loops
left in the catalog.

### Added

- **`examples/biome-plugin/`** — reference plugin module. Registers two
  themed generators (`forest-biome`, `desert-biome`) against
  `GeneratorRegistry` and subscribes to `MazeGeneratedEvent` to log a
  one-line summary per generation. Both generators are written from
  scratch against the public SPI — no reach-ins to package-private engine
  internals — so the example doubles as a from-zero tutorial for plugin
  authors.

  - `ForestBiomeGenerator` — recursive backtracker with a weighted
    vertical-first carve order. With probability 0.7 the two vertical
    directions occupy slots 0–1 of the per-cell try-order; with the
    complementary probability the two horizontal directions take those
    slots. Within-pair order is uniformly random on each side. Long
    trunks, short side branches. Perfect maze (single component, no
    cycles); seed-deterministic.
  - `DesertBiomeGenerator` — Sidewinder variant with a 1/3 run-close
    probability (vs. Sidewinder's 1/2). Longer horizontal corridors.
    Perfect maze; seed-deterministic.
  - `BiomeGeneratorPlugin` — extends `AbstractPlugin`. Subscribes to
    `MazeGeneratedEvent` by looking up Spring's well-known
    `ApplicationEventMulticaster` bean and calling
    `addApplicationListener(...)` on it. Plugin instances are loaded via
    `ServiceLoader` (not by the Spring bean factory), so `@EventListener`
    annotations on plugin classes are silently ignored; programmatic
    registration is the supported path. The listener unwraps
    `PayloadApplicationEvent` manually — `PluginEvent` is a Daedalus-domain
    POJO that doesn't extend `ApplicationEvent`, so Spring wraps it on
    publish; `@EventListener` does this automatically via its method-adapter
    layer, but a raw `ApplicationListener` doesn't. An `AtomicBoolean armed`
    flag is flipped to false in `stop()` to neutralise the listener; Spring's
    `removeApplicationListener` would also work, but the flag keeps the
    lifecycle methods one line each without retaining the listener reference
    as plugin state.
  - `BiomeGeneratorsTest` — perfect-maze invariant + seed-determinism +
    descriptor smoke tests for both generators.
  - `META-INF/services/com.daedalus.plugin.MazePlugin` — ServiceLoader
    entry so the plugin is discovered by the host's `PluginManager`.
  - `examples/biome-plugin/README.md` — build / run instructions plus
    the why-not-`@EventListener` explanation.

- **`examples/run-with-biome.sh`** — one-shot demo script. Installs
  `daedalus-plugin-api` into the local Maven repo, builds the plugin
  JAR, stages it in a `mktemp -d` plugin directory, then boots
  `daedalus-server` with `daedalus.plugins.directory` pointed at that
  directory. Forwards any extra arguments as Spring Boot run arguments.

- **`.github/workflows/ci.yml`** — `mvn -B verify` on push/PR for
  `main`. Java 21 Temurin via `actions/setup-java@v4` with built-in
  Maven cache. Locale + timezone forced to `en_US.UTF-8 / UTC` so any
  format-sensitive test is deterministic across runners. Builds the
  reference plugin in a follow-on step so the example doesn't silently
  rot. Concurrency group cancels in-flight runs on rapid pushes.

- **`.github/workflows/release.yml`** — tag-driven release pipeline.
  Triggers on `v*` tags; builds the reactor (`-DskipTests` since CI
  already validated the tip), builds the example plugin, extracts the
  matching CHANGELOG section as release notes, and publishes a GitHub
  Release with the server's `-exec.jar` and the plugin JAR attached.
  `softprops/action-gh-release@v2` handles the upload. Tags with
  `-rc` / `-beta` / `-alpha` suffixes are marked prerelease.

- **`GrowingTreePolicies.newestWithNormJump(double pJump)`** — new
  composed policy: mostly pick the newest cell (RB-style long corridors),
  with probability `pJump` jump to the active cell with the largest
  quadratic norm (a fork toward the high-norm corner). Endpoints
  short-circuit to the underlying singletons — `pJump = 0.0` returns
  `newest()`, `pJump = 1.0` returns `quadraticNorm()` — so the seed
  consumption pattern at the endpoints matches the underlying policy
  byte-for-byte. Used by `LightningGenerator` (see below); also generally
  available to plugin authors who want the same texture.

- **`GrowingTreePoliciesTest`** — five new unit tests covering
  `newestWithNormJump`: equivalence to `newest()` at `pJump=0.0`,
  equivalence to `quadraticNorm()` at `pJump=1.0`, seed determinism in
  the mixed regime, branch-coverage at `pJump=0.5` (both component
  policies fire over a small sample), and bounds-rejection for NaN /
  out-of-range probabilities.

### Changed

- **`LightningGenerator`** — given a genuinely different selection policy
  to restore its visual identity. The 2026-05-07 unification collapsed
  Lightning onto Gauss (both delegated to `quadraticNorm()`); per the
  BACKLOG resolution, Lightning now uses
  `GrowingTreePolicies.newestWithNormJump(0.15)` — mostly RB-like long
  corridors with a 15% chance per turn of forking toward the highest-norm
  active cell. Produces a jagged "lightning bolt with branches" texture
  distinct from every other generator in the catalog. **Seed-mapping
  change:** the `seed → maze` mapping for id `"lightning"` changed in
  this pass; pinned seeds from before 2026-05-11 will resolve to
  different mazes. The displayName drops the "(Fast)" qualifier since the
  hand-tuned fast path is long gone.

- **`RecursiveBacktrackerGenerator`** — folded onto `GrowingTreeEngine`
  via `GrowingTreePolicies.newest()`. The pre-refactor implementation
  maintained its own stack-of-cells DFS with a Fisher–Yates shuffle of
  `Direction.values()` and an in-order scan for the first unvisited
  neighbour; the engine's slow-path enumeration uses
  `Collections.shuffle` on a `List<Direction>`. For size-4 lists
  `Collections.shuffle` takes the fast path and emits exactly the same
  Fisher–Yates sequence (`nextInt(4), nextInt(3), nextInt(2)`).
  **Seed-mapping: preserved.** The original BACKLOG note had worried
  about a different `Random` consumption pattern; a side-by-side audit
  of the pre- and post-refactor code confirmed identical bit consumption
  end-to-end (same start-cell call, same shuffle output, the `newest()`
  policy consumes zero bits). Clients with pinned RB seeds resolve to
  the same maze before and after this refactor. The equivalence is
  locked by the new
  `RecursiveBacktrackerEngineEquivalenceTest` (parameterised over five
  `(rows, cols, seed)` combinations including tall, wide, and non-square
  grids). This was the last newest-pick generator carrying its own loop
  — the entire Growing-Tree family now lives behind one engine.

- **`README.md`** — adds a CI badge, points the "Writing a plugin"
  section at `examples/biome-plugin/`, and lists `examples/` in the
  workspace-layout overview.
- **`BACKLOG.md`** — removes the closed "Reference plugin:
  `BiomeGeneratorPlugin`" item and rewrites the stretch-goal
  "GitHub Actions CI" entry to reflect that the CI + release pieces
  are now done; only the optional coverage-upload step remains. The
  entire "Refactoring (core)" section is dropped — both items
  (Lightning's fate and RB on `GrowingTreeEngine`) shipped in this
  pass and the section had no other entries.

---

## [1.0.0] — 2026-05-07 (released with 1.0.0)

**Four BACKLOG items closed in one pass:** DSU extraction, Growing-Tree policy
unification, REST input validation, and per-method rate limiting on write
endpoints. All four were called out in `BACKLOG.md` (server hardening + core
refactor sections); each now has a real implementation plus tests, and the
matching backlog entries have been removed.

**Desktop visualizer is now actually runnable.** The `daedalus-desktop`
module shipped with `DaedalusLauncher` + `DaedalusPrimaryStage` referencing
a `/ui/main.fxml` and a `Theme` SPI that had no implementations and no
resources directory — the app would have crashed on startup with
`NullPointerException: main.fxml missing from /resources/ui`. This
release fills in the missing pieces so
`mvn -pl daedalus-desktop javafx:run -am` opens a window and draws mazes:

- **`/ui/main.fxml`** — `BorderPane` with a top toolbar (generator
  picker, rows / cols spinners, seed field, Generate button), a center
  `Pane` holding the rendering `Canvas`, and a bottom status bar.
  Controller wired via Spring's bean factory.
- **`/ui/cosmic.css`** — paired stylesheet for the Cosmic theme.
- **`MainController` (`@Component`)** — populates the generator
  and solver dropdowns from the live `GeneratorRegistry` and
  `SolverRegistry`, runs generations and solves through
  `MazeGenerationService` / `MazeSolverService` (so plugin events and
  metrics fire exactly as they do for the REST surface), renders the
  resulting `MazeGrid` via `toTileGrid()` onto the canvas with
  theme-driven colors, and re-renders on window resize. Three layers
  on every paint: tile grid (passages / walls / start / goal); solve
  path overlay in `theme.path()` (drawn under endpoint markers so
  start and goal stay visible, with connector tiles between
  consecutive path cells so the trace renders continuously rather than
  as dots); and finally the movable player marker as a circle in
  `theme.player()`. Reset puts the player back at start without
  re-running the generator. Arrow keys and WASD walk the player
  through open walls (closed walls silently block); reaching the goal
  flips the marker to `theme.path()` color and announces the win in
  the status bar.
- **`CosmicTheme` (`@Component implements Theme`)** — first concrete
  theme: dark navy + cyan + magenta palette; matches the
  `daedalus.ui.theme: cosmic` default in `application.yml`.

Note: `DaedalusLauncher` boots the full Spring context including the
embedded servlet container, so running the desktop client also exposes
the REST API on port 8080. Useful for debugging; potentially noisy if
something else is bound to that port.

### Added

- **`com.daedalus.util.DSU` — shared union-find utility.** Single
  implementation with both standard optimizations (path-compressing two-pass
  `find`, union-by-rank with `byte[]` ranks) over a fixed `int[]` keyspace.
  Maze generators that work in 2-D coordinates flatten via
  `r * cols + c`. Replaces the inline `HashMap<Point, Point>` DSUs that
  used to live in `KruskalsGenerator` and `BoruvkasGenerator` — same
  asymptotic complexity, no more boxing on the hot inner loop. The API
  also surfaces `sizeOf(int)`, `largestComponent()`, and
  `isFullyConnected()`; the first two are backed by an `int[]
  componentSize` array maintained at the root on every union plus a
  running `largestSize` max, so both queries stay O(1). `DSUTest` (unit
  + randomized stress against an oracle, cross-checking connectivity *and*
  size bookkeeping) locks in the invariants.

- **Kruskal's now early-exits when the spanning tree is complete.**
  `KruskalsGenerator` checks `dsu.isFullyConnected()` at the top of the
  edge-iteration loop and breaks when true, sparing the shuffle's
  cycle-creating tail (~half of the original edge list on a typical
  maze). Output is bit-for-bit identical for the same seed — the skipped
  edges were all guaranteed-no-op `union` calls; we just stop visiting
  them.

- **`GrowingTreePolicy` SPI + `GrowingTreeEngine` shared loop.** The
  Growing-Tree family (`GrowingTreeGenerator`, `LightningGenerator`,
  `GaussGenerator`, `TuringGenerator`) used to repeat the same
  frontier-list / pick-cell / carve-or-drop skeleton four times with only
  the cell-selection rule differing. Extracted: each generator now passes
  a one-method `GrowingTreePolicy` lambda (or stateful object, in
  Turing's case) into `GrowingTreeEngine.run(...)`. Existing public
  generator classes are kept as thin adapters for backward compatibility
  — callers that hold `new GaussGenerator()` references compile and
  behave identically. Named factories live in `GrowingTreePolicies`
  (`newest`, `oldest`, `random`, `middle`, `mixed(double)`,
  `quadraticNorm`, `turingMachine`); the four registered generators
  consume them instead of inlining lambdas, and the stateful
  Turing-machine policy was moved out of `TuringGenerator`'s private
  inner class into the shared bucket. `GrowingTreePoliciesTest` pins
  each factory's contract directly (synthetic active lists + fixed-seed
  `Random`).

- **`OldestPickGenerator` (id `oldest-pick`).** New built-in: a
  Growing-Tree variant that always expands the head of the active list,
  giving BFS-shaped wave-front growth — short branches, "expanding ring"
  texture, the visual opposite of Recursive Backtracker's long winding
  rivers. Existence as a five-line class plus one line in
  `AlgorithmConfig.builtInGenerators()` is the demonstration that the
  engine + policy extraction pays off. Covered by
  `PerfectMazePropertyTest`.

- **REST input validation on every write endpoint.** `GenerateRequest`,
  `MoveRequest`, and `LoginRequest` carry `jakarta.validation`
  annotations (`@NotBlank`, `@Pattern` for IDs, `@Min`/`@Max` for grid
  dimensions, `@Size` for usernames/passwords). `MazeController` is
  `@Validated` (enables param-level constraints on path / query) and
  every body parameter is `@Valid`. `ApiExceptionHandler` translates
  `MethodArgumentNotValidException` and `ConstraintViolationException`
  into RFC 7807 `ProblemDetail` 400 responses with a sorted
  `fieldErrors` map keyed by the offending field — replaces the
  previous "malformed payload returns 500" behavior that was called out
  in the audit. New: `MazeControllerValidationTest` (boundary cases per
  field) and `AuthControllerValidationTest` (login DTO).

- **`@AlgorithmId` composite constraint.** New annotation in
  `com.daedalus.api.validation` that bundles
  `@NotBlank + @Pattern("^[a-z0-9][a-z0-9-]{0,63}$")` with
  `@ReportAsSingleViolation`. Single source of truth for the algorithm
  / solver id regex; `GenerateRequest.generatorId` and
  `MazeController.solve`'s `solverId` path variable both wear it now,
  replacing the duplicated `@NotBlank @Pattern(...)` blocks. The
  composite's message is preserved verbatim from the prior
  `@Pattern` message so existing test assertions still hold.

- **`@NonNegativeCoordinate` constraint on `MoveRequest.to`.** Closes
  the documented validation gap where a request body with a negative
  `row` or `col` slipped past the API surface and silently flipped
  `GameSessionService#tryMove` to `false` (returning `200 OK`
  body=`false` instead of a structured 400). The validator lives in
  `daedalus-server`'s validation package and reaches into `Point` via
  its public accessors, so `daedalus-core` stays framework-free per its
  existing rationale. Upper-bound and adjacency checks remain owned by
  `tryMove` (which has access to the grid dimensions and current
  position); validation only catches the structurally impossible. New
  test cases in `MazeControllerValidationTest` cover null `to`,
  negative `row`, and negative `col`.

- **Resilience4j rate limiting on the three write endpoints.** Three
  named `@RateLimiter` instances configured in `application.yml`:
  `mazeGenerate` (30/min), `mazeSolve` (60/min — solving is cheaper),
  and `authLogin` (10/min — brute-force guard). `application-test.yml`
  overrides with very generous limits so MockMvc tests don't trip over
  themselves; `application-prod.yml` tightens `authLogin` further. All
  three configured `timeout-duration: 0` — fail fast with
  `RequestNotPermitted` rather than queueing.
  `ApiExceptionHandler#onRateLimited` maps the exception to a
  `429 Too Many Requests` with a `Retry-After` header carrying the
  limiter's actual `limit-refresh-period` (rounded up to whole seconds,
  floored at 1 per RFC 9110) and a problem-detail body whose `limiter`
  property names which instance was exhausted, so clients can
  differentiate "your generate quota is gone" from "your solve quota is
  gone" without us baking business meaning into HTTP.
  `ApiExceptionHandler` now takes an optional `RateLimiterRegistry` via
  an `@Autowired` constructor (Resilience4j Spring Boot autowires it
  from YAML); tests using the no-arg constructor see the previous
  1-second floor as the fallback. New:
  `ApiExceptionHandlerRateLimitTest` — five unit tests against the
  handler in isolation, including the registry-aware path
  (verifies `Retry-After: 60` for a 1-minute refresh, `Retry-After: 1`
  for a 250 ms refresh and for unregistered limiter names).

### Changed

- **`LightningGenerator`'s seed → maze mapping is no longer bit-for-bit
  identical to its pre-refactor output.** Pre-refactor Lightning used a
  faster array-based shuffle that filtered out-of-bounds neighbors
  *before* shuffling — that consumed `Random` differently than the other
  three Growing-Tree variants. The unified `GrowingTreeEngine` uses the
  slow path (shuffle all four directions, then iterate and bounds-check)
  so that `GrowingTreeGenerator`, `GaussGenerator`, and
  `TuringGenerator` all stay bit-for-bit identical to their previous
  output. Lightning was the odd one out, and unification + reproducibility
  across the family was preferred over Lightning's marginal allocation
  savings. Anyone pinning a Lightning seed should regenerate.

### Caveats

- **Rate limits are global, not per-IP / per-subject.** Resilience4j's
  `@RateLimiter` annotation is method-scoped — a single bucket shared by
  all callers. A new BACKLOG entry has been kept ("Per-key rate
  limiting") to track the upgrade to a `RateLimiterRegistry` plus
  `HandlerInterceptor` keyed off the request principal / IP.

## [1.0.0] — 2026-05-06 (released with 1.0.0)

**Cost-aware routing landed.** New `WeightedMazeGrid` adds per-cell entry
costs, and `DijkstraSolver` / `AStarSolver` now read those costs through
a polymorphic `MazeGrid#weightOf(Point)` hook (default `1.0`). Plain
`MazeGrid` instances are unchanged behaviourally, so existing solver
callers and the perfect-maze property test keep working untouched. Two
new core test files (`WeightedMazeGridTest`, `WeightedRoutingTest`) lock
in defaults / validation and prove that on a two-corridor maze the
solvers detour around a heavily-weighted cell and stay on the short
corridor when the penalty is modest.

This is the LoadBalancer-Lab integration angle from the Vision docs:
load on a node = cost to route through it. The same pattern works for
latency, terrain cost, swamp tiles, etc. Edge cost from `u` to `v` is
defined as `weightOf(v)`; the start cell is never charged because the
solver begins there rather than entering it.

**Multi-JAR discovery test restored and broadened.** `PluginManagerJar
DiscoveryTest` had a 4th test method (`discover_withMu...`) that lost
its body — the file was truncated at line 199 and broke the reactor.
Reconstructed as `discover_withMultipleJars_isolatesEachInItsOwnClass
loader`, plus a new `OtherSamplePlugin` test fixture so two genuinely
different plugins can coexist in the registry. Test asserts both jars
reach the registry under distinct ids, that `externalLoaders` holds
two distinct `URLClassLoader` instances, and that each loader's URL
list points at exactly one of the two jars we wrote (not collapsed
into a single loader). The "plugin.getClass().getClassLoader() is the
URLClassLoader" assertion is intentionally absent — Maven Surefire's
parent-first delegation lets the parent CL define the class because
the test fixtures are on the test classpath, so we probe the invariant
through `getURLs()` instead.

**Plugin-runtime audit gaps closed.** Three more tests added to
`PluginManagerJarDiscoveryTest`:

- `discover_ignoresNonJarFiles_butStillLoadsJarsBesideThem` — drops a
  real plugin JAR alongside `.txt` / `.yml` / `.zip` files plus a
  jar-named subdirectory; only the JAR is processed.
- `discover_jarWithNoServiceFile_tracksLoaderButRegistersNothing` —
  documents that a JAR with a class file but no `META-INF/services`
  entry produces zero plugins yet still has its `URLClassLoader`
  tracked, so `shutdownAll()` can release the file handle on Windows.
- `discover_corruptJar_publishesPluginFailedEvent_discoverPhase` —
  builds a JAR whose service file names a missing class and asserts
  the failure surfaces as a `PluginFailedEvent.Phase.DISCOVER`.

### Fixed

- **`PluginManager.loadJar()` now catches `Throwable`, not just
  `Exception`.** The original `catch (Exception e)` couldn't catch
  `ServiceConfigurationError` (which extends `Error`), so the most
  common discovery failures — service file naming a missing class,
  wrong type, plugin constructor throwing — would crash `discover()`
  outright instead of publishing a `PluginFailedEvent.Phase.DISCOVER`.
  The event-publication branch was effectively unreachable. Widening
  the catch to `Throwable` aligns this method with how `bootAll()` and
  `shutdownAll()` already treat lifecycle failures (each catches
  `Throwable`) and makes the "operators see plugin failures via
  `/topic/plugins/failures`" guarantee actually hold for discovery.

- **OneDrive sync corruption — 10 server-module files repaired.**
  A reactor build surfaced compile errors in six files with the
  unmistakable pattern of an interrupted OneDrive sync: trailing null
  bytes (`\0`) on some, mid-method truncation on others. A full
  sweep then found four more in the same state that the compiler
  hadn't reached yet because the build aborted early.

  **Cleanly recovered (trailing nulls only — surviving content is
  byte-identical to the pre-corruption file):**
  - `daedalus-server/.../config/OpenApiConfig.java`
  - `daedalus-server/.../controller/MazeWebSocketController.java`
  - `daedalus-server/.../test/.../MazeWebSocketControllerPluginFailedTest.java`

  **Reconstructed (truncation, but the missing tail was small or
  obvious from surrounding context):**
  - `daedalus-server/.../controller/MazeController.java` — initial
    pass added only the missing closing brace because the surviving
    tail looked clean; a follow-up build error revealed two more
    methods had been silently lost: the `GET /api/v1/leaderboard`
    endpoint (present in the class Javadoc but not the body) and a
    private `toResponse(UUID, String, int, int, long, MazeGrid)`
    helper called by both `generate` and `get`. Both now restored;
    the helper flattens `MazeGrid#toTileGrid()` (which returns
    `TileType[][]`) into the `char[][]` shape `GenerateResponse`
    expects. Lesson: corruption-tail detection that relies on "ends
    with `}`" misses the case where the last surviving content was
    itself a method-end brace inside a longer file.
  - `daedalus-server/.../controller/PluginController.java` — last
    `.toList()` of the existing stream pipeline plus the `/describe`
    endpoint (signature documented in README's REST table)
  - `daedalus-server/.../test/.../MazeControllerGeneratorIdTest.java`
    — the last few `jsonPath` assertions on `$.cols` and `$.seed`
  - `daedalus-server/.../test/.../JwtTokenServiceTest.java` — the
    body of `issuedToken_expiresAtMatchesTtl` (TTL math against
    `IssuedToken#expiresAt`)
  - `daedalus-server/.../DaedalusApp.java` — the small
    `SpringApplicationBuilder` shim subclass

  **Reconstructed with reasonable confidence but worth a second pair
  of eyes** (the surviving header + Javadoc described the intent
  clearly, but a meaningful chunk of body had to be rebuilt):
  - `daedalus-server/.../config/ProdSecurityConfig.java` — last few
    `requestMatchers` for protected write endpoints + plugin
    introspection + `/ws/**` + `/v3/api-docs/**` deny + `.anyRequest()
    .authenticated()` + `.oauth2ResourceServer(...jwt)` wiring
  - `daedalus-server/.../config/SecurityConfig.java` — entire
    `@Bean SecurityFilterChain` body (CSRF off, stateless sessions,
    `permitAll` on every documented path glob)

  **Backups of the corrupted originals** are at
  `/tmp/server-backup/` in the build sandbox; if the reconstruction
  diverges from the user's intent, the surviving prefixes can be
  diffed against the rebuilt files to find disagreement.

  **Root cause** is OneDrive's "Files On-Demand" feature lazily
  hydrating cloud-only files: when an editor or compiler reads a file
  that hasn't fully synced down, OneDrive sometimes returns the
  cached-locally portion plus null padding instead of waiting for
  hydration. The fix on the user's side is either pinning the project
  folder ("Always keep on this device") or moving the working copy
  off OneDrive entirely.

## [1.0.0] — 2026-05-05 (released with 1.0.0)

Reactor green: `mvn clean verify` passes 25 / 25 tests across all six modules
in 16 s. The four findings from the May 3 audit are confirmed applied; the
follow-ups it called out as "non-blocking" are now also done.

Two further changes landed later in the day, after the build was verified:
**OpenAPI / Swagger UI polish** and a **profile-aware Security split**. Both
are additive — the dev / test posture is unchanged, only the prod posture
gets meaningfully more restrictive, and there's a new test that locks in
which `SecurityFilterChain` bean activates per profile.

A subsequent pass added **JWT-based auth** to the prod posture — single ops
user with bcrypt-hashed password from env vars, `POST /api/v1/auth/login`
issues a self-signed HS256 JWT, write endpoints + `/ws/**` + plugin
introspection require the token, reads stay public. Two new test classes
(`JwtTokenServiceTest`, `AuthControllerTest`) lock in issue/decode round-trip
and the login contract.

### Added

- **`com.daedalus.api.dto` package** with 10 record-based DTOs extracted from
  controller inner classes — `GenerateRequest`/`Response`, `MoveRequest`,
  `SessionResponse`, `SolveResponse`, `GeneratedFrame`, `SolvedFrame`,
  `MoveFrame`, `PluginFailedFrame`, `PluginInfo`. Every record has Javadoc
  describing its endpoint or STOMP topic.
- **OpenAPI / Swagger UI polish.** New `OpenApiConfig` populates the doc-level
  `Info` (title, description, version, contact, license placeholder), declares
  the dev server URL, and pre-registers three tags (`Mazes`, `Plugins`,
  `Leaderboard`) for stable ordering in Swagger UI. `MazeController`,
  `PluginController`, and the leaderboard endpoint carry `@Tag` and
  `@Operation` summaries so the rendered UI explains each route. Spec is
  served at `/v3/api-docs` (JSON), `/v3/api-docs.yaml`, and `/swagger-ui.html`
  in dev / non-prod profiles.
- **`ProdSecurityConfig`** — new `@Profile("prod")` filter chain:
  `/actuator/health`, `/actuator/info`, `/actuator/prometheus` stay public
  (matching `application-prod.yml`'s exposure list); every other
  `/actuator/**` path requires authentication; `/v3/api-docs/**` and
  `/swagger-ui/**` are explicitly denied; `/api/**` and `/ws/**` remain
  permitted with TODOs for wiring real auth (OAuth2 / JWT / mTLS) before
  any non-trusted-network deployment.
- **`SecurityConfigProfileTest`** — locks in the `@Profile` split so the
  dev and prod chains can never both activate (which would crash boot).
- **JWT auth (prod)** — `JwtAuthProperties`, `AdminCredentialsProperties`,
  `JwtTokenService` (HS256, self-signed via `NimbusJwtEncoder` / `Decoder`),
  `LoginRequest`/`LoginResponse` DTOs, `AuthController` with
  `POST /api/v1/auth/login`. Dependency added: `spring-boot-starter-oauth2-
  resource-server` (brings in `nimbus-jose-jwt`). Config bound from
  `daedalus.security.jwt.*` and `daedalus.security.admin.*`; prod requires
  `DAEDALUS_JWT_SECRET` + `DAEDALUS_ADMIN_PASSWORD_BCRYPT` env vars. Dev
  defaults are baked into `application.yml` so login works out-of-box during
  development (admin / admin).
- **`JwtTokenServiceTest`** (4 cases) — round-trip claims, foreign-secret
  rejection, short-secret refusal at construction time, TTL math.
- **`AuthControllerTest`** (4 cases) — 200 + token on success; identical
  401 / no body on wrong password, unknown user, and unconfigured admin
  (no leakage of which check failed).
- **API versioning** on the REST surface: `MazeController` now mounts at
  `/api/v1`, `PluginController` at `/api/v1/plugins`. Class Javadoc, the one
  test that hits the endpoint, and its docstring all updated.
- **Desktop module tests** (`daedalus-desktop`, previously had none):
  - `ThemeManagerTest` — 3 cases covering the constructor's default-resolution
    branches (named-default present, named-default missing → fall back to first,
    empty theme list → no NPE).
  - `DaedalusLauncherTest` — 1 case locking in the static-lifecycle null-safety
    contract.
- **`@AfterEach closeManager()`** in `PluginManagerJarDiscoveryTest` — releases
  every `URLClassLoader` opened by `discover()` so JUnit's `@TempDir` cleanup
  can delete the test JARs on Windows.

### Changed

- **Controllers stripped of inner records.** `MazeController` 135→128 lines,
  `MazeWebSocketController` 68→63 lines, `PluginController` 40→37 lines.
  Routing/handler logic unchanged.
- **`SecurityConfig` is now `@Profile("!prod")`.** Behaviour for dev / test /
  the JavaFX desktop client is unchanged: every endpoint is `permitAll()`,
  Swagger UI works, actuator is open. Each `requestMatcher` is now explicitly
  declared and commented so the intent is obvious. `PasswordEncoder` moved
  to its own `PasswordEncoderConfig` class so the bean stays available
  regardless of which profile is active.
- **`AUDIT_RECOMMENDATIONS_2026-05-05.md`** rewritten from a backlog into a
  verification log. All audit items, including the five "non-blocking"
  follow-ups, now have date-stamped completion notes.
- **Workspace root** trimmed from 11 entries to 9: only `.idea/`, `_migration/`,
  the five Maven modules, `pom.xml`, `README.md`, `AUDIT_RECOMMENDATIONS_*.md`,
  and this file.

### Fixed

- **Spring Boot multi-module artifact collision.** `daedalus-server`'s
  `spring-boot-maven-plugin` now uses `<classifier>exec</classifier>` so the
  thin JAR remains the main Maven artifact (downstream modules like
  `daedalus-desktop` can compile against it) and the executable fat JAR is
  published as `daedalus-server-<version>-exec.jar`. Run with
  `java -jar daedalus-server-<version>-exec.jar`.
- **`PluginManagerJarDiscoveryTest` Windows file-locks.** Three tests called
  `discover()` (which opens a `URLClassLoader` per JAR) but never invoked
  `shutdownAll()`. The new `@AfterEach` closes the loaders before `@TempDir`
  cleans up. Net effect: `mvn clean verify` now goes green on Windows.

### Licensed

- **MIT License** — added `LICENSE` at project root. Copyright 2026 Richmond.
  README updated to point at it; `OpenApiConfig` swagger metadata switched
  from "Unlicensed (no license file in repo yet)" to MIT.
- **SPDX-License-Identifier headers** — `// SPDX-License-Identifier: MIT`
  added as line 1 of every Java source file (109 across the five modules)
  plus the two files under `Code/`. Total: 111 files. Lets automated
  license-scanners (FOSSA, ScanCode, REUSE) detect the license per-file
  without having to read the root `LICENSE`.

### Removed

- Three superseded audit zips from project root: `daedalus-complete-audit-
  2026-05-03.zip` (duplicate of `(1)` archive), `daedalus-full-audit-
  2026-05-03.zip`, `daedalus-server-audit-2026-05-03.zip`.
- Empty `src/` skeleton (23 leftover directories from the multi-module split
  that `migrate.bat` should have removed).
- Two 0-byte stub files in root: `com.daedalus.desktop`, `com.daedalus.server`.
- `migrate.bat` and `MIGRATION.md` from the active root (archived to
  `_migration/`; migration is complete).

### Verified (no changes needed)

- All four audit patches (`M