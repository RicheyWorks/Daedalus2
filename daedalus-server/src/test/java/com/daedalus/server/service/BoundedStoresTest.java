// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.GameSession;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.Point;
import com.github.benmanes.caffeine.cache.Ticker;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;

/**
 * Every in-memory store the server accumulates into must be bounded (audit 2026-07-29).
 *
 * <p>Three stores grew without limit before this: the maze cache (one full grid per
 * generation, up to 43k/day inside the base rate limit), the session store (never evicted,
 * not even after completion), and the in-memory leaderboard (one entry per completed session,
 * forever). Same slow-leak shape the rate-limiter buckets had before their Caffeine bound
 * (BACKLOG, 2026-07-19) — this closes the remaining three at once. Each test constructs its
 * service with a tiny bound so eviction is deterministic, and each fails against the pre-fix
 * unbounded implementation.
 */
class BoundedStoresTest {

    /**
     * Caffeine evicts asynchronously (maintenance piggybacks on later cache operations), so a
     * single post-insert snapshot can overcount. Poll with a deadline; against the pre-fix
     * unbounded stores this never converges and the assertion still fails, so the teeth
     * survive the retry.
     */
    private static long survivorsWithin(List<UUID> ids, java.util.function.Function<UUID, Object> find,
                                        long bound) throws InterruptedException {
        long survivors = Long.MAX_VALUE;
        long deadline = System.nanoTime() + Duration.ofSeconds(5).toNanos();
        while (System.nanoTime() < deadline) {
            survivors = ids.stream().filter(id -> find.apply(id) != null).count();
            if (survivors <= bound) {
                break;
            }
            Thread.sleep(50);
        }
        return survivors;
    }

    /**
     * The three tests below prove eviction for three named stores. This one asks the harder
     * question: are there stores nobody wrote a test for?
     *
     * <p>Measured during the post-ADR-007 audit, there are <b>nine</b> Caffeine caches in the
     * server and three named eviction tests. All nine turned out to declare a
     * {@code maximumSize} — the rule held — but it held by everyone remembering, which is not a
     * property, it is a run of luck. This scans the source instead, so a tenth cache added next
     * month is covered the moment it exists rather than the moment someone thinks to add a test.
     * The same reason {@code GeneratorInvariantFuzzTest} is driven by the registry and
     * {@code ConfigCoverageTest} is driven by the yml.
     */
    @Test
    void everyCaffeineCacheInTheServerDeclaresAMaximumSize() throws Exception {
        java.nio.file.Path root = java.nio.file.Path.of("src/main/java");
        assertThat(java.nio.file.Files.isDirectory(root))
                .as("expected to run from the daedalus-server module directory").isTrue();

        List<String> unbounded = new ArrayList<>();
        int caches = 0;
        try (var files = java.nio.file.Files.walk(root)) {
            for (java.nio.file.Path file : files
                    .filter(f -> f.toString().endsWith(".java")).toList()) {
                String text = java.nio.file.Files.readString(file);
                int at = text.indexOf("Caffeine.newBuilder");
                while (at >= 0) {
                    caches++;
                    int end = text.indexOf(';', at);
                    String statement = end < 0 ? text.substring(at) : text.substring(at, end);
                    if (!statement.contains(".maximumSize(")) {
                        unbounded.add(file.getFileName() + ": " + statement.replaceAll("\\s+", " "));
                    }
                    at = text.indexOf("Caffeine.newBuilder", at + 1);
                }
            }
        }

        assertThat(caches).as("the scanner found no caches at all, so it is broken")
                .isGreaterThanOrEqualTo(8);
        assertThat(unbounded)
                .as("an unbounded Caffeine cache is a slow leak with a friendly API: %s", unbounded)
                .isEmpty();
    }

    /**
     * The companion question, and the one this class kept getting wrong: a cache that declares
     * {@code expireAfterAccess} is not a cache whose expiry anyone has checked.
     *
     * <p>Three separate mutation harnesses found the same defect on three separate days —
     * deleting {@code expireAfterAccess} from `GameSessionService` (08-01), from
     * {@code MazeGenerationService} (08-02) and from {@code AgentWalkService} (08-03) left the
     * whole suite green each time, because no test could move a clock. Each was fixed the same
     * way, with a package-private constructor taking a Caffeine {@link Ticker}. Three identical
     * fixes is not a run of bad luck, it is a missing rule.
     *
     * <p>So this is the rule, enforced the way the {@code maximumSize} sweep above is enforced:
     * scan the source, and for every cache that declares an idle TTL, require its class to offer
     * a constructor a test can hand a {@code Ticker}. A store whose expiry cannot be exercised
     * has an expiry nobody has ever seen work. When this fails it names the class, and the fix is
     * ten lines — the alternative is finding out on the fourth harness.
     */
    @Test
    void everyCacheWithAnIdleTtlExposesASeamForMovingTheClock() throws Exception {
        java.nio.file.Path root = java.nio.file.Path.of("src/main/java");
        List<String> unseamed = new ArrayList<>();
        int idleBounded = 0;

        try (var files = java.nio.file.Files.walk(root)) {
            for (java.nio.file.Path file : files
                    .filter(f -> f.toString().endsWith(".java")).toList()) {
                String text = java.nio.file.Files.readString(file);
                boolean idle = false;
                int at = text.indexOf("Caffeine.newBuilder");
                while (at >= 0) {
                    int end = text.indexOf(';', at);
                    String statement = end < 0 ? text.substring(at) : text.substring(at, end);
                    if (statement.contains(".expireAfterAccess(") || statement.contains(".expireAfter(")) {
                        idle = true;
                    }
                    at = text.indexOf("Caffeine.newBuilder", at + 1);
                }
                if (!idle) {
                    continue;
                }
                idleBounded++;
                String className = root.relativize(file).toString()
                        .replace(".java", "").replace(java.io.File.separatorChar, '.');
                Class<?> type = Class.forName(className);
                boolean seam = java.util.Arrays.stream(type.getDeclaredConstructors())
                        .flatMap(c -> java.util.Arrays.stream(c.getParameterTypes()))
                        .anyMatch(Ticker.class::equals);
                if (!seam) {
                    unseamed.add(type.getSimpleName());
                }
            }
        }

        assertThat(idleBounded)
                .as("the scanner found no idle-bounded caches, so it is broken")
                .isGreaterThanOrEqualTo(6);
        assertThat(unseamed)
                .as("these classes bound a store by idle time and offer no way to advance the "
                        + "clock, so nothing has ever observed that bound working: %s", unseamed)
                .isEmpty();
    }

    @Test
    void mazeCacheEvictsPastItsBound() throws Exception {
        GeneratorRegistry registry = new GeneratorRegistry(List.of(new BinaryTreeGenerator()));
        MazeGenerationService svc = new MazeGenerationService(
                registry, event -> { }, new SimpleMeterRegistry(), 3, Duration.ofHours(1));

        List<UUID> ids = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            ids.add(svc.generate("binary-tree", 5, 5, i).metadata().id());
        }
        // Caffeine's size eviction is not strictly FIFO, so assert the bound, not the victims.
        assertThat(survivorsWithin(ids, svc::find, 3)).isLessThanOrEqualTo(3);
    }

    @Test
    void sessionStoreRefusesPastItsBoundInsteadOfEvictingALiveOne() {
        GameSessionService svc = new GameSessionService(
                event -> { }, mock(LeaderboardService.class), false, 3, Duration.ofHours(1));

        List<UUID> live = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            live.add(svc.open(UUID.randomUUID(), "p" + i, new Point(0, 0)).id());
        }
        assertThatThrownBy(() -> svc.open(UUID.randomUUID(), "overflow", new Point(0, 0)))
                .as("Caffeine put at maximumSize used to LRU-evict; a mid-hunt session "
                        + "then 404ed after an unrelated open")
                .isInstanceOf(GameSessionService.CapacityExceededException.class);
        for (UUID id : live) {
            assertThat(svc.find(id))
                    .as("the older live session must still be findable after the refused open")
                    .isNotNull();
        }
    }

    /** Moves Caffeine's clock without moving the wall clock — see {@code PerKeyRateLimitEvictionTest}. */
    /**
     * The four stores the seam rule above just made testable, each with its clock moved.
     *
     * <p>These are grouped rather than split because they are one property measured four ways:
     * an idle bound that no test advances a clock past is a line of configuration, not a bound.
     * Three services had to be fixed one at a time, on three separate days, before it was worth
     * asking how many others were in the same state. The answer was four more, holding five
     * caches between them.
     *
     * <p>Note what makes them observable at all. A memoization cache — tours, tournaments, fits
     * — is a pure function behind a map, so eviction changes no answer anybody can see; the
     * recomputed value is identical. Each service therefore reports its own cached count, the
     * same window {@code trackedCount}, {@code liveCount} and {@code plannedCount} already open
     * onto their stores. Without that, "the bound works" is unfalsifiable, and an unfalsifiable
     * claim in a test file is worse than no test because it reads like coverage.
     */
    @Test
    void ghostsExpireWhenIdle() {
        FakeClock clock = new FakeClock();
        GhostService ghosts = new GhostService(1000, Duration.ofHours(24), clock);
        UUID mazeId = UUID.randomUUID();
        GameSession session = new GameSession(mazeId, "ariadne", new Point(0, 0));
        session.move(new Point(0, 1));   // a ghost needs a trail; an empty one is ignored
        session.complete(100);
        ghosts.onCompleted(new com.daedalus.plugin.events.SessionCompletedEvent(this, session));
        assertThat(ghosts.ghostOf(mazeId)).as("a completed run takes the seat").isNotNull();

        clock.advance(Duration.ofHours(25));

        assertThat(ghosts.ghostCount()).isZero();
        assertThat(ghosts.ghostOf(mazeId))
                .as("a ghost nobody has raced in a day is not worth a megabyte of trail")
                .isNull();
    }

    @Test
    void cachedToursExpireWhenIdle() {
        FakeClock clock = new FakeClock();
        GeneratorRegistry registry = new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator()));
        MazeGenerationService gen = new MazeGenerationService(
                registry, event -> { }, new SimpleMeterRegistry());
        WaypointService waypoints = new WaypointService(gen,
                new GameSessionService(event -> { }, mock(LeaderboardService.class), false),
                5, 500, Duration.ofHours(2), clock);
        UUID mazeId = gen.generate("recursive-backtracker", 11, 11, 1L).metadata().id();

        assertThat(waypoints.tourFor(mazeId, 3)).isNotNull();
        assertThat(waypoints.cachedTours()).isEqualTo(1);

        clock.advance(Duration.ofHours(3));

        assertThat(waypoints.cachedTours())
                .as("a Held-Karp tour is expensive to compute and cheap to recompute; holding "
                        + "one for a maze nobody has touched in hours is pure residency")
                .isZero();
    }

    @Test
    void cachedTournamentsExpireWhenIdle() {
        FakeClock clock = new FakeClock();
        TournamentService tournaments = new TournamentService(
                new GeneratorRegistry(List.of(new BinaryTreeGenerator())),
                new com.daedalus.solver.solvers.SolverRegistry(List.of(new BfsSolver())),
                24, 41, 100, Duration.ofHours(6), clock);

        assertThat(tournaments.run("binary-tree", 5, TournamentService.MIN_MAZES, 0.0, 1L))
                .isNotNull();
        assertThat(tournaments.cachedTournaments()).isEqualTo(1);

        clock.advance(Duration.ofHours(7));

        assertThat(tournaments.cachedTournaments()).isZero();
    }

    @Test
    void cachedComplexityFitsExpireWhenIdle() {
        FakeClock clock = new FakeClock();
        ComplexityLabService lab = new ComplexityLabService(
                new GeneratorRegistry(List.of(new BinaryTreeGenerator())),
                16, 2, 200, Duration.ofHours(6), clock);

        assertThat(lab.fit("binary-tree", "cellsVisited", 7L)).isNotNull();
        assertThat(lab.cachedFits()).isEqualTo(1);

        clock.advance(Duration.ofHours(7));

        assertThat(lab.cachedFits()).isZero();
    }

    private static final class FakeClock implements Ticker {
        private long nanos;

        @Override
        public long read() {
            return nanos;
        }

        void advance(Duration by) {
            nanos += by.toNanos();
        }
    }

    @Test
    void sessionStoreEvictsAfterItsIdleTtl() {
        // The size bound above and this one are separate promises, and only the first was
        // checked: deleting `expireAfterAccess` from the builder left every test in this class
        // green, because none of them could move time. A store bounded only by size holds a
        // finished game for as long as it takes 10,000 more to push it out — on a quiet
        // instance, indefinitely — which is most of what the unbounded map it replaced did.
        FakeClock clock = new FakeClock();
        GameSessionService svc = new GameSessionService(
                event -> { }, mock(LeaderboardService.class), false, 10_000,
                Duration.ofHours(2), clock);

        UUID id = svc.open(UUID.randomUUID(), "ariadne", new Point(0, 0)).id();
        assertThat(svc.find(id))
                .as("a session must be live the moment it is opened")
                .isNotNull();

        clock.advance(Duration.ofHours(3));

        assertThat(svc.find(id))
                .as("a session idle for longer than the TTL must be gone; an evicted session "
                        + "answers 404 on its next move, which is the API's existing "
                        + "unknown-session path")
                .isNull();
    }

    @Test
    void aRunLongEnoughToOutscoreItselfStillReportsANonNegativeScore() {
        // The score formula subtracts moves and elapsed time from 100,000 and clamps at zero.
        // Nothing pinned the clamp, so removing it passed the whole suite — and a session can
        // reach the negative regime honestly: the idle TTL is two hours, and 10,000 moves is
        // roughly fourteen milliseconds of actual work.
        GameSessionService svc = new GameSessionService(event -> { },
                mock(LeaderboardService.class), false);
        // A real generated maze, not a hand-built fixture — house rule.
        MazeGrid grid = new RecursiveBacktrackerGenerator()
                .generate(8, 8, 42L, new MazeStats());
        grid.setStart(new Point(0, 0));
        grid.setGoal(new Point(7, 7));
        var session = svc.open(UUID.randomUUID(), "sisyphus", grid.start());

        // Pace between the start and one of its open neighbours until the move penalty alone
        // exceeds the base score, then walk to the goal so the session completes.
        Point home = grid.start();
        Point neighbour = grid.openNeighbors(home).iterator().next();
        for (int i = 0; i < 10_100; i++) {
            svc.tryMove(session.id(), grid, (i % 2 == 0) ? neighbour : home);
        }
        for (Point step : new BfsSolver().solve(grid)) {
            svc.tryMove(session.id(), grid, step);
        }

        assertThat(session.score())
                .as("100,000 - 10,101*10 is already below zero before elapsed time is counted; "
                        + "the clamp is what keeps a published score non-negative")
                .isGreaterThanOrEqualTo(0L);
    }

    @Test
    void leaderboardRetainsOnlyTheBestUpToItsCap() {
        LeaderboardService svc = new LeaderboardService(null, false, 5);
        for (int score = 1; score <= 20; score++) {
            svc.submit(new LeaderboardEntry(UUID.randomUUID(), null, "p" + score, score,
                    10, 1000, "binary-tree", Instant.now()));
        }
        List<LeaderboardEntry> top = svc.top(100);
        assertThat(top).hasSize(5);
        // The cap trims from the worst end — the survivors are exactly the best five.
        assertThat(top).extracting(LeaderboardEntry::score)
                .containsExactly(20L, 19L, 18L, 17L, 16L);
    }
}
