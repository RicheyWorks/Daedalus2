// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.AgentSteppedEvent;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.daedalus.plugin.events.TrafficPulseEvent;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.BooleanSupplier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;

/**
 * Traffic simulation (ADR-006 idea #3) at the service seam: occupancy raises entered
 * cells' costs, decay pulls them back to uniform, the tracker retires itself when quiet —
 * and both occupancy sources (players via {@link PlayerMovedEvent}, agents via
 * {@link AgentSteppedEvent}) count identically. Same bounded-poll pattern as the
 * living-maze tests: the pulse runs on the service's scheduler thread.
 */
class TrafficServiceTest {

    private static final Duration FAST_TICK = Duration.ofMillis(25);

    private final List<Object> published = new CopyOnWriteArrayList<>();
    private MazeGenerationService gen;
    private GameSessionService sessions;
    private TrafficService traffic;
    private UUID mazeId;

    @BeforeEach
    void setUp() {
        gen = new MazeGenerationService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                published::add, new SimpleMeterRegistry());
        sessions = new GameSessionService(published::add, mock(LeaderboardService.class), false);
        mazeId = gen.generate("recursive-backtracker", 11, 11, 42L).metadata().id();
    }

    private TrafficService service(Duration tick, int maxConcurrent, int quietTicks) {
        traffic = new TrafficService(gen, sessions, published::add,
                4.0, 0.80, 200.0, tick, maxConcurrent, quietTicks);
        return traffic;
    }

    @AfterEach
    void shutdown() {
        if (traffic != null) traffic.shutdown();
    }

    /* ------------------------------------------------------------------ */

    @Test
    void enablingWrapsAUniformGridWeightedSoCongestionHasAHome() {
        assertThat(gen.find(mazeId).grid()).isNotInstanceOf(WeightedMazeGrid.class);

        var status = service(Duration.ofSeconds(10), 8, 5).enable(mazeId);

        assertThat(status.active()).isTrue();
        assertThat(gen.find(mazeId).grid())
                .as("weight-aware solvers must see congestion from the first pulse")
                .isInstanceOf(WeightedMazeGrid.class);
        assertThat(traffic.enable(mazeId).active()).as("idempotent while tracked").isTrue();
        assertThat(traffic.trackedCount()).isEqualTo(1);
    }

    @Test
    void occupancyFromPlayersAndAgentsRaisesCostsThenDecayReturnsThemToUniform() {
        service(FAST_TICK, 8, 3).enable(mazeId);
        var grid = gen.find(mazeId).grid();
        Point crowded = grid.start();

        // One player move and one agent step onto the same cell — both count.
        var session = sessions.open(mazeId, "alice", grid.start(), null);
        traffic.onPlayerMoved(new PlayerMovedEvent(this, session.id(), "alice",
                grid.start(), crowded));
        traffic.onAgentStepped(new AgentSteppedEvent(this, mazeId, UUID.randomUUID(),
                grid.start(), crowded));

        // Capture the first congested snapshot — Cached is immutable, so unlike a live
        // re-read it cannot decay between the await and the assertions.
        var congested = new java.util.concurrent.atomic.AtomicReference<MazeGenerationService.Cached>();
        awaitUntil(() -> {
            var c = gen.find(mazeId);
            if (c.grid().weightOf(crowded.row(), crowded.col()) > 1.0) {
                congested.set(c);
                return true;
            }
            return false;
        }, "the pulse to apply occupancy");
        var snapshot = congested.get();
        assertThat(snapshot.grid().weightOf(crowded.row(), crowded.col()))
                .as("two occupancy events × bump 4.0, minus decay — never above two bumps")
                .isGreaterThan(1.0).isLessThanOrEqualTo(9.0);
        assertThat(snapshot.hotspots())
                .as("congestion IS a hotspot — existing cost shading just works")
                .anySatisfy(h -> {
                    assertThat(h.row()).isEqualTo(crowded.row());
                    assertThat(h.col()).isEqualTo(crowded.col());
                });

        // No further occupancy: decay must pull the cost back to uniform, then the
        // tracker retires itself with a settled pulse.
        awaitUntil(() -> traffic.trackedCount() == 0, "decay + quiet retirement");
        assertThat(gen.find(mazeId).grid().weightOf(crowded.row(), crowded.col()))
                .isEqualTo(1.0);
        TrafficPulseEvent last = published.stream()
                .filter(TrafficPulseEvent.class::isInstance)
                .map(TrafficPulseEvent.class::cast)
                .reduce((a, b) -> b).orElseThrow();
        assertThat(last.settled()).isTrue();
    }

    @Test
    void costsClampAtMaxAndNeverLeaveTheWeightedApiDomain() {
        service(FAST_TICK, 8, 3).enable(mazeId);
        var grid = gen.find(mazeId).grid();
        Point cell = grid.start();

        // A stampede: far more occupancy than the ceiling allows.
        for (int i = 0; i < 500; i++) {
            traffic.onAgentStepped(new AgentSteppedEvent(this, mazeId, UUID.randomUUID(),
                    cell, cell));
        }
        var peak = new java.util.concurrent.atomic.AtomicReference<Double>(1.0);
        awaitUntil(() -> {
            double w = gen.find(mazeId).grid().weightOf(cell.row(), cell.col());
            peak.set(Math.max(peak.get(), w));
            return peak.get() > 1.0;
        }, "the stampede to land");
        assertThat(peak.get())
                .as("500 × 4.0 would be 2000 — the ceiling keeps it in the API's domain")
                .isGreaterThan(1.0).isLessThanOrEqualTo(200.0);
    }

    @Test
    void untrackedMazesIgnoreOccupancyAndCapacityIsBounded() {
        var other = gen.generate("recursive-backtracker", 8, 8, 7L).metadata().id();
        service(Duration.ofSeconds(10), 1, 5).enable(mazeId);

        // Occupancy on an untracked maze is a no-op, not an error.
        traffic.onAgentStepped(new AgentSteppedEvent(this, other, UUID.randomUUID(),
                new Point(0, 0), new Point(0, 1)));
        assertThat(gen.find(other).grid()).isNotInstanceOf(WeightedMazeGrid.class);

        assertThatThrownBy(() -> traffic.enable(other))
                .isInstanceOf(TrafficService.CapacityExceededException.class);
    }

    @Test
    void twoFirstEnablesCannotBothClaimTheLastSlot() throws Exception {
        var other = gen.generate("recursive-backtracker", 8, 8, 7L).metadata().id();
        service(Duration.ofSeconds(10), 1, 5);
        var go = new java.util.concurrent.CountDownLatch(1);
        var accepted = new java.util.concurrent.atomic.AtomicInteger();
        var refused = new java.util.concurrent.atomic.AtomicInteger();
        try (var pool = java.util.concurrent.Executors.newFixedThreadPool(2)) {
            var first = pool.submit(() -> raceEnable(mazeId, go, accepted, refused));
            var second = pool.submit(() -> raceEnable(other, go, accepted, refused));
            go.countDown();
            first.get(2, java.util.concurrent.TimeUnit.SECONDS);
            second.get(2, java.util.concurrent.TimeUnit.SECONDS);
        }
        assertThat(accepted.get()).as("exactly one first enable owns the only slot").isEqualTo(1);
        assertThat(refused.get()).isEqualTo(1);
        assertThat(traffic.trackedCount()).isEqualTo(1);
    }

    private void raceEnable(UUID id, java.util.concurrent.CountDownLatch go,
                            java.util.concurrent.atomic.AtomicInteger accepted,
                            java.util.concurrent.atomic.AtomicInteger refused) {
        try {
            go.await();
            traffic.enable(id);
            accepted.incrementAndGet();
        } catch (TrafficService.CapacityExceededException e) {
            refused.incrementAndGet();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(e);
        }
    }

    /* ------------------------------------------------------------------ */

    private static void awaitUntil(BooleanSupplier condition, String what) {
        long deadline = System.nanoTime() + Duration.ofSeconds(10).toNanos();
        while (System.nanoTime() < deadline) {
            if (condition.getAsBoolean()) return;
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new AssertionError("interrupted awaiting " + what, e);
            }
        }
        throw new AssertionError("timed out awaiting " + what);
    }
}
