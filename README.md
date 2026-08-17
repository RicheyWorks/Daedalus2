# Daedalus

[![CI](https://github.com/RicheyWorks/Daedalus2/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/RicheyWorks/Daedalus2/actions/workflows/ci.yml)
![Coverage](.github/badges/jacoco.svg)

A multi-module Java engine for procedural maze and graph generation, with a
plugin runtime, a Spring Boot server (REST + WebSocket), and an optional
JavaFX desktop client.

The core is intentionally framework-free — `daedalus-core` has no Spring, JPA,
Jackson, or web dependencies — so the engine can be embedded in anything from
a load balancer to a research notebook without dragging Tomcat along. The
Spring Boot server and JavaFX desktop are layered on top as optional hosts.

## At a glance

- **23 generator algorithms** — Aldous-Broder, Archimedes (spiral), Binary
  Tree, Borůvka's, Chaos Mode (multi-generator bands), Dungeon (BSP rooms +
  corridors), Eller's, Gauss, Growing Tree, Hilbert Curve, Hunt-and-Kill,
  Kraken (Eden growth), Kruskal's (randomised), Lightning, Morton Curve
  (Z-order), Oldest-Pick, Prim's (randomised), Weighted Prim's (true MST),
  Recursive Backtracker, Recursive Division, Sidewinder, Turing (state
  machine), Wilson's.
- **10 solver algorithms** — A\*, BFS, Bidirectional BFS, Dead-End Filling,
  DFS, Dial (bucket-queue Dijkstra), Dijkstra, IDA\*, Trémaux, Wall Follower.
- **A graph seam, not just a grid** — solvers and analysis run against a
  `Graph` interface with dense integer node ids and allocation-free adjacency,
  so the engine routes over any topology rather than only a rectangular maze.
  See [`docs/adr/ADR-001`](./docs/adr/ADR-001-graph-engine-seam.md).
- **Pluggable** — third-party JARs can contribute generators, solvers, themes,
  and event listeners through a Spring-free SPI; loaders are tracked and
  closed cleanly on shutdown (no Windows file-locks, no metaspace bloat).
  A plugin can **add** an algorithm, never replace one: ids are claimed once
  and a collision fails that plugin rather than shadowing the incumbent. Until
  2026-07-31 `register` was a bare map `put`, so any JAR in the plugins
  directory could declare `id() == "recursive-backtracker"` and become it —
  silently, irreversibly, and taking the daily challenge, campaign stages and
  every seeded reproduction with it. Unloading is symmetric: a stopped plugin's
  algorithms are removed from the registries, which until the same date they
  were not — closing a classloader does not unload its classes, so a "stopped"
  plugin stayed listed and callable. `unregister` refuses built-ins, because a
  removal path reachable from teardown must not be able to delete a shipped
  algorithm.
- **Java 21**, **Spring Boot 4.1**, **JavaFX 21**.
- **Live over the wire** — a session-scoped STOMP surface (maze state, solver
  runs, player moves, plugin failures) with `CONNECT` authentication,
  per-destination `SUBSCRIBE` authorization on owned sessions, and client
  `SEND` refused outright: the surface is broadcast-only, and with a simple
  broker on `/topic` anything less meant any connected client could publish a
  forged move frame into any session's feed (found by sending one and watching
  it arrive, 2026-07-31). A one-file vanilla-JS web UI served at `/` plays
  mazes against it, with an opt-in multiplayer flag
  (`daedalus.session.multiplayer`).
- **Deterministic across restarts, not just across a cache hit.** Same seed,
  same answer, on a process that has never seen the request before.
  `DeterminismGoldenTest` compares 23 endpoints — seeded generation, the seeded
  campaign, every analytical route, the tournament, a complexity fit and all
  nine solvers — against digests recorded by a *different JVM* and committed to
  the repo, so every build is a cross-process comparison. In-process tests
  cannot do this job: these endpoints sit behind caches keyed on their inputs,
  so the second call returns the first call's object whether the computation is
  deterministic or not.
- **Watch the algorithms think** — `?replay=true` on the solve endpoint ships
  the search's real recorded expansion order (observation via the `Graph`
  seam, never simulation); the web UI animates it and can race all ten
  solvers on one maze in a compare table with per-route previews.
- **Verified** — `mvn clean verify` passes **623 tests** across the five
  modules (core 322, server 258, plugin-runtime 26, plugin-api 7, desktop 10)
  with zero Checkstyle violations, zero SpotBugs findings, and a per-module
  JaCoCo coverage ratchet that fails the build in **both** directions — on a
  regression below the floor, and on the floor going more than 3 points stale
  as coverage rises (audited 2026-07-31: the server had drifted 12 points, so
  the one-sided version was a floor rather than a ratchet).
  [`CHANGELOG.md`](./CHANGELOG.md) records what changed and, where a decision
  was measured rather than assumed, the numbers behind it;
  [`TESTING.md`](./TESTING.md) is the strategy those tests follow.

## Modules

```
daedalus/
├── daedalus-core/             pure-Java engine: generators, solvers, model
├── daedalus-plugin-api/       SPI types (Spring-free) for plugin authors
├── daedalus-plugin-runtime/   PluginManager, PluginRegistry, JAR discovery
├── daedalus-server/           Spring Boot REST + WebSocket + Redis-optional
└── daedalus-desktop/          JavaFX desktop host (optional)
```

| Module | Depends on | What lives here |
|---|---|---|
| `daedalus-core` | SLF4J only | `MazeGrid`, `MazeGenerator`/`MazeSolver` interfaces, all 23 + 10 algorithms, `Point`/`MazeMetadata`/`MazeStats` model. No Spring, no Jackson, no JPA. |
| `daedalus-plugin-api` | core | `MazePlugin`, `PluginManifest`, `PluginLifecycle`, `PluginContext`, lifecycle events (`MazeGeneratedEvent`, `MazeSolvedEvent`, `PlayerMovedEvent`, `PluginFailedEvent`). What plugin authors implement against. |
| `daedalus-plugin-runtime` | core, plugin-api, Spring | `PluginManager` (discovery, lifecycle), `PluginRegistry`, JAR `URLClassLoader` isolation. Spring is allowed here so events can be published into a Spring `ApplicationContext`. |
| `daedalus-server` | plugin-runtime, Spring Boot, Redis (optional) | Controllers (`MazeController`, `MazeWebSocketController`, `PluginController`), DTOs in `com.daedalus.api.dto`, services (`MazeGenerationService` with Resilience4j circuit breaker, `LeaderboardService` with optional Redis backing, `GameSessionService`). |
| `daedalus-desktop` | server, JavaFX | `DaedalusLauncher` (boots Spring + JavaFX), `DaedalusPrimaryStage`, `ThemeManager`. Loads `/ui/main.fxml`. |

## Build & run

Requires Java 21+ and Maven 3.9+. From the project root:

```bash
mvn clean verify          # build all modules, run tests
```

To run the server headless:

```bash
mvn -pl daedalus-server -am spring-boot:run
# or after a build:
java -jar daedalus-server/target/daedalus-server-1.0.0-SNAPSHOT-exec.jar
```

(Note the `-exec` classifier — see `CHANGELOG.md` for why this matters in
multi-module Spring Boot setups.)

To run the JavaFX desktop client (boots Spring first, then opens the UI):

```bash
mvn -pl daedalus-desktop -am javafx:run
```

Default server port is `8080` (override with `SERVER_PORT`). Default profile
is `dev` (in-memory leaderboard, no Redis required); flip to `prod` when
deploying:

```bash
SPRING_PROFILES_ACTIVE=prod DAEDALUS_REDIS_ENABLED=true \
  mvn -pl daedalus-server -am spring-boot:run
```

## REST API

All endpoints are mounted under `/api/v1` (versioned 2026-05-05 ahead of any
public consumers).

| Method | Path | Auth (prod) | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | public | Exchange admin credentials for a JWT |
| `GET` | `/api/v1/algorithms` | public | List every registered generator and solver |
| `POST` | `/api/v1/maze/generate` | required | Generate a maze (`GenerateRequest` → `GenerateResponse`) |
| `GET` | `/api/v1/maze/daily` | public | Today's shared challenge — same maze for everyone until midnight UTC (ADR-006) |
| `GET` | `/api/v1/maze/{id}` | public | Fetch a previously-generated maze's metadata + tile grid |
| `POST` | `/api/v1/maze/{id}/live?ticks=30` | required | Bring the maze to life: bounded erosion ticks mutate it in place (ADR-006). Optional `seal=` in `[0, 1]` also closes extra passages without disconnecting anyone (ADR-008; default 0 = v1) |
| `POST` | `/api/v1/maze/{id}/solve/{solverId}` | required | Run a solver against a stored maze. Answers **422** if the solver spends its node budget — IDA\* does this on dungeons from ~21×21 up, where the unguarded search took 16 s and worse (ADR-007 postscript) |
| `POST` | `/api/v1/maze/{id}/session?player=...` | required | Open a play session (returns `SessionResponse`) |
| `POST` | `/api/v1/session/{id}/move` | required | Move the player one step (`MoveRequest`). Rate-limited on the `sessionMove` budget — 1200/min, the same as the fog-of-war agent, because it is the same shape of traffic |
| `POST` | `/api/v1/session/{id}/join` | required | Add another player to an open session |
| `POST` | `/api/v1/maze/{id}/agent?steps=...` | required | Open a fog-of-war walk: the agent sees only its cell's openings (ADR-006) |
| `POST` | `/api/v1/agent/{id}/step?direction=NORTH` | required | Take one blind step — validated against the maze's *live* grid |
| `GET` | `/api/v1/agent/{id}` | public | Re-poll the agent's view without spending a step |
| `POST` | `/api/v1/maze/{id}/traffic` | required | Track traffic: occupancy raises cell costs, which decay each pulse (ADR-006) |
| `GET` | `/api/v1/maze/{id}/fingerprint` | required | Structural signature + which generator most likely made it (ADR-007) |
| `GET` | `/api/v1/complexity?generator=&metric=` | required | Measure a generator's real growth curve and report its big-O with an R² (ADR-007) |
| `GET` | `/api/v1/complexity/metrics` | required | Which metrics `/complexity` can be asked for |
| `GET` | `/api/v1/maze/{id}/tour?count=` | required | Waypoints plus the provably optimal route collecting them all (ADR-007) |
| `GET` | `/api/v1/session/{id}/tour` | public | Server-observed progress against that optimum |
| `GET` | `/api/v1/campaign?seed=` | required | A deterministic, difficulty-graded ladder of stages; omit the seed for today's (ADR-006). The finale declares `hardening` so the client starts `/live?seal=` (ADR-008) |
| `POST` | `/api/v1/maze/breed?a=&b=&seed=` | required | Crossbreed two equal-sized mazes into a connected child (ADR-006) |
| `GET` | `/api/v1/session/{id}` | public | Read-only session snapshot — the spectator entry point (`#session=` permalink) |
| `GET` | `/api/v1/maze/{id}/analysis` | required | Structural analysis: unit-capacity min-cut chokepoints, dead ends, route length (ADR-006). Real capacities live on `MazeFlow.minCut(..., PassageCapacity)` (ADR-009) — a maze has no bandwidth of its own |
| `GET` | `/api/v1/maze/{id}/distance-field` | required | Every cell's walking distance from the goal (or start), for a heat map. Unreachable cells report -1; payload-capped (ADR-007) |
| `GET` | `/api/v1/maze/{id}/heuristic-lens?heuristic=` | required | The three bands that explain A\*'s expansions — must expand, tie decides, never touched — plus a live admissibility check (ADR-007) |
| `GET` | `/api/v1/tournament?generator=&size=&mazes=&braid=` | required | Rank every solver over a sample with Student-t intervals, report which pairs are statistically indistinguishable, and name the adversarial seed where the leader does worst (ADR-007) |
| `GET` | `/api/v1/maze/{id}/sanctuaries` | required | k-center safe points, the covering radius, and the cell served worst (ADR-007) |
| `GET` | `/api/v1/maze/{id}/hardest-route` | required | Longest simple route vs shortest, the detour between them, and the maze's loop count. On a perfect maze the two are equal by mathematics and the response says so (ADR-007) |
| `GET` | `/api/v1/maze/{id}/ghost` | public | The maze's best completed run as a timed recording — the UI replays it as a ghost racer |
| `GET` | `/api/v1/leaderboard?n=20&maze={id}&generator={id}` | public | Top-N leaderboard — `maze=` scopes to one maze's board (the daily's partition), `generator=` to one algorithm's; `maze` wins if both are given |
| `GET` | `/api/v1/plugins` | required | Currently-loaded plugins (`PluginInfo`) |
| `GET` | `/api/v1/plugins/describe` | required | Human-readable plugin tree |

In dev / test profiles every endpoint is open. The "Auth (prod)" column applies when
`spring.profiles.active=prod` (see `ProdSecurityConfig`), and it is **executable**:
`ProdAuthPostureTest` boots a prod context, drives an unauthenticated request at every row above,
and fails the build if the answer disagrees with the word in that column — in either direction,
and also if a row is missing or an endpoint exists that no row covers. The table is not
documentation of the security posture; it is one of the two sources the posture is checked
against. It earned that on its first run: four endpoints marked `public` here were being refused
in prod, which meant the spectator permalink, the ghost racer and the agent re-poll did not work
there at all.

### Errors

Every error this API produces is an [RFC 7807](https://www.rfc-editor.org/rfc/rfc7807) problem
detail, served as `application/problem+json` and carrying `type`, `title`, `status`, `detail` and
`instance`. Some carry more: validation failures add a `fieldErrors` map, a 429 adds `limiter`
and `retryAfterSeconds` alongside the `Retry-After` header, and a 405 adds `allowed` alongside
`Allow`.

```jsonc
// POST /api/v1/maze/generate  {"generatorId": "recursive-backtracer", ...}
{
  "type":     "https://daedalus.dev/problems/unknown-algorithm",
  "title":    "Unknown generator",
  "status":   404,
  "detail":   "No generator is registered with id 'recursive-backtracer'",
  "instance": "/api/v1/maze/generate",
  "kind":     "generator",
  "requested":"recursive-backtracer",
  "known":    ["aldous-broder", "archimedes-spiral", "binary-tree", "..."]
}
```

The `type` URIs are stable identifiers, not fetchable documents: `validation`,
`malformed-request`, `rate-limited`, `unknown-algorithm`, `not-found`, plus the capacity and
budget types. Match on `type`, not on `detail` — `detail` is written for a human.

There are no exceptions — including the 404 for a resource that is not here. That one is worth a
note, because the empty body it used to send was hiding real distinctions. `GET /maze/{id}/ghost`
now tells you whether the *maze* is gone or whether the maze is fine and nobody has completed a
run on it yet; `POST /session/{id}/move` tells you whether the *session* is unknown or whether the
session is open and its maze has been evicted. Those pairs call for opposite reactions and used to
send identical replies. One 404 deliberately stays uninformative: `join` with the multiplayer flag
off answers exactly what an unknown session answers, so the endpoint reads as absent rather than
disabled.

This is enforced, not described. `ErrorContractTest` drives twenty-one failure modes at a booted
server, and — more importantly — generates a wrong-verb and a malformed-path-variable request for
every mapping it finds in the controller sources, failing the build on any 4xx or 5xx that comes
back without a `type`. Before it existed, a mistyped `generatorId` answered **500**.

### Auth flow

```bash
# 1. Exchange admin credentials for a JWT.
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"your-password"}'
# → { "token": "eyJhbGc...", "expiresAt": "2026-05-06T12:34:56Z" }

# 2. Use it on protected calls.
curl -X POST http://localhost:8080/api/v1/maze/generate \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -d '{"generatorId":"binary-tree","rows":20,"cols":20}'
```

To configure the admin credentials in prod, set two env vars:

```bash
export DAEDALUS_JWT_SECRET="$(openssl rand -base64 32)"
export DAEDALUS_ADMIN_PASSWORD_BCRYPT='$2a$10$...'   # bcrypt hash, not plaintext
# Optional:
export DAEDALUS_ADMIN_USER=admin
export DAEDALUS_JWT_TTL_MINUTES=60
```

To produce the bcrypt hash, the simplest way is a one-line scratch program with Spring's
`BCryptPasswordEncoder`:

```java
System.out.println(new BCryptPasswordEncoder().encode("your-password"));
```

DTOs live in `com.daedalus.api.dto` and have Javadoc on every field. A
TypeScript mirror of the DTOs is in [`Code/daedalus-api-dtos.ts`](./Code/daedalus-api-dtos.ts).

## WebSocket / STOMP topics

Real-time updates are pushed over STOMP. Connect at `/ws` and subscribe to:

| Topic | When it fires | Frame type |
|---|---|---|
| `/topic/maze/{mazeId}/state` | Maze finishes generating | `GeneratedFrame` |
| `/topic/maze/{mazeId}/solver` | Solver finishes a run | `SolvedFrame` |
| `/topic/session/{sessionId}/player` | Player moves | `MoveFrame` |
| `/topic/plugins/failures` | A plugin throws in any lifecycle phase | `PluginFailedFrame` |

The `PluginFailedFrame` topic is intentional: operators can surface plugin
failures as toasts / banner alerts instead of grepping logs.

## Writing a plugin

Implement `com.daedalus.plugin.MazePlugin` (or extend `AbstractPlugin`),
declare it in `META-INF/services/com.daedalus.plugin.MazePlugin`, drop the
JAR into the plugin directory (`daedalus.plugins.directory`, defaults to
`/var/daedalus/plugins` in prod). The runtime discovers it via
`ServiceLoader`, isolates it in its own `URLClassLoader`, and drives it
through `init` → `registerAlgorithms` → `start` on boot, `stop` on shutdown.

Failures at any phase publish `PluginFailedEvent`, which the server
re-emits to `/topic/plugins/failures`. The runtime closes every external
classloader in `shutdownAll()`, so JARs aren't kept locked open and you
can swap a plugin without restarting the server.

See `daedalus-plugin-api/src/main/java/com/daedalus/plugin/AbstractPlugin.java`
for the easiest starting point. The
[`examples/biome-plugin/`](./examples/biome-plugin/) module is a worked
end-to-end example: two themed generators (`forest-biome`, `desert-biome`)
plus a programmatic `MazeGeneratedEvent` subscriber. Build it with
`mvn -f examples/biome-plugin/pom.xml clean package`, or run it against a
live server in one command with `./examples/run-with-biome.sh`.

## Worked examples

Four standalone modules, none of them reactor children — the parent pom lists
production modules only, so each is built and run on its own.

| module | what it shows |
|---|---|
| [`examples/biome-plugin`](./examples/biome-plugin/) | Writing a plugin: two themed generators plus an event subscriber, loaded from a JAR. |
| [`examples/loadbalancer-topology`](./examples/loadbalancer-topology/) | Daedalus as the topology and analysis engine behind a load balancer — generate a topology, measure unit connectivity and capacitated bandwidth (ADR-009), place facilities with k-center, assign a batch of requests under replica capacity (ADR-010), and route with cost in `g` rather than in the heuristic. |
| [`examples/dungeon-layout`](./examples/dungeon-layout/) | Daedalus as the spatial layer under a narrative game engine — BSP rooms, level depth, the hardest route, and treasure placement, emitted as named locations. |
| [`examples/benchmark-harness`](./examples/benchmark-harness/) | Times every generator and solver and writes `docs/benchmarks/benchmark-<date>.csv`. Run it by hand on a machine whose numbers you trust; timings are machine-specific and are deliberately not asserted in CI. |

```bash
mvn -f examples/loadbalancer-topology/pom.xml clean test
mvn -f examples/dungeon-layout/pom.xml exec:java
```

## Testing

```bash
mvn clean verify              # all five modules
mvn -pl daedalus-server test  # one module
```

Test inventory — **623 tests across 127 files, all green** (322 core, 7 plugin-api, 26
plugin-runtime, 258 server, 10 desktop) as of 2026-07-31:

| Module | Highlights |
|---|---|
| `daedalus-core` | `PerfectMazePropertyTest` — every generator output is a spanning tree (perfect-maze contract) |
| `daedalus-plugin-api` | `PluginManifestNullGuardTest` — manifest required-field guards |
| `daedalus-plugin-runtime` | `PluginManagerLifecycleTest`, `PluginManagerJarDiscoveryTest` — boot/shutdown ordering, classloader cleanup, `PluginFailedEvent` publication |
| `daedalus-server` | `GeneratorInvariantFuzzTest` — **every registered generator**, taken from the live registry rather than a list, held to the universal invariants across 11 shapes × 2 seeds (506 generations, zero violations); `MazeGenerationServiceFallbackTest` (Resilience4j circuit breaker), `RedisConfigConditionalTest` (on/off toggle), `SecurityConfigProfileTest` (profile-aware filter chain), `MazeControllerGeneratorIdTest`, `MazeWebSocketControllerPluginFailedTest` |
| `daedalus-desktop` | `DesktopWorkTest` — generation and solve run off the JavaFX thread as plain callables, so they are testable without a headless toolkit (measured: hunt-and-kill takes 1101 ms at 128×128, IDA\* 1783 ms, all of it frozen UI before this); `ThemeManagerTest`, `DaedalusLauncherTest` |

## Workspace layout

Beyond the five Maven modules:

```
Audit/       Vision-style audit + integration ideas (Grok, May 6)
Code/        Sample integrations: HilbertLoadBalancer.java, daedalus-api-dtos.ts
docs/adr/    Architecture decision records (graph seam; living mazes; theory-as-product; hardening)
docs/        benchmarks/ (harness output), evaluations/ (standalone measurement code)
examples/    Four worked examples — see "Worked examples" above
PDFs/        Auto-generated reference docs (server, runtime, desktop, core, generators, overview)
Vision/      Forward-looking direction docs
_migration/  Historical artefacts from the multi-module split + earlier audits
```

`AUDIT_RECOMMENDATIONS_2026-05-05.md` is the canonical audit-verification
record (build-verified). `CHANGELOG.md` tracks concrete changes to the
working tree.

## Operational notes

- **Redis is optional — and disabling it no longer reports the app as
  unhealthy.** `daedalus.redis.enabled=false` (the dev default) uses an
  in-memory leaderboard; set it `true` for the Redis-backed implementation.
  `RedisConfig` is `@ConditionalOnProperty` so the app boots cleanly either
  way. **Note if you deployed before 2026-07-19:** Boot's stock Redis health
  indicator registered regardless of that flag, so `/actuator/health` answered
  **503** on a perfectly healthy instance running the in-memory backend —
  which a load balancer or Kubernetes readiness probe reads as "take this pod
  out of rotation". `management.health.redis.enabled` is now bound to
  `${daedalus.redis.enabled:false}`, so the check applies exactly where Redis
  is actually required.
- **Health is a report, not a veto.** `/actuator/health` carries a
  `pluginSubsystem` component with `loadedPlugins`, `failedPlugins` and a
  `lastFailure` description. It never reports DOWN by design: a broken
  *optional* plugin must not pull a serving instance out of rotation, since
  the engine, REST API and solver registry all keep working without it.
- **Rate limiting is per-caller and bounded.** Each caller (authenticated
  subject, else client IP) gets its own bucket. The bucket store is capped by
  `daedalus.ratelimit.max-keys` (default 10 000) and expires on
  `daedalus.ratelimit.idle-ttl` (default 10 min), so a caller minting many
  keys costs bounded memory. Eviction can never refund permits early — each
  bucket's effective TTL is raised to at least its own limit-refresh period.
  Set `daedalus.ratelimit.trust-forwarded-header=true` **only** behind a proxy
  that overwrites `X-Forwarded-For`; otherwise a client can spoof it and mint
  a fresh bucket per forged IP.
- **WebSocket connections are authenticated in prod.** The STOMP `CONNECT`
  frame must carry `Authorization: Bearer <token>`; the JWT subject becomes
  the session principal. Outside `prod` a token is optional, but an *invalid*
  token is rejected in every profile. Note this is authentication only —
  destinations are not yet scoped per user, so any authenticated client can
  subscribe to any topic (see BACKLOG.md).
- **The generation service is wrapped in a Resilience4j circuit breaker.**
  When it trips, a cached binary-tree maze is returned and the response
  reports the actual generator id (not the requested one) so clients,
  leaderboards, and `MazeGeneratedEvent` consumers all see the truth.
- **Security split by profile.** Dev / test / desktop use a permissive
  `SecurityConfig` (every endpoint open) — this matches the JavaFX client's
  needs and keeps `mvn test` simple. Prod uses `ProdSecurityConfig`: JWT
  bearer-token auth on write endpoints, plugin introspection, and the
  WebSocket; reads stay open; actuator-restricted endpoints require a token;
  Swagger UI is denied. See the auth-flow section above for the exact env-var
  contract.

## License

MIT — see [`LICENSE`](./LICENSE) for the full text. Permissive: anyone can
use, modify, distribute, or sell the software, including in proprietary work,
provided the copyright notice and license 