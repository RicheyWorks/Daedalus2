// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.model.LeaderboardEntry;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Two sessions finishing the same maze. The in-memory board is a
 * {@code ConcurrentSkipListSet} ordered by {@link LeaderboardEntry#compareTo}.
 * Until identity broke score-tuple ties, two equal-score runs were one member
 * and the second submit vanished. Redis keeps members by value, so the backends
 * disagreed. Add-then-pollLast at the cap is a second compound: two threads
 * can both see size == cap+1 and both evict.
 */
class LeaderboardServiceConcurrencyTest {

    private static LeaderboardEntry entry(UUID mazeId, String player, long score) {
        return new LeaderboardEntry(UUID.randomUUID(), mazeId, player, score,
                10, 1000, "recursive-backtracker", Instant.EPOCH);
    }

    @Test
    void twoEqualScoreFinishesOnTheSameMazeBothStay() throws Exception {
        for (int attempt = 0; attempt < 200; attempt++) {
            LeaderboardService svc = new LeaderboardService(null, false, 100);
            UUID maze = UUID.randomUUID();
            LeaderboardEntry alice = entry(maze, "alice", 1_000);
            LeaderboardEntry bob = entry(maze, "bob", 1_000);
            var go = new CountDownLatch(1);
            try (var pool = Executors.newFixedThreadPool(2)) {
                var a = pool.submit(() -> raceSubmit(svc, alice, go));
                var b = pool.submit(() -> raceSubmit(svc, bob, go));
                go.countDown();
                a.get(2, TimeUnit.SECONDS);
                b.get(2, TimeUnit.SECONDS);
            }
            assertThat(svc.top(10, maze))
                    .extracting(LeaderboardEntry::playerName)
                    .as("a skip-list that stops at elapsedMs drops one of two tied runs")
                    .containsExactlyInAnyOrder("alice", "bob");
        }
    }

    @Test
    void concurrentSubmitAtTheCapDoesNotDropAnExtraRun() throws Exception {
        for (int attempt = 0; attempt < 200; attempt++) {
            LeaderboardService svc = new LeaderboardService(null, false, 2);
            UUID maze = UUID.randomUUID();
            svc.submit(entry(maze, "best", 100));
            svc.submit(entry(maze, "second", 90));
            var go = new CountDownLatch(1);
            try (var pool = Executors.newFixedThreadPool(2)) {
                var a = pool.submit(() -> raceSubmit(svc, entry(maze, "worse-a", 80), go));
                var b = pool.submit(() -> raceSubmit(svc, entry(maze, "worse-b", 70), go));
                go.countDown();
                a.get(2, TimeUnit.SECONDS);
                b.get(2, TimeUnit.SECONDS);
            }
            assertThat(svc.top(10))
                    .extracting(LeaderboardEntry::playerName)
                    .as("two threads both polling the worst can shrink the board below the cap")
                    .containsExactly("best", "second");
        }
    }

    private static void raceSubmit(LeaderboardService svc, LeaderboardEntry entry,
                                   CountDownLatch go) {
        try {
            go.await();
            svc.submit(entry);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(e);
        }
    }
}
