# Daedalus2 Testing Strategy — Reactor Gap Audit

*Audited 2026-07-28 against the working tree at `RicheyWorks/Daedalus2` (main, Spring Boot 4.1.0, 347 tests).*

## 1. Where the suite stands

The reactor's test distribution, by module (counting `@Test` / `@ParameterizedTest` methods; parameterized tests expand further at runtime):

| Module | Test methods | Assessment |
|---|---|---|
| daedalus-core | 203 | Strong — property tests, awkward-shape sweeps, regression tests with verified teeth |
| daedalus-server | 78 | Good slice coverage + one real-context smoke test; **no WebSocket integration path** |
| daedalus-plugin-runtime | 16 | Lifecycle + jar discovery covered; `SpringPluginContext` untested |
| daedalus-plugin-api | 7 | Adequate for a contracts module |
| daedalus-desktop | 4 | Near-zero — needs a deliberate policy, not necessarily more tests |
| examples/* (4 modules) | 22 | Written, meaningful — but **three of four never run in CI** |

What the suite already does well, and should keep doing:

- **Hostile fixtures are institutionalized.** `SolverBraidedMazePropertyTest` runs all 10 solvers on braided mazes where "found a path" and "found the best path" diverge; `GeneratorConnectivityTest` sweeps all 21 spanning-tree generators across degenerate grid shapes. This is the direct product of the four bugs that shipped behind easy fixtures — don't let new tests regress to comfortable squares and perfect mazes.
- **The smoke test earns its keep.** `ApplicationSmokeTest` is the only test that boots the real context on a real port, and it exists because 267 green slice tests missed a broken `/v3/api-docs` and a 503 health endpoint. Its contract-paths list is the right shape: a subset assertion that catches silent loss without punishing addition.
- **Regression tests are proven against pre-fix code.** The Trémaux test fails 21/80 on the old implementation. Keep requiring this for every new regression test.
- **Cross-cutting concerns get layered coverage.** Rate limiting has five test classes spanning unit (key resolution, naming), behavior (eviction), and HTTP (MockMvc) — a good template for any new middleware.

## 2. Gaps, prioritized

### P1 — CI silently skips three example modules

`ci.yml` builds the reactor, then only `examples/biome-plugin`. The other three — `loadbalancer-topology`, `dungeon-layout`, `benchmark-harness` — hold 17 test methods that pin the claims the examples' narratives make ("executable documentation, so its claims are tested rather than printed and hoped for"), and none of them execute on any push. This is exactly the "silently rot" failure the CI file's own comment warns about, and `TopologyLabTest` has already caught one real bug (the Hilbert forest). A core API change that breaks an example today ships green.

**Fix** (one step in `ci.yml`, after the biome-plugin step):

```yaml
      - name: Build the remaining examples
        run: |
          mvn -B -ntp -f examples/loadbalancer-topology/pom.xml clean package
          mvn -B -ntp -f examples/dungeon-layout/pom.xml clean package
          mvn -B -ntp -f examples/benchmark-harness/pom.xml clean package
```

(Same ordering constraint as biome-plugin: must run after the reactor's `install` populates `~/.m2`.)

### P1 — No end-to-end WebSocket/STOMP test

Nothing in the repo constructs a `WebSocketStompClient` or `StompSession`. Concretely:

- `WebSocketConfig` is referenced by **zero** tests. The endpoint path (`/ws` + SockJS), broker prefixes (`/topic`, `/queue`, `/app`), and the registration of `StompAuthChannelInterceptor` into the inbound channel are all unverified wiring.
- `StompAuthChannelInterceptorTest` is a solid unit test of CONNECT handling, but it tests the interceptor in isolation — it cannot prove the interceptor is actually installed.
- `MazeWebSocketControllerPluginFailedTest` covers one of the four event→topic bridges; the `/topic/maze/{id}/state`, `/topic/maze/{id}/solver`, and `/topic/session/{id}/player` re-publications have no test proving a subscriber receives them.

This has the same shape as the springdoc incident: a starter/framework bump (or a one-line config change) could break the entire realtime path while every slice test stays green. It also matters for what's next — session-ownership modelling and STOMP per-destination authorization can't be test-driven without this harness existing first.

**Fix:** one `WebSocketSmokeTest` in daedalus-server, `@SpringBootTest(webEnvironment = RANDOM_PORT)`, sketch:

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class WebSocketSmokeTest {

    @LocalServerPort int port;
    @Autowired SimpMessagingTemplate stomp;   // or publish a real MazeGeneratedEvent

    @Test
    void aStompClientCanConnectSubscribeAndReceiveABrokerFrame() throws Exception {
        WebSocketStompClient client = new WebSocketStompClient(
                new SockJsClient(List.of(new WebSocketTransport(new StandardWebSocketClient()))));
        client.setMessageConverter(new MappingJackson2MessageConverter());

        StompSession session = client.connectAsync("http://localhost:" + port + "/ws",
                new StompSessionHandlerAdapter() {}).get(5, TimeUnit.SECONDS);

        BlockingQueue<PluginFailedFrame> received = new ArrayBlockingQueue<>(1);
        session.subscribe("/topic/plugins/failures", frameHandlerInto(received));

        // Publish the internal event the bridge listens for, then assert the frame arrives.
        // (Publishing the Spring ApplicationEvent, not calling the controller, tests the
        //  whole chain: event -> bridge -> broker -> wire -> client.)
        eventPublisher.publishEvent(new PluginFailedEvent(...));

        assertThat(received.poll(5, TimeUnit.SECONDS)).isNotNull();
    }
}
```

Assertions worth making in this class: connect succeeds without auth in the test profile's non-required mode; connect with a forged JWT is refused when required (proves the interceptor is *installed*, complementing the unit test); one broker frame round-trips per topic family. Async caveat: always receive through a `BlockingQueue` with a timeout — never `Thread.sleep`.

### P2 — Roster guards are size tripwires, not completeness checks

`everySolverIsCoveredByThisTest()` asserts `hasSize(10)` — a tripwire that only fires if someone remembers to bump it, which is a politer version of the same silent-omission hazard it guards against ("silent omission is exactly how Trémaux went untested"). `GeneratorConnectivityTest` has **no guard at all**: a 22nd generator added to `AlgorithmConfig` would be registered in production and never braided, never shape-swept.

**Fix:** make the guard structural. `GeneratorRegistry`'s built-in list is wired in daedalus-server's `AlgorithmConfig`, which core tests can't see — so scan the package instead:

```java
@Test
void everyConcreteGeneratorInThePackageIsOnTheRoster() throws Exception {
    // Enumerate .class files in com/daedalus/engine/generators on the test classpath,
    // keep concrete MazeGenerator implementations, and assert the roster covers them.
    Set<Class<?>> concrete = classesInPackage("com.daedalus.engine.generators").stream()
            .filter(MazeGenerator.class::isAssignableFrom)
            .filter(c -> !Modifier.isAbstract(c.getModifiers()))
            .filter(c -> c != DungeonGenerator.class)      // documented exclusion
            .collect(toSet());
    assertThat(spanningTreeGenerators()).extracting(Object::getClass)
            .containsExactlyInAnyOrderElementsOf(concrete);
}
```

Apply the same pattern to the solver roster (replacing the `hasSize(10)` bump-me). A ~15-line `classesInPackage` helper over `ClassLoader.getResources` needs no new dependency. Exclusions stay possible — they just become visible code instead of invisible absence.

### P2 — Coverage is reported but never enforced

JaCoCo runs `prepare-agent` + `report`; the only consumer is the badge. Nothing fails a build on a coverage regression, so a PR that deletes tests (or adds a large untested class) passes CI with a quietly shrinking badge.

**Fix:** add a `jacoco:check` execution with per-module ratchet thresholds. Don't invent numbers — run `mvn verify`, read the current per-module instruction coverage from the reports, and pin each module 2–3 points below its actual value (the ratchet), raising it as coverage rises. Suggested scope: enforce on daedalus-core, daedalus-plugin-runtime, and daedalus-server; explicitly exempt daedalus-desktop (see P3 policy) and daedalus-plugin-api (interfaces/events). Add exclusions for `api/dto/**` and `model/**` records if they drag the number without meaning.

### P2 — Untested classes in the server and runtime

- **`PluginController` — zero test references.** The smoke test proves `/api/v1/plugins` appears in the OpenAPI doc, not that it returns anything sane. Add a `@WebMvcTest` slice: lists registered plugins, shape of `PluginInfo`, empty-registry behavior, auth posture consistent with the other controllers.
- **`SpringPluginContext` — zero test references.** It's the seam plugins actually receive. A focused unit test: what a plugin can reach through it, and what it does when asked for something unavailable (fail fast vs. null — pin whichever is intended, since plugin authors will depend on it).
- **`MazeWebSocketController`** — three of four event bridges untested (covered by the P1 harness above; alternatively cheap `@EventListener`-invocation unit tests asserting `convertAndSend` destinations, but the integration test is worth more).

### P3 — GameSessionService under concurrency

Sessions live in a `ConcurrentHashMap`, and the WebSocket layer makes concurrent access to one session realistic (two tabs, a reconnect race). `ConcurrentHashMap` protects the map, not compound operations on a `GameSession`. Worth one targeted test only if the service has check-then-act sequences (read position → validate move → write position); if it does, a small `CountDownLatch`-gated two-thread test on the same session pins the intended semantics. If moves are atomic per call, skip it — don't write concurrency theater. This becomes P1 the moment session-ownership modelling lands, since ownership checks are exactly check-then-act.

### P3 — Desktop: pick a policy, write it down

Four test methods across launcher + theme manager. Recommended policy, worth a paragraph in the README or an ADR note rather than more tests: keep `daedalus-desktop` a thin JavaFX shell, push any logic that grows in `MainController` down into daedalus-core where the property tests live, and exclude the module from coverage enforcement. TestFX-style UI automation is not worth its flakiness for a single-developer desktop shell. The test-worthy signal to watch for: the first time a bug report is *in* desktop logic, that logic moves to core and gets tested there.

## 3. What NOT to add

- **More perfect-maze or square-grid fixtures.** The suite's whole immune system is built on hostile shapes; new tests should draw fixtures from the braided/awkward-shape helpers that already exist.
- **Per-SEND JWT re-verification tests.** `nonConnectFramesPassThroughUntouched` documents a deliberate design (authenticate at CONNECT, not per frame). Don't add tests that would enshrine the opposite until session-ownership work deliberately changes the design.
- **Benchmark assertions in CI.** The staleness lesson from ADR-002 applies: performance claims need a swept, controlled harness, not a CI assert that flakes on runner noise. `benchmark-harness` tests should pin correctness of the harness, never latency numbers.
- **Mutation testing as a gate.** A one-off PIT run on daedalus-core would be an interesting audit of the property tests (and probably a flattering one), but it's too slow for CI here. Optional curiosity, not process.

## 4. Suggested order of work

1. `ci.yml`: build+test all four example modules (~5 minutes of work, closes the biggest blind spot per keystroke).
2. `WebSocketSmokeTest` (unblocks test-driving the STOMP authorization work that's already queued).
3. Structural roster guards in `GeneratorConnectivityTest` and `SolverBraidedMazePropertyTest`.
4. `PluginController` slice test + `SpringPluginContext` unit test.
5. JaCoCo ratchet thresholds (after reading current numbers from a local `mvn verify`).
6. GameSessionService concurrency test — only if inspection finds check-then-act; otherwise defer to the session-ownership work.

Every new regression test in any of the above follows the house rule: replay it against the pre-fix code (or a deliberately broken variant) once, to prove it has teeth.
