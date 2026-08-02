// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.engine.generators.GeneratorRegistry;
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
    void sessionStoreEvictsPastItsBound() throws Exception {
        GameSessionService svc = new GameSessionService(
                event -> { }, mock(LeaderboardService.class), false, 3, Duration.ofHours(1));

        List<UUID> ids = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            ids.add(svc.open(UUID.randomUUID(), "p" + i, new Point(0, 0)).id());
        }
        assertThat(survivorsWithin(ids, svc::find, 3)).isLessThanOrEqualTo(3);
    }

    /** Moves Caffeine's clock without moving the wall clock — see {@code PerKeyRateLimitEvictionTest}. */
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
