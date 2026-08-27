// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.Braider;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.plugin.events.MazeMutatedEvent;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The bounds and the scheduling of a living run — the promises {@link LivingMazeServiceTest}
 * cannot reach from the far side of a real clock.
 *
 * <p>That suite is the stronger of the two ticker suites in this package: it pins the
 * copy-on-write swap by identity, checks the pre-tick snapshot survives it, proves determinism
 * by eroding two identical mazes under one seed, and asks the right question about idempotence —
 * restarting a live maze with a <em>different</em> tick count and checking the run kept its
 * original one. Pointing mutations at the class anyway found five things it does not see, and
 * every one of them is a promise about a boundary rather than about an outcome:
 *
 * <ul>
 *   <li><b>One ticker per maze.</b> The idempotence assertion proves the second {@code start}
 *       joined the existing <em>run</em>; it says nothing about how many <em>tasks</em> are
 *       scheduled against it. Dropping the {@code future == null} guard schedules a second, and
 *       the maze then erodes at twice the requested rate while the run's own tick count — which
 *       is what {@code status} reports — advances normally.
 *   <li><b>At least one wall per tick while any dead end remains.</b> {@code Braider} opens
 *       {@code round(factor * deadEnds)}, so a plain {@code erosionFactor} of 0.08 opens
 *       <em>nothing</em> once fewer than about six dead ends remain. The run then reports itself
 *       settled with dead ends still in the maze — not a failure, just a maze that stopped
 *       eroding early, which no assertion about connectivity or determinism can distinguish from
 *       one that finished.
 *   <li><b>The per-run tick cap.</b> {@code max-ticks} is the bound on how long one request can
 *       occupy the shared ticker; nothing pinned it, and a caller asking for a million ticks got
 *       a million.
 *   <li><b>Erosion never mints hotspots.</b> {@code drift} skips uniform cells. Without that
 *       skip every cell in a weighted maze breathes, and the response's hotspot list grows from
 *       a handful to rows·cols entries — every one of them still inside the API's cost domain,
 *       so every existing assertion about hotspots still passes.
 *   <li><b>A failed commit ends the run.</b> {@code replace} answering false is the documented
 *       stop signal (the maze was evicted; never resurrect it) and a throwing tick must retire
 *       its run rather than spin. Neither path is reachable without a fake, so neither was tested.
 * </ul>
 *
 * <p>{@link ManualTicker} makes all five exact: ticks are counts run on the test thread, and
 * "how many tickers are alive" is a number.
 */
class LivingMazeTickContractTest {

    private final List<Object> published = new CopyOnWriteArrayList<>();
    private final ManualTicker ticker = new ManualTicker();

    private ScriptedGen gen;
    private LivingMazeService living;
    private SimpleMeterRegistry meters;

    @BeforeEach
    void setUp() {
        gen = new ScriptedGen(new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                published::add);
    }

    private LivingMazeService service(int maxTicks, int maxConcurrent, double erosionFactor) {
        meters = new SimpleMeterRegistry();
        living = new LivingMazeService(gen, published::add, meters, Duration.ofMillis(25),
                maxTicks, maxConcurrent, erosionFactor, ticker);
        return living;
    }

    @AfterEach
    void shutdown() {
        if (living != null) living.shutdown();
    }

    /* ------------------------------------------------------------------ */

    @Test
    void restartingALiveMazeJoinsItsRunInsteadOfSchedulingASecondTicker() {
        UUID id = gen.generate("recursive-backtracker", 11, 11, 42L).metadata().id();
        service(240, 8, 0.08).start(id, 5, 1L);

        var again = living.start(id, 99, 7L);

        assertThat(again.ticksRequested()).as("joined the existing run").isEqualTo(5);
        assertThat(living.liveCount()).isEqualTo(1);
        assertThat(ticker.live())
                .as("a second ticker would erode the maze at twice the requested rate, and "
                        + "outlive the run that owns it")
                .isEqualTo(1);
    }

    @Test
    void aRunEndsExactlyAtItsRequestedTickCountAndLeavesNothingScheduled() {
        UUID id = gen.generate("recursive-backtracker", 15, 15, 42L).metadata().id();
        service(240, 8, 0.08).start(id, 3, 1L);

        assertThat(ticker.tickUntil(() -> living.liveCount() == 0, 20)).isEqualTo(3);
        assertThat(mutations()).hasSize(3);
        assertThat(mutations().get(2).tick()).isEqualTo(3);
        assertThat(ticker.live()).as("the finished run's future is cancelled").isZero();
    }

    @Test
    void aRequestedTickCountIsClampedToTheConfiguredCap() {
        UUID id = gen.generate("recursive-backtracker", 9, 9, 4L).metadata().id();

        var status = service(3, 8, 0.08).start(id, 1_000_000, 1L);

        assertThat(status.ticksRequested())
                .as("max-ticks bounds how long one request can hold the shared ticker")
                .isEqualTo(3);
        assertThat(ticker.tickUntil(() -> living.liveCount() == 0, 20)).isEqualTo(3);
    }

    @Test
    void erosionOpensAWallWheneverADeadEndRemains() {
        // 0.08 of the handful of dead ends a 9x9 ends up with rounds to zero long before the
        // maze is fully eroded — the floor of one wall per tick is what finishes the job.
        var cached = gen.generate("recursive-backtracker", 9, 9, 3L);
        UUID id = cached.metadata().id();
        assertThat(Braider.deadEnds(cached.grid())).isNotEmpty();

        service(240, 8, 0.08).start(id, 240, 1L);
        ticker.tickUntil(() -> living.liveCount() == 0, 400);

        MazeMutatedEvent last = mutations().get(mutations().size() - 1);
        assertThat(last.settled()).isTrue();
        assertThat(last.deadEndsRemaining())
                .as("a run that stops while dead ends remain has stalled, not settled")
                .isZero();
        assertThat(Braider.deadEnds(gen.find(id).grid())).isEmpty();
    }

    @Test
    void driftBreathesTheHotspotsItWasGivenAndMintsNoNewOnes() {
        var cached = gen.generate("recursive-backtracker", 10, 10, 8L,
                List.of(new Hotspot(2, 2, 40.0), new Hotspot(5, 5, 1.5)));
        UUID id = cached.metadata().id();

        service(240, 8, 0.08).start(id, 4, 21L);
        ticker.tickUntil(() -> living.liveCount() == 0, 20);

        assertThat(gen.find(id).hotspots())
                .as("only existing hotspots breathe — erosion never mints new ones, and a "
                        + "hotspot list the size of the grid is a different response entirely")
                .hasSizeLessThanOrEqualTo(2);
    }

    @Test
    void aRunWhoseMazeWasEvictedRetiresInsteadOfCommittingOverTheEviction() {
        UUID id = gen.generate("recursive-backtracker", 11, 11, 42L).metadata().id();
        service(240, 8, 0.08).start(id, 10, 1L);

        gen.refuseReplace = true; // the cache dropped this entry between find and replace
        ticker.tick();

        assertThat(living.liveCount()).isZero();
        assertThat(ticker.live()).isZero();
        assertThat(mutations())
                .as("no mutation is announced for a snapshot that was never committed")
                .isEmpty();
        assertThat(living.status(id).ticksDone()).isZero();
        assertThat(living.lastTickFailed())
                .as("an eviction is the documented stop signal, not a thrown tick")
                .isFalse();
        assertThat(living.lastTickError()).isNull();
    }

    @Test
    void aTickThatThrowsEndsItsRunInsteadOfSpinningOnABrokenMaze() {
        UUID id = gen.generate("recursive-backtracker", 11, 11, 42L).metadata().id();
        service(240, 8, 0.08).start(id, 10, 1L);

        gen.explode = true;
        ticker.tick();

        assertThat(living.liveCount())
                .as("one broken maze must not hold the shared ticker thread forever")
                .isZero();
        assertThat(ticker.live()).isZero();
        assertThat(living.lastTickFailed())
                .as("a thrown tick is not a warn-only log")
                .isTrue();
        assertThat(living.lastTickError()).contains("cache swap failed");
        assertThat(meters.counter("daedalus.living.tick.failure").count()).isEqualTo(1.0);

        gen.explode = false;
        living.start(id, 3, 1L);
        ticker.tick();
        assertThat(living.lastTickFailed())
                .as("health must recover when a later tick completes")
                .isFalse();
        assertThat(living.lastTickError()).isNull();
    }

    @Test
    void aTickerNeverAskedIsNotAFailure() {
        service(240, 8, 0.08);
        assertThat(living.lastTickFailed()).isFalse();
        assertThat(living.lastTickError()).isNull();
    }

    /* ------------------------------------------------------------------ */

    private List<MazeMutatedEvent> mutations() {
        return published.stream()
                .filter(MazeMutatedEvent.class::isInstance)
                .map(MazeMutatedEvent.class::cast)
                .toList();
    }
}
