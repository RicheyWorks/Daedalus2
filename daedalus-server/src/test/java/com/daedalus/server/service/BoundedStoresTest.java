// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.Point;
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
