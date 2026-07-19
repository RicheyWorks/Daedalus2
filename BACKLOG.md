# Daedalus Backlog

Forward-looking work items not yet captured in the current code or in
`AUDIT_RECOMMENDATIONS_2026-05-05.md`, `Audit/DAEDALUS_ENGINE_AUDIT_FEEDBACK_RECOMMENDATIONS.md`,
or the `Vision/` documents.

This file consolidates the surviving "to do" intent from the legacy
`_migration/legacy-archives/Daedalus_Complete_Master_Portfolio` v1.x
portfolio drops (now deleted). Anything those archives contained that was
either already implemented in the current code or already documented
elsewhere has been omitted on purpose.

Last consolidated: 2026-05-07

---

## Hardening (server)

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
- **Re-triage the open Dependabot PRs against Boot 4.** The parent bump to
  `spring-boot-starter-parent` 4.1.0 re-pins most managed dependency versions,
  so any open PR bumping a Boot-managed 3.x artifact is now either obsolete or
  actively conflicting. Close the superseded ones rather than merging them.
- **WebSocket / STOMP authorization — *authentication* done 2026-07-19,
  per-destination rules still open.** `StompAuthChannelInterceptor` validates the
  bearer token on `CONNECT` and attaches a `Principal`; required under `prod`,
  advisory elsewhere. A token that is *present but invalid* is refused in every
  profile — "no credentials" and "bad credentials" are different, and only the
  first should be waved through by a permissive profile.

  **What remains is the part the original note actually asked for.** A client can
  still subscribe to another user's frames, because the broker's destinations
  (`/topic/maze/{id}/state`, `/topic/session/{id}/player`) are not scoped to an
  owner and **nothing in the domain records which subject owns a session** — so
  "may this principal subscribe here?" is not a question the server can answer
  yet. Closing it needs session ownership modelled first, then a `SUBSCRIBE`
  rule matching destination against principal. Authenticating `CONNECT` is the
  prerequisite for that work, not a substitute for it.

  Per-frame validation was deliberately *not* added: the principal is
  established once and carried on the session, so re-decoding the token on every
  `SEND` would cost thousands of verifications for no additional guarantee. The
  consequence is that a connection outlives its token's expiry — disconnecting
  on expiry is its own feature.

## New surfaces

- **Performance benchmark harness.** Standalone `main` (or JMH module)
  that times all 20+ generators and 9 solvers on 50×50 / 100×100 / 200×200
  grids, multiple seeds, prints CSV + a small chart. Ship the latest run
  in `docs/benchmarks/` so README can link to it.
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

- **Procedural dungeon mode.** Rooms + corridors over `RecursiveDivision`
  with a post-process that punches doorways. New `MazeGenerator`
  implementation, not a refactor of an existing one.
- **Multiplayer sessions.** Multiple players in the same maze via per-
  session WebSocket scopes. Existing `GameSessionService` already tracks
  one player per session; lift that constraint behind a feature flag.
- **Web UI.** Lightweight React or Vue frontend that subscribes to the
  STOMP topics and renders generation/solve frames in real time.
- **Coverage upload to a free service.** The CI workflow added on
  2026-05-11 covers `mvn -B verify` + example-plugin build, and the
  release workflow attaches the exec JAR on `v*` tags — the only piece
  of the original "GitHub Actions CI" backlog item still outstanding is
  uploading test coverage to Codecov / Coveralls. Punted until someone
  wants the badge.

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
