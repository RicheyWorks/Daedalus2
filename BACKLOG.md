# Daedalus Backlog

Forward-looking work items not yet captured in the current code or in
`AUDIT_RECOMMENDATIONS_2026-05-05.md`, `Audit/DAEDALUS_ENGINE_AUDIT_FEEDBACK_RECOMMENDATIONS.md`,
or the `Vision/` documents.

This file consolidates the surviving "to do" intent from the legacy
`_migration/legacy-archives/Daedalus_Complete_Master_Portfolio` v1.x
portfolio drops (now deleted). Anything those archives contained that was
either already implemented in the current code or already documented
elsewhere has been omitted on purpose.

Last consolidated: 2026-08-17

---

## Hardening (server)

- ~~**The 27 bodiless 404s.**~~ **Done 2026-07-31.** All 27 `ResponseEntity.notFound().build()`
  sites now throw `ResourceNotFoundException` and answer in the RFC 7807 shape, which closes the
  last hole in the error contract — `ErrorContractTest`'s `ALLOW_EMPTY_404` exemption is now
  `false`.

  The interesting part was not the 27 edits. It was that several of those sites had been
  answering different questions with the same empty body: session-unknown versus
  session-fine-but-its-maze-was-evicted, no-such-maze versus nobody-has-finished-this-maze-yet,
  unregistered-generator versus unmeasured-metric. Flattening had hidden real distinctions, and
  giving each a body surfaced them. One case deliberately stayed flat: `join` with multiplayer
  off must keep looking absent rather than disabled.

- ~~**Registrations outlive the plugin that made them.**~~ **Done 2026-07-31.** Neither `GeneratorRegistry` nor
  `SolverRegistry` had an unregister, so `PluginManager.shutdownAll()` closed the plugin's
  `URLClassLoader` while the algorithms it contributed stayed in the global maps. Already-loaded
  classes keep working after `close()`, so a "stopped" plugin's generator was still listed by
  `/api/v1/algorithms` and still callable — and on Windows the JAR cannot be replaced while those
  classes are reachable, which is the file-locking problem the classloader hygiene work was
  supposed to have solved.

  Fixed the same day. Both registries gained `unregister(id)` that refuses built-ins, and
  `PluginManager` attributes contributions by diffing the registry's id set across each plugin's
  whole boot — which needs no change to the SPI plugin authors compile against, and is honest
  that a plugin registering later from its own thread is unattributable. Every entry is unloaded,
  not only the `STARTED` ones, because a plugin that registered and then threw in `start()` has
  contributions in the registry and no `STARTED` state. `PluginUnloadTest`; teeth in
  `mutants/unloadteeth.py`.

- ~~**Per-key rate-limiter bucket eviction.**~~ **Done 2026-07-19.** Buckets now
  live in a Caffeine cache bounded by `daedalus.ratelimit.max-keys` (default
  10 000) and expiring on `daedalus.ratelimit.idle-ttl` (default 10 minutes),
  instead of accumulating in the `RateLimiterRegistry` forever.

  The non-obvious part is that bounding the store can itself *defeat* the
  limit: discard a bucket a caller has already drained and they get a full
  budget back, so cycling keys fast enough to force eviction would bypass
  throttling entirely. Each bucket's effective TTL is therefore raised to at
  least its own `limitRefreshPeriod` — past that it would have refilled anyway,
  so dropping it is unobservable. That needs a per-entry Caffeine `Expiry`
  rather than a cache-wide `expireAfterAccess`, because different base limiters
  configure different refresh periods. `PerKeyRateLimitEvictionTest` pins both
  directions, driving a fake `Ticker` so the assertions are exact rather than
  slept for.
- ~~**Re-triage the open Dependabot PRs against Boot 4.**~~ **Done 2026-07-31.** Closed #3
  (slf4j-api), #4 (spring-context), #5 (assertj-core) — all re-pinned by the Boot 4.1 parent —
  and #8, the parent bump itself, long since applied by hand. Kept for individual judgment:
  #1/#2 (actions bumps, low risk), #10 (Checkstyle 10→13, three majors, expect new rule
  violations), #11 (jacoco/checkstyle/spotbugs build plugins — merge after a local
  `mvn verify`). #9 (JavaFX 26) closed the same day once verified: it is compiled
  `--release 24` and needs JDK 24+, and the project pins `java.version` 21 — revisit when
  the JDK baseline moves. Original triage notes kept below for the record.

  *2026-07-29: fully scripted —* `docs/handoff/triage-dependabot.ps1` *(dry-run by
  default,* `-Close` *to execute); see* `docs/handoff/README.md` *for the whole
  fifteen-minute GitHub-chores pass. Original manual commands kept below for reference.*

  *2026-07-28: this is a GitHub-side action, not a code change. One pass:*
  `gh pr list --author "app/dependabot" --json number,title` *then, for each PR
  bumping an artifact that `mvn dependency:tree` shows Boot 4.1 already manages
  at an equal-or-newer version,* `gh pr close <n> --comment "superseded by the
  Boot 4.1.0 parent bump"`. *Anything Boot does not manage (JavaFX, resilience4j,
  springdoc, build plugins) gets judged on its own.*
- ~~**WebSocket / STOMP authorization.**~~ **Done — authentication 2026-07-19,
  per-destination rules 2026-07-28.** `StompAuthChannelInterceptor` validates the
  bearer token on `CONNECT` and attaches a `Principal`; required under `prod`,
  advisory elsewhere. A token that is *present but invalid* is refused in every
  profile — "no credentials" and "bad credentials" are different, and only the
  first should be waved through by a permissive profile.

  The per-destination half: sessions opened by an authenticated request record
  the token's subject as **owner** (`GameSession.owner()`, null for anonymous
  opens), and `StompSubscriptionAuthorizationInterceptor` refuses `SUBSCRIBE`
  to an owned session's `/topic/session/{id}/player` unless
  `GameSession.maySubscribe` says yes — the owner, or a subject that joined
  with a token (ADR-012, 2026-08-17). Joining used to put a piece on the board
  and leave the feed owner-only. Deliberately open: unowned sessions (dev/desktop
  posture — no claim to enforce), unknown session ids (refusing would make the
  rule an existence oracle), and the shared `/topic/maze/**` +
  `/topic/plugins/**` surfaces, which carry no per-user data. Pinned by
  `GameSessionTest` (the decision, in core),
  `StompSubscriptionAuthorizationInterceptorTest` (every branch) and
  `WebSocketOwnershipSmokeTest` (interceptor installed; owner and joiner
  receive frames; refusal reaches a real client as a STOMP ERROR) — the latter
  replayed against a build without the interceptor registered, per the house
  teeth rule.

  Per-frame validation was deliberately *not* added: the principal is
  established once and carried on the session, so re-decoding the token on every
  `SEND` would cost thousands of verifications for no additional guarantee. The
  consequence is that a connection outlives its token's expiry — disconnecting
  on expiry is its own feature.

  **2026-08-17:** the HTTP `/ws/**` upgrade is public in prod. Browsers cannot
  attach `Authorization` to SockJS, so authenticating the handshake made the
  signed-in UI's `CONNECT` unreachable. The frame is still the gate.

## Living mazes v2

- ~~**Wall closing / hardening.**~~ **Done 2026-08-17 (ADR-008).** ADR-006's re-fire
  trigger (traffic or fog-of-war shipped → revisit closing with a connectivity proof)
  fired. `Sealer` closes the complement of a spanning forest so a tick can harden many
  walls without stranding anyone; `POST /live?seal=` is opt-in and the process default
  stays 0. Campaign stages that only declare `living` stay v1; the finale now also
  declares `hardening`, and the client folds that into one `/live?seal=` call.

- ~~**Capacitated max-flow.**~~ **Done 2026-08-17 (ADR-009).** `MazeFlow` already had
  Edmonds-Karp; every passage was capacity 1, so "capacity" in the topology example was
  a recount of links. The unit reading stays the product default (chokepoint count).
  Real capacities are opt-in per call. Hilbert's API descriptor was still claiming the
  locality the July measurement disproved; that string is what `/algorithms` ships.

- ~~**Bipartite matching.**~~ **Done 2026-08-17 (ADR-010).** The next ADR-001 appendix
  item after capacitated flow. A* routes; matching assigns. First-fit strands the
  request that can only use a seat someone else took — the test compares against
  that greedy so a rewrite to it fails. No REST surface: a maze has no batch of
  incoming requests.

- ~~**Incremental SSSP.**~~ **Declined 2026-08-17 (ADR-011).** Measured: full
  Dijkstra after a living tick is 50–200 µs at the sizes `/live` serves, 2 ms at
  128², against a 2 s ticker. The textbook repair cannot pay for itself. Re-fire
  conditions are in the ADR.

- ~~**Bellman-Ford / Johnson.**~~ **Declined 2026-08-17 (ADR-013).** Appendix
  item 4. Weights are costs in `[1, 1000]`; there is no negative edge.
  Re-fire if a directed latency graph with signed hops appears.

- ~~**Waypoint tour vs living mazes.**~~ **Done 2026-08-17 (ADR-014).** The
  tour cache scored you against the tree the coins were first placed on.
  Placement stays frozen; the optimum is Held-Karp on the live grid.

- ~~**CLRS G4 Kruskal texture / D2 packed grid.**~~ **Declined 2026-08-17
  (ADR-015, ADR-016).** Shuffle is already Kruskal; bias is already
  weighted Prim's. A `long[]` `MazeGrid` cannot pay at API sizes. Cell
  nibble + allocation-free `MazeGraph` shipped as the cheap leftovers.

## New surfaces

- ~~**Performance benchmark harness.**~~ **Done 2026-07-19** —
  `examples/benchmark-harness`, a standalone `main` timing all 22 generators and
  10 solvers at configurable sizes (default 50/100/200) and seed counts, writing
  `docs/benchmarks/benchmark-<date>.csv` plus a console summary with a
  "vs fastest" column.

  Three decisions worth knowing. Every run records its JVM, OS, CPU count and
  heap into the CSV header, because a timing without its machine is an anecdote
  — the useful column is *relative* cost within a run, not absolute
  milliseconds. Timings are **medians**, so one GC pause cannot move a published
  number. And an algorithm exceeding a 2 s budget is measured once and flagged
  `single-sample` rather than warmed up and repeated five times: IDA\* is roughly
  300× BFS, and without that rule a full sweep never finishes.

  Deliberately **not** a reactor module and **not** run in CI — a timing
  assertion on a shared runner fails for reasons unrelated to the code. Its own
  tests assert structure (full algorithm coverage, well-formed rows, median
  behaviour), never durations.
- **Custom Spring Boot `HealthIndicator`s.** ~~Two~~ one remaining:
  1. ~~`RedisHealthIndicator`~~ — **done 2026-07-19, and no custom code was
     needed.** Boot's stock indicator already does a real `PING`; the actual
     defect was that it registered *unconditionally*, so an instance with
     `daedalus.redis.enabled=false` answered `/actuator/health` with **503**
     while running perfectly on its in-memory backend. Fixed by binding
     `management.health.redis.enabled` to `${daedalus.redis.enabled:false}` in
     `application.yml`. Both directions are pinned by tests
     (`ApplicationSmokeTest`, `RedisHealthBindingTest`).
  2. ~~`PluginSubsystemHealthIndicator`~~ — **done 2026-07-19.** Reports
     `loadedPlugins`, `failedPlugins` and a `lastFailure` description as
     actuator health details, and is **deliberately never DOWN**: Boot folds
     component statuses into the aggregate, and the aggregate is what a load
     balancer or readiness probe acts on, so condemning the instance over a
     broken *optional* plugin would be the same defect the stock Redis
     indicator caused earlier the same day. Failures are surfaced as detail for
     a human to act on. The original note below already called for exactly this
     ("components, not as the top-level status") — reproduced for the record:

     > reports the count of loaded plugins, count of failed plugins (since last
     > `bootAll`), and the most recent `PluginFailedEvent` (if any). Wire both
     > into `/actuator/health` as components, not as the top-level status (so a
     > degraded plugin doesn't take the app out of the load balancer's
     > rotation).

## Stretch goals (no commitment, capture only)

- ~~**Procedural dungeon mode.**~~ **Done (predates this note's cleanup) —**
  `DungeonGenerator` in daedalus-core is rooms + corridors as a new
  `MazeGenerator` implementation, via BSP splitting rather than the
  `RecursiveDivision` post-process this note sketched: recursive splits, a room
  per leaf, L-shaped sibling corridors, connectivity guaranteed by recursion
  order. Deliberately not a perfect maze (open rooms, loops, unreachable rock);
  `DungeonGeneratorTest` pins its own connectivity property, and the
  spanning-tree roster guard excludes it as visible code.
- ~~**Multiplayer sessions.**~~ **Done 2026-07-28** — behind
  `daedalus.session.multiplayer` (default `false`; off is byte-for-byte the
  pre-flag behavior). `GameSession` tracks per-player positions (opening
  player mirrored into `currentPosition()` for compatibility);
  `POST /api/v1/session/{id}/join?player=` admits extra players (404 with the
  flag off, as if the endpoint did not exist; rejoin keeps the player's
  position); `MoveRequest.player` names who moves; `PlayerMovedEvent` and
  `MoveFrame` gained an additive nullable `player` field so existing listeners
  and clients keep working. Any player reaching the goal completes the session
  exactly once. Pinned by `GameSessionMultiplayerTest` +
  `MazeControllerJoinTest`. **STOMP follow-up 2026-08-17 (ADR-012):** joining
  with a token now grants `SUBSCRIBE` on the owned player topic. Anonymous
  join still gets a seat, not the feed. Cap 8. Spectator permalink stays
  read-only until the page POSTs `/join`.
- ~~**Web UI.**~~ **Done 2026-07-28** — one file of vanilla JS
  (`daedalus-server/src/main/resources/static/index.html`, served at `/` by
  Boot convention; `WebUiSmokeTest` pins that convention). Generate/solve/play
  over the REST API, live frames over the STOMP topics via SockJS, canvas
  renderer with solver-path overlay and per-player markers; arrow keys move
  the opening player, WASD the joined one when the multiplayer flag is on.
  Deliberately framework-free — no build step, no npm; it exercises the public
  surfaces exactly as an external integrator would, so it doubles as living
  documentation of the API. **2026-08-17:** Sign in attaches the JWT to REST
  and STOMP (prod generate/play and ADR-012 join-with-token); Fog of war
  walks the agent API and paints only stood-on cells. Show ASCII uses
  `Accept: text/plain`; the plugin panel lists `GET /plugins`. The
  leaderboard Algorithm select is `?generator=`, disabled when `maze=`
  already owns the board. Solver routes, player trails, fog walks, and
  the ghost all paint corridor tiles, not a polyline through the walls.
  A `#session=` spectator hydrates every player's walk from `walks`
  (the opener's `trail` is still ghost material) and keeps the session
  hash so a refresh still spectates. Hunt waypoints paints the Held-Karp
  `path` through the openings, not only the coins you are scored against.
  Permalinks keep their kind (`#daily`, `#campaign=`, `#generator=`)
  instead of collapsing to `#maze=`. `GET /session/{id}/tour` is a read
  — a spectator cannot mint the coins — and hydrates a hunt or ghost
  that already exists. Fog plus a living tick re-polls the agent only;
  `GET /maze` would have painted rooms the walk has not stood in.
  Generate accepts `braid`; the tournament load-it link rebuilds the
  sample that was raced, not the unbraided seed. A living tick
  refreshes hardest-route, the heat map, sanctuaries, the lens, the
  fingerprint, and ASCII the same way it already rescored the tour. A
  plugin failure refreshes the roster; generate and tournament share
  one braid factor.

- ~~**Coverage upload to a free service.**~~ **Done 2026-07-28** — `ci.yml`
  uploads every module's JaCoCo XML to Codecov via `codecov-action@v5`,
  guarded on the `CODECOV_TOKEN` Actions secret: without the secret the step
  skips and CI behaves exactly as before. To activate, add the repo on
  codecov.io and set its upload token as `CODECOV_TOKEN`.

---

## What was omitted (and where to find it instead)

| Legacy item | Why omitted |
| --- | --- |
| Implement Solver Layer (AStar, Dijkstra, BFS, DFS) | Done — see `daedalus-core/src/main/java/com/daedalus/solver/solvers/` (9 solvers, exceeds the original ask). |
| Add Test Suite | Done — 1,194 lines across 5 modules; itemized in `AUDIT_RECOMMENDATIONS_2026-05-05.md` §3. |
| Plugin Security Hardening | Done — JWT-bearer auth on prod profile + isolated `URLClassLoader` for external plugins; see `AUDIT_RECOMMENDATIONS_2026-05-05.md` §"Open follow-ups" #5. |
| algorithms.md visual / complexity guide | Covered by `PDFs/05-Generator-Catalog.pdf`. |
| Better error messages on unknown generator/solver id | Already returns a clean 404 from `MazeController` after the API-versioning pass. |
| MazeVisualizer interface, JMX exposure, Chaos Mode generator, parallel generation, MazeReplay, more A* heuristics (Octile etc.) | All captured in `Audit/DAEDALUS_ENGINE_AUDIT_FEEDBACK_RECOMMENDATIONS.md`. |
| WeightedMazeGrid + weighted routing | Done — see `daedalus-core/src/test/java/com/daedalus/engine/WeightedMazeGridTest.java` and `WeightedRoutingTest.java`. |
| LoadBalancer integration / "Daedalus as a Service" / topology generator | Captured in `Vision/02-LoadBalancer-Integration-Guide.md` and `Audit/DAEDALUS_ENGINE_AUDIT_FEEDBACK_RECOMMENDATIONS.md` §3. |
| Algorithm comparison video / GIF, regenerate portfolio ZIP | One-time deliverables, not tracked. |
