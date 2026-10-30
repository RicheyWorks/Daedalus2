// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The daily maze's whole value is one property: <b>the date alone determines the maze</b>.
 * No storage, no coordination — two instances, a restart, a replica behind a load balancer
 * all serve the identical topology because the seed derives from the UTC date and the
 * generation pipeline is deterministic end to end. These tests pin that property from both
 * sides: same day → same maze (even across service instances that share no state), and
 * next day → a different one.
 */
class DailyMazeServiceTest {

    private static final Clock DAY_ONE =
            Clock.fixed(Instant.parse("2026-07-30T12:00:00Z"), ZoneOffset.UTC);
    private static final Clock DAY_TWO =
            Clock.fixed(Instant.parse("2026-07-31T00:00:01Z"), ZoneOffset.UTC);

    private MazeGenerationService freshGen() {
        return new MazeGenerationService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                event -> { }, new SimpleMeterRegistry());
    }

    private DailyMazeService service(MazeGenerationService gen, Clock clock) {
        return new DailyMazeService(gen, "recursive-backtracker", 15, 15, clock);
    }

    @Test
    void theSameDayServesTheSameMazeInstance() {
        var gen = freshGen();
        var daily = service(gen, DAY_ONE);

        var first = daily.today();
        var second = daily.today();

        assertThat(second.maze().metadata().id())
                .as("within a day, every caller gets the SAME maze id — shared leaderboard "
                        + "runs and permalinks depend on it")
                .isEqualTo(first.maze().metadata().id());
        assertThat(first.date()).isEqualTo(LocalDate.of(2026, 7, 30));
    }

    @Test
    void instancesSharingNoStateServeTheIdenticalTopology() {
        // Two services, two generation pipelines, zero shared state — a restart, or a
        // second replica. Ids differ (each generated its own copy); the maze must not.
        var a = service(freshGen(), DAY_ONE).today();
        var b = service(freshGen(), DAY_ONE).today();

        assertThat(a.maze().metadata().seed()).isEqualTo(b.maze().metadata().seed());
        assertThat(a.maze().grid().toTileGrid())
                .as("the date IS the coordination mechanism — same date, same maze, "
                        + "no storage required (this is also the eviction-recovery path: "
                        + "a regenerated daily is indistinguishable from the original)")
                .isDeepEqualTo(b.maze().grid().toTileGrid());
        assertThat(a.maze().grid().start()).isEqualTo(b.maze().grid().start());
        assertThat(a.maze().grid().goal()).isEqualTo(b.maze().grid().goal());
    }

    @Test
    void midnightUtcRollsEveryoneToAFreshMaze() {
        var gen = freshGen();
        var today = service(gen, DAY_ONE).today();
        var tomorrow = service(gen, DAY_TWO).today();

        assertThat(tomorrow.maze().metadata().seed())
                .isNotEqualTo(today.maze().metadata().seed());
        assertThat(tomorrow.maze().grid().toTileGrid())
                .isNotEqualTo(today.maze().grid().toTileGrid());
        assertThat(tomorrow.date()).isEqualTo(LocalDate.of(2026, 7, 31));
    }

    @Test
    void consecutiveDaysLandFarApartInSeedSpace() {
        long d1 = DailyMazeService.seedFor(LocalDate.of(2026, 7, 30));
        long d2 = DailyMazeService.seedFor(LocalDate.of(2026, 7, 31));
        // Golden-ratio spread: adjacent epoch days must not produce adjacent seeds, which
        // low-quality generators could turn into visibly similar mazes.
        assertThat(Math.abs(d2 - d1)).isGreaterThan(1_000_000L);
    }

    @Test
    void twoFirstRequestsMintOneMazeNotAnOrphan() throws Exception {
        var published = new java.util.concurrent.CopyOnWriteArrayList<>();
        var gen = new MazeGenerationService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                published::add, new SimpleMeterRegistry());
        var daily = service(gen, DAY_ONE);
        var go = new java.util.concurrent.CountDownLatch(1);
        var ids = new java.util.concurrent.ConcurrentLinkedQueue<java.util.UUID>();
        try (var pool = java.util.concurrent.Executors.newFixedThreadPool(2)) {
            var a = pool.submit(() -> raceToday(daily, go, ids));
            var b = pool.submit(() -> raceToday(daily, go, ids));
            go.countDown();
            a.get(5, java.util.concurrent.TimeUnit.SECONDS);
            b.get(5, java.util.concurrent.TimeUnit.SECONDS);
        }
        assertThat(ids.stream().distinct()).hasSize(1);
        long minted = published.stream()
                .filter(com.daedalus.plugin.events.MazeGeneratedEvent.class::isInstance)
                .count();
        assertThat(minted)
                .as("a lost first-request race used to leave a second maze in the cache")
                .isEqualTo(1);
    }

    private static void raceToday(DailyMazeService daily,
                                  java.util.concurrent.CountDownLatch go,
                                  java.util.Queue<java.util.UUID> ids) {
        try {
            go.await();
            ids.add(daily.today().maze().metadata().id());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(e);
        }
    }
}
