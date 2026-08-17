// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.Sealer;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeMutatedEvent;
import com.daedalus.solver.solvers.BfsSolver;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.BooleanSupplier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The living-maze tick (ADR-006), proven at the service seam with a real
 * {@link MazeGenerationService} and real generators — no mocks between the tick and the
 * cache, because the contract under test IS the tick→copy→braid→swap→publish chain.
 *
 * <p>Determinism note: ticks run on the service's scheduler thread, so tests await
 * observable outcomes (events published, run count reaching zero) with a bounded poll —
 * the same pattern {@code BoundedStoresTest} uses for Caffeine's async eviction.
 */
class LivingMazeServiceTest {

    private static final Duration FAST_TICK = Duration.ofMillis(25);

    private final List<Object> published = new CopyOnWriteArrayList<>();
    private final MazeGenerationService gen = new MazeGenerationService(
            new GeneratorRegistry(List.of(
                    new RecursiveBacktrackerGenerator(), new BinaryTreeGenerator())),
            published::add, new SimpleMeterRegistry());

    private LivingMazeService living;

    private LivingMazeService service(Duration tick, int maxConcurrent) {
        living = new LivingMazeService(gen, published::add, new SimpleMeterRegistry(),
                tick, 240, maxConcurrent, 0.25);
        return living;
    }

    @AfterEach
    void shutdown() {
        if (living != null) living.shutdown();
    }

    /* ------------------------------------------------------------------ */

    @Test
    void erosionMutatesSwapsAndNeverBreaksConnectivity() {
        var cached = gen.generate("recursive-backtracker", 15, 15, 42L);
        UUID id = cached.metadata().id();
        MazeGrid before = cached.grid();
        int deadEndsBefore = Braider.deadEnds(before).size();
        assertThat(deadEndsBefore).isGreaterThan(0); // perfect mazes always have dead ends

        var status = service(FAST_TICK, 8).start(id, 3, 7L);
        assertThat(status.active()).isTrue();
        awaitUntil(() -> mutationEvents().size() >= 3, "3 mutation ticks");

        MazeGrid after = gen.find(id).grid();
        assertThat(after)
                .as("the cache must serve a NEW snapshot — mutating in place would tear "
                        + "concurrent readers")
                .isNotSameAs(before);
        assertThat(Braider.deadEnds(after).size()).isLessThan(deadEndsBefore);
        assertThat(Braider.deadEnds(before).size())
                .as("the pre-tick snapshot is immutable — readers holding it stay consistent")
                .isEqualTo(deadEndsBefore);

        // Erosion only opens walls: the maze must still be solvable, start to goal.
        List<Point> route = new BfsSolver()
                .solve(after, after.start(), after.goal(), new MazeStats());
        assertThat(route).isNotEmpty();
        assertThat(after.start()).isEqualTo(before.start());
        assertThat(after.goal()).isEqualTo(before.goal());

        MazeMutatedEvent last = mutationEvents().get(2);
        assertThat(last.tick()).isEqualTo(3);
        assertThat(last.settled()).as("tick 3 of 3 is the run's final frame").isTrue();
    }

    @Test
    void erosionIsDeterministic_sameSeedSameMazeSameResult() {
        var a = gen.generate("recursive-backtracker", 12, 12, 5L);
        var b = gen.generate("recursive-backtracker", 12, 12, 5L);
        assertThat(a.grid().toTileGrid()).isDeepEqualTo(b.grid().toTileGrid());

        service(FAST_TICK, 8);
        living.start(a.metadata().id(), 4, 99L);
        living.start(b.metadata().id(), 4, 99L);
        awaitUntil(() -> living.liveCount() == 0, "both runs to finish");

        assertThat(gen.find(a.metadata().id()).grid().toTileGrid())
                .as("same maze + same seed must erode identically — the same determinism "
                        + "contract every generator honors")
                .isDeepEqualTo(gen.find(b.metadata().id()).grid().toTileGrid());
    }

    @Test
    void aFullyErodedMazeSettlesEarlyInsteadOfTickingToTheCap() {
        var cached = gen.generate("recursive-backtracker", 9, 9, 3L);
        UUID id = cached.metadata().id();
        // Pre-braid every dead end away: erosion will find nothing to do on tick one.
        Braider.braid(cached.grid(), 1.0, 11L);
        assertThat(Braider.deadEnds(cached.grid())).isEmpty();

        service(FAST_TICK, 8).start(id, 200, 1L);
        awaitUntil(() -> living.liveCount() == 0, "the run to settle");

        List<MazeMutatedEvent> events = mutationEvents();
        assertThat(events).hasSize(1);
        assertThat(events.get(0).settled()).isTrue();
        assertThat(events.get(0).wallsOpened()).isZero();
        assertThat(living.status(id).active()).isFalse();
    }

    @Test
    void concurrentRunsAreBoundedAndStartIsIdempotentPerMaze() {
        var a = gen.generate("recursive-backtracker", 10, 10, 1L);
        var b = gen.generate("recursive-backtracker", 10, 10, 2L);

        service(Duration.ofSeconds(10), 1); // slow ticks: run A stays alive for the test
        var first = living.start(a.metadata().id(), 5, 1L);
        assertThat(first.active()).isTrue();

        assertThatThrownBy(() -> living.start(b.metadata().id(), 5, 1L))
                .as("run capacity is a bound, not a queue")
                .isInstanceOf(LivingMazeService.CapacityExceededException.class);

        var again = living.start(a.metadata().id(), 99, 1L);
        assertThat(again.ticksRequested())
                .as("a second /live on an already-living maze joins the existing run "
                        + "instead of stacking a second ticker on the same grid")
                .isEqualTo(5);
        assertThat(living.liveCount()).isEqualTo(1);
    }

    @Test
    void weightedMazesStayWeightedAndDriftedCostsStayInTheApiDomain() {
        var cached = gen.generate("recursive-backtracker", 10, 10, 8L,
                List.of(new Hotspot(2, 2, 999.0), new Hotspot(5, 5, 1.5)));
        UUID id = cached.metadata().id();

        service(FAST_TICK, 8).start(id, 5, 21L);
        awaitUntil(() -> living.liveCount() == 0, "the weighted run to finish");

        var after = gen.find(id);
        assertThat(after.grid())
                .as("copy() must preserve the runtime type — a weighted maze silently "
                        + "flattening to uniform cost erases every hotspot")
                .isInstanceOf(WeightedMazeGrid.class);
        assertThat(after.hotspots()).isNotEmpty();
        for (Hotspot h : after.hotspots()) {
            assertThat(h.cost()).isBetween(1.0, 1000.0);
            assertThat(after.grid().weightOf(h.row(), h.col()))
                    .as("the response-facing hotspot list mirrors the grid's live weights")
                    .isEqualTo(h.cost());
        }
    }

    @Test
    void hardeningClosesLoopsWithoutDisconnectingAnyone() {
        var cached = gen.generate("recursive-backtracker", 12, 12, 42L);
        UUID id = cached.metadata().id();
        Braider.braid(cached.grid(), 1.0, 11L);
        int extras = Sealer.closablePassages(cached.grid()).size();
        assertThat(extras).isPositive();

        // Erosion off, full seal: extras come off, the habitable graph stays one piece.
        living = new LivingMazeService(gen, published::add, new SimpleMeterRegistry(),
                FAST_TICK, 240, 8, 0.0, 1.0);
        living.start(id, 8, 7L);
        awaitUntil(() -> living.liveCount() == 0, "the hardening run to finish");

        MazeGrid after = gen.find(id).grid();
        assertThat(Sealer.closablePassages(after)).isEmpty();
        assertThat(new BfsSolver().solve(after, after.start(), after.goal(), new MazeStats()))
                .isNotEmpty();
        assertThat(mutationEvents().stream().mapToInt(MazeMutatedEvent::wallsClosed).sum())
                .as("erosion is off, so the extras present at start are exactly what closed")
                .isEqualTo(extras);
    }

    @Test
    void replaceNeverResurrectsAnEvictedMaze() {
        var cached = gen.generate("recursive-backtracker", 5, 5, 1L);
        assertThat(gen.replace(UUID.randomUUID(),
                new MazeGenerationService.Cached(cached.metadata(), cached.grid(),
                        new MazeStats())))
                .as("replace on an unknown/evicted id answers false — the living tick's "
                        + "stop signal, never a re-insert that would pin the entry")
                .isFalse();
    }

    /* ------------------------------------------------------------------ */

    private List<MazeMutatedEvent> mutationEvents() {
        return published.stream()
                .filter(MazeMutatedEvent.class::isInstance)
                .map(MazeMutatedEvent.class::cast)
                .toList();
    }

    /** Bounded poll — scheduler outcomes are eventually visible, never instant. */
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
