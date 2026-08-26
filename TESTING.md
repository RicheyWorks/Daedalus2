# Daedalus2 Testing Strategy — Reactor Gap Audit

*Originally audited 2026-07-28 (347 tests). Refreshed 2026-08-26 against the
working tree at `RicheyWorks/Daedalus2` (Spring Boot 4.1.0, **734** reactor
test methods, plus 24 in `examples/*`). Counts are `@Test` /
`@ParameterizedTest` methods; parameterized tests expand further at runtime.*

## 1. Where the suite stands

| Module | 2026-07-28 | 2026-08-26 | Assessment |
|---|---|---|---|
| daedalus-core | 203 | 313 | Strong — property tests, awkward-shape sweeps, structural roster guards |
| daedalus-server | 78 | 378 | Slice coverage, real-context smokes, WebSocket/STOMP on the wire, concurrency |
| daedalus-plugin-runtime | 16 | 26 | Lifecycle, JAR discovery, unload, `SpringPluginContext` |
| daedalus-plugin-api | 7 | 12 | Manifest guards plus SPI lifecycle/event contracts |
| daedalus-desktop | 4 | 18 | `DesktopWork` + `DesktopWalk` + `DesktopPaint`; FXML stays launch-only |
| examples/* (4 modules) | 22 | 24 | All four run in CI after the reactor `install` |

What the suite already does well, and should keep doing:

- **Hostile fixtures are institutionalized.** `SolverBraidedMazePropertyTest` runs all 10 solvers on braided mazes where "found a path" and "found the best path" diverge; `GeneratorConnectivityTest` sweeps spanning-tree generators across degenerate grid shapes. This is the direct product of the four bugs that shipped behind easy fixtures — don't let new tests regress to comfortable squares and perfect mazes.
- **The smoke test earns its keep.** `ApplicationSmokeTest` boots the real context on a real port because 267 green slice tests missed a broken `/v3/api-docs` and a 503 health endpoint. Its contract-paths list is the right shape: a subset assertion that catches silent loss without punishing addition.
- **Regression tests are proven against pre-fix code.** The Trémaux test fails 21/80 on the old implementation. Keep requiring this for every new regression test.
- **Cross-cutting concerns get layered coverage.** Rate limiting has five test classes spanning unit (key resolution, naming), behavior (eviction), and HTTP (MockMvc) — a good template for any new middleware.

## 2. Gaps

Closed items stay here so the audit cannot quietly reopen. Open items are unmarked.

### ~~P1 — CI silently skips three example modules~~ — CLOSED 2026-07-31

`.github/workflows/ci.yml` builds the reactor, then `examples/biome-plugin`, then the
remaining three (`loadbalancer-topology`, `dungeon-layout`, `benchmark-harness`) after
`install` so their poms resolve from `~/.m2`.

### ~~P1 — No end-to-end WebSocket/STOMP test~~ — CLOSED 2026-07-31

`WebSocketSmokeTest` constructs a real `WebSocketStompClient` / `StompSession`. Follow-on
harnesses (`WebSocketOwnershipSmokeTest`, `WebSocketForgerySmokeTest`,
`WebSocketProdHandshakeTest`) pin authorization, client `SEND` refusal, and prod CONNECT.

### ~~P2 — Roster guards are size tripwires, not completeness checks~~ — CLOSED 2026-07-31

`PackageScan` enumerates concrete implementations on the test classpath.
`GeneratorConnectivityTest#everyConcreteGeneratorInThePackageIsOnTheRoster` and
`SolverBraidedMazePropertyTest#everyConcreteSolverInThePackageIsOnTheRoster` fail if a
new algorithm is added to the package and omitted from the roster. `DungeonGenerator` is
the one documented exclusion.

### ~~P2 — Coverage is reported but never enforced~~ — DONE, then audited again

The `jacoco:check` execution landed as prescribed: per-module floors pinned a few points under
measured coverage, "raising it as coverage rises".

**Nobody raised it as coverage rose.** Audited 2026-07-31, after two roadmaps' worth of tests:

| module | floor was | actual | slack |
|---|---|---|---|
| daedalus-server | 0.79 | 0.910 | **+12.0 pts** |
| daedalus-plugin-api | 0.00 | 0.130 | no guard at all |
| daedalus-desktop | 0.00 | 0.105 | no guard at all |
| daedalus-core | 0.87 | 0.901 | +3.1 pts |
| daedalus-plugin-runtime | 0.84 | 0.870 | +3.0 pts |

Server coverage could have fallen by a ninth of the codebase before the build said a word. The
instruction "raise it as coverage rises" was correct and, like most conventions that depend on
someone remembering, it was not followed — which is the same failure the config and rate-limit
audits found in their own areas.

**Fix, applied:** the rule now carries a **maximum** as well as a minimum. Drift more than
`jacoco.check.headroom` (3 points) above the floor and the build fails asking for the bump. That
makes the ratchet mechanical instead of aspirational; the cost is that improving coverage
occasionally means a one-line pom edit, paid by the person who improved it rather than by
whoever regresses it later. Both directions are proven by `mutants/ratchetteeth.py`.

Floors as of 2026-08-26 (not 0.00 exemptions):

| module | floor | ceiling |
|---|---|---|
| daedalus-server | 0.93 | 0.96 |
| daedalus-core | 0.90 | 0.93 |
| daedalus-plugin-runtime | 0.84 | 0.87 |
| daedalus-plugin-api | 0.96 | 0.99 |
| daedalus-desktop | 0.28 | 0.31 |

Parent and module pom comments that still said "visible 0.00 exemption" were corrected on
2026-08-26. The 0.00 figures above are the July audit, not the current poms.

### ~~P2 — Untested classes in the server and runtime~~ — CLOSED 2026-07-31

- **`PluginController`** — `PluginControllerTest` slice covers the list/describe surface.
- **`SpringPluginContext`** — `SpringPluginContextTest` pins fail-fast `bean()` semantics.
- **`MazeWebSocketController`** — covered by the WebSocket smokes above, plus
  `MazeWebSocketControllerPluginFailedTest` and `MazeWebSocketMutationBridgeTest`.

Host plugin *shutdown* (the destroy-method half of `PluginConfig`) is pinned by
`PluginHostShutdownTest` (2026-08-26). Boot was already pinned by `PluginSpiEndToEndTest`.

### ~~P3 — GameSessionService under concurrency~~ — CLOSED 2026-07-31

`GameSessionServiceConcurrencyTest` hammers the per-session lock. Moves are check-then-act
and the lock is the intended semantics, not `ConcurrentHashMap` alone.

### P3 — Desktop: `MainController` is still the untested core

Policy is written (ADR-003): thin JavaFX shell, no TestFX. The 2026-07-31 FX-thread freeze
moved generation/solve into `DesktopWork` (6 tests). Launcher + theme add 4 more.

What remains: `MainController` (~393 LOC) still owns rendering, movement, and FXML glue,
with zero tests. The module floor is 0.28 / 0.31 after DesktopWalk / DesktopPaint.
FXML wiring is still launch-only. Keep pushing logic that can leave the toolkit
into testable helpers; do not add TestFX.

## 3. What NOT to add

- **More perfect-maze or square-grid fixtures.** The suite's whole immune system is built on hostile shapes; new tests should draw fixtures from the braided/awkward-shape helpers that already exist.
- **Per-SEND JWT re-verification tests.** `nonConnectFramesPassThroughUntouched` documents a deliberate design (authenticate at CONNECT, not per frame). Don't add tests that would enshrine the opposite until session-ownership work deliberately changes the design.
- **Benchmark assertions in CI.** The staleness lesson from ADR-002 applies: performance claims need a swept, controlled harness, not a CI assert that flakes on runner noise. `benchmark-harness` tests should pin correctness of the harness, never latency numbers.
- **Mutation testing as a gate.** `mutants/` is a local proof that tests have teeth. Too slow for every push; optional curiosity, not process.
- **New `contains(...)` or leftover `indexOf` body pins in `WebUiSmokeTest`.** That class is a boot-and-serve contract. Leftover-state and feature regressions belong in `sweep/` (`api-sweep.py` runs in CI against a test-profile server; `ui-sweep.js` is the local Playwright pass). The leftover `indexOf("async function play")` mirror was retired 2026-08-26. Leftover function-name `contains` pins were dropped the same day. Do not add either back.

## 4. Suggested order of work

1. ~~`ci.yml`: build+test all four example modules~~ — done.
2. ~~`WebSocketSmokeTest`~~ — done; ownership / forgery / prod handshake followed.
3. ~~Structural roster guards~~ — done (`PackageScan`).
4. ~~`PluginController` slice + `SpringPluginContext` unit test~~ — done.
5. ~~JaCoCo ratchet thresholds~~ — done, then re-audited: the floors had gone up to 12 points stale, so the rule gained a ceiling. 2026-08-26: pom comments no longer claim a 0.00 exemption.
6. ~~GameSessionService concurrency test~~ — done.
7. ~~Desktop: extract more of `MainController` into testable helpers~~ — walk rules live in `DesktopWalk`; letterbox / path tiles / player disc live in `DesktopPaint` (2026-08-26). FXML wiring stays launch-only (ADR-003).
8. Keep `TESTING.md` dated when the standings table moves. A strategy doc that describes last month's gaps is itself a gap.
9. ~~Stop growing `WebUiSmokeTest`; add a real API sweep in CI~~ — done 2026-08-26. `sweep/api-sweep.py` now fails the job on a failed check. Playwright `ui-sweep.js` stays local. Leftover body pins and leftover function-name `contains` pins were retired the same day.
10. ~~Windows CI for plugin-host JAR-lock~~ — done 2026-08-26. `ci.yml` runs `PluginHostShutdownTest` on `windows-latest`.

Every new regression test in any of the above follows the house rule: replay it against the pre-fix code (or a deliberately broken variant) once, to prove it has teeth.
