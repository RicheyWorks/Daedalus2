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
            svc.submit(new LeaderboardEntry(UUID.randomUUID(), "p" + score, score,
                    10, 1000, "binary-tree", Instant.now()));
        }
        List<LeaderboardEntry> top = svc.top(100);
        assertThat(top).hasSize(5);
        // The cap trims from the worst end — the survivors are exactly the best five.
        assertThat(top).extracting(LeaderboardEntry::score)
                .containsExactly(20L, 19L, 18L, 17L, 16L);
    }
}
