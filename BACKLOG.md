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

- **Per-key rate-limiter bucket eviction.** Per-key limiting shipped
  2026-07-18 (`com.daedalus.server.ratelimit` — `@PerKeyRateLimit` +
  `PerKeyRateLimitInterceptor`, replacing the old global `@RateLimiter`
  annotations). The one open thread: the interceptor creates a Resilience4j
  instance per distinct caller key and never evicts them, so a
  high-cardinality attacker (many forged subjects, or many IPs when
  `daedalus.ratelimit.trust-forwarded-header` is on) could grow the
  `RateLimiterRegistry` unbounded. Live key cardinality is tiny today (a
  handful of subjects; login is IP-keyed), so this is deferred — but before
  any untrusted-network deploy, back the per-key buckets with a bounded /
  idle-evicting store (a Caffeine cache of `RateLimiter`s, or a scheduled
  purge of instances whose permits are full and untouched for N minutes).
- **Full-context smoke test (`@SpringBootTest`) — coverage gap found during the
  Boot 4 migration.** Every server test today is a slice: `@WebMvcTest`
  controllers plus `ApplicationContextRunner` for `RedisConfig`. Nothing boots
  the whole application context, and nothing exercises `/v3/api-docs` or
  `/swagger-ui/**`. That means the springdoc **2.6.0 → 3.0.3** major bump —
  which changed the emitted document from OpenAPI 3.0.x to **3.1.0** — was
  invisible to a fully green suite; it had to be checked by packaging the jar
  and curling the endpoints by hand. Add one
  `@SpringBootTest(webEnvironment = RANDOM_PORT)` that asserts the context
  loads, `/actuator/health` is `UP`, and `/v3/api-docs` returns 200 with the
  expected path count. Cheap, and it converts "I remembered to check" into
  something CI enforces.
- **Re-triage the open Dependabot PRs against Boot 4.** The parent bump to
  `spring-boot-starter-parent` 4.1.0 re-pins most managed dependency versions,
  so any open PR bumping a Boot-managed 3.x artifact is now either obsolete or
  actively conflicting. Close the superseded ones rather than merging them.
- **WebSocket / STOMP authentication.** HTTP JWT auth is wired in
  `ProdSecurityConfig` (2026-05-06), but the STOMP topics under
  `/topic/maze/**` and the `/ws/**` upgrade are not yet authenticated at
  the message level. Add a `ChannelInterceptor` that validates the JWT on
  `CONNECT` and per-message `SEND` so a client can't subscribe to another
  user's session frames.

## New surfaces

- **Performance benchmark harness.** Standalone `main` (or JMH module)
  that times all 20+ generators and 9 solvers on 50×50 / 100×100 / 200×200
  grids, multiple seeds, prints CSV + a small chart. Ship the latest run
  in `docs/benchmarks/` so README can link to it.
- **Custom Spring Boot `HealthIndicator`s.** Two:
  1. `RedisHealthIndicator` — only registered when `daedalus.redis.enabled`
     is `true`; reports OK / degraded / down based on an actual `PING`.
  2. `PluginSubsystemHealthIndicator` — reports the count of loaded
     plugins, count of failed plugins (since last `bootAll`), and the most
     recent `PluginFailedEvent` (if any). Wire both into
     `/actuator/health` as components, not as the top-level status
     (so a degraded plugin doesn't take the app out of the load
     balancer's rotation).
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
