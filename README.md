# Daedalus

[![CI](https://github.com/RicheyWorks/Daedalus2/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/RicheyWorks/Daedalus2/actions/workflows/ci.yml)

A multi-module Java engine for procedural maze and graph generation, with a
plugin runtime, a Spring Boot server (REST + WebSocket), and an optional
JavaFX desktop client.

The core is intentionally framework-free — `daedalus-core` has no Spring, JPA,
Jackson, or web dependencies — so the engine can be embedded in anything from
a load balancer to a research notebook without dragging Tomcat along. The
Spring Boot server and JavaFX desktop are layered on top as optional hosts.

## At a glance

- **19 generator algorithms** — Aldous-Broder, Archimedes (spiral), Binary
  Tree, Borůvka's, Eller's, Gauss, Growing Tree, Hilbert Curve, Hunt-and-Kill,
  Kraken (Eden growth), Kruskal's (randomised), Lightning, Morton Curve
  (Z-order), Prim's (randomised), Recursive Backtracker, Recursive Division,
  Sidewinder, Turing (state machine), Wilson's.
- **9 solver algorithms** — A\*, BFS, Bidirectional BFS, Dead-End Filling,
  DFS, Dijkstra, IDA\*, Trémaux, Wall Follower.
- **Pluggable** — third-party JARs can contribute generators, solvers, themes,
  and event listeners through a Spring-free SPI; loaders are tracked and
  closed cleanly on shutdown (no Windows file-locks, no metaspace bloat).
- **Java 21**, **Spring Boot 3.3**, **JavaFX 21**.
- **Audit-clean** — see [`AUDIT_RECOMMENDATIONS_2026-05-05.md`](./AUDIT_RECOMMENDATIONS_2026-05-05.md)
  for the verification record. `mvn clean verify` passes 25 / 25 tests across
  all modules.

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
| `daedalus-core` | SLF4J only | `MazeGrid`, `MazeGenerator`/`MazeSolver` interfaces, all 19 + 9 algorithms, `Point`/`MazeMetadata`/`MazeStats` model. No Spring, no Jackson, no JPA. |
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

| Method | Path | Description |
|---|---|---|
| Method | Path | Auth (prod) | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | public | Exchange admin credentials for a JWT |
| `GET` | `/api/v1/algorithms` | public | List every registered generator and solver |
| `POST` | `/api/v1/maze/generate` | required | Generate a maze (`GenerateRequest` → `GenerateResponse`) |
| `GET` | `/api/v1/maze/{id}` | public | Fetch a previously-generated maze's metadata + tile grid |
| `POST` | `/api/v1/maze/{id}/solve/{solverId}` | required | Run a solver against a stored maze |
| `POST` | `/api/v1/maze/{id}/session?player=...` | required | Open a play session (returns `SessionResponse`) |
| `POST` | `/api/v1/session/{id}/move` | required | Move the player one step (`MoveRequest`) |
| `GET` | `/api/v1/leaderboard?n=20` | public | Top-N leaderboard |
| `GET` | `/api/v1/plugins` | required | Currently-loaded plugins (`PluginInfo`) |
| `GET` | `/api/v1/plugins/describe` | required | Human-readable plugin tree |

In dev / test profiles every endpoint is open. The "Auth (prod)" column applies when
`spring.profiles.active=prod` (see `ProdSecurityConfig`).

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

## Testing

```bash
mvn clean verify              # all five modules
mvn -pl daedalus-server test  # one module
```

Test inventory (1,194 lines across 12 files, all green as of 2026-05-05):

| Module | Highlights |
|---|---|
| `daedalus-core` | `PerfectMazePropertyTest` — every generator output is a spanning tree (perfect-maze contract) |
| `daedalus-plugin-api` | `PluginManifestNullGuardTest` — manifest required-field guards |
| `daedalus-plugin-runtime` | `PluginManagerLifecycleTest`, `PluginManagerJarDiscoveryTest` — boot/shutdown ordering, classloader cleanup, `PluginFailedEvent` publication |
| `daedalus-server` | `MazeGenerationServiceFallbackTest` (Resilience4j circuit breaker), `RedisConfigConditionalTest` (on/off toggle), `SecurityConfigProfileTest` (profile-aware filter chain), `MazeControllerGeneratorIdTest`, `MazeWebSocketControllerPluginFailedTest` |
| `daedalus-desktop` | `ThemeManagerTest`, `DaedalusLauncherTest` |

## Workspace layout

Beyond the five Maven modules:

```
Audit/       Vision-style audit + integration ideas (Grok, May 6)
Code/        Sample integrations: HilbertLoadBalancer.java, daedalus-api-dtos.ts
examples/    Worked example plugins (biome-plugin + run-with-biome.sh)
PDFs/        Auto-generated reference docs (server, runtime, desktop, core, generators, overview)
Vision/      Forward-looking direction docs
_migration/  Historical artefacts from the multi-module split + earlier audits
```

`AUDIT_RECOMMENDATIONS_2026-05-05.md` is the canonical audit-verification
record (build-verified). `CHANGELOG.md` tracks concrete changes to the
working tree.

## Operational notes

- **Redis is optional.** `daedalus.redis.enabled=false` (the dev default)
  uses an in-memory leaderboard. Set `daedalus.redis.enabled=true` for the
  Redis-backed implementation. The `RedisConfig` Spring config is
  `@ConditionalOnProperty` so the app boots cleanly either way.
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
provided the copyright notice and license terms travel with copies. No
warranty.
