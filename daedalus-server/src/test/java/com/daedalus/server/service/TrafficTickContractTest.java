// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.AgentSteppedEvent;
import com.daedalus.plugin.events.TrafficPulseEvent;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.mock;

/**
 * The scheduling half of {@link TrafficService} — the guarantees about what is <em>running</em>
 * rather than what is computed.
 *
 * <p>{@link TrafficServiceTest} covers the arithmetic (occupancy raises cost, decay returns it,
 * the ceiling clamps) by watching a real scheduler through a bounded poll, which is the right
 * tool for an outcome that eventually appears. It is the wrong tool for the four promises below,
 * because each of them is about something that must <em>not</em> happen, and nothing observable
 * happens when they lapse:
 *
 * <ul>
 *   <li><b>{@code enable} is idempotent.</b> The javadoc says "idempotent while tracked"; a
 *       second call must neither take a second slot against {@code max-concurrent} nor schedule
 *       a second ticker on the same maze. {@code TrafficServiceTest} calls {@code enable} twice
 *       and asserts {@code trackedCount() == 1}, but the count is a map size keyed by maze — it
 *       reads 1 whether the second call reused the tracker or replaced it, and it says nothing
 *       at all about how many tasks are queued.
 *   <li><b>A retired tracker leaves nothing scheduled.</b> {@code stop} removes the map entry
 *       <em>and</em> cancels the future; a leak of the second half is invisible, because an
 *       orphaned tick on a settled maze does no damage you can see — until it reaches its own
 *       quiet threshold and calls {@code stop} on a maze someone has since re-enabled.
 *   <li><b>Occupancy restarts the quiet countdown.</b> Without the reset, quiet ticks accumulate
 *       across activity and a maze in steady use retires mid-game. Wall-clock, the difference is
 *       a few tick intervals — long enough to be slow to test, short enough to be flaky.
 *   <li><b>A throwing tick retires its tracker.</b> The {@code catch} calls {@code stop} so a
 *       tracker cannot spin on a permanently broken maze, logging once per tick forever.
 * </ul>
 *
 * <p>So this class hands the service its executor ({@link ManualTicker}) and runs ticks
 * synchronously on the test thread. Every assertion below is exact and none of them sleep: tick
 * counts are counts, not durations, and "still scheduled" is a number the fake can report.
 */
class TrafficTickContractTest {

    private final List<Object> published = new CopyOnWriteArrayList<>();
    private final ManualTicker ticker = new ManualTicker();

    private ScriptedGen gen;
    private GameSessionService sessions;
    private TrafficService traffic;
    private UUID mazeId;

    @BeforeEach
    void setUp() {
        gen = new ScriptedGen(new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                published::add);
        sessions = new GameSessionService(published::add, mock(LeaderboardService.class), false);
        mazeId = gen.generate("recursive-backtracker", 11, 11, 42L).metadata().id();
    }

    private TrafficService service(int maxConcurrent, int quietTicks) {
        traffic = new TrafficService(gen, sessions, published::add,
                4.0, 0.80, 200.0, Duration.ofMillis(25), maxConcurrent, quietTicks, ticker);
        return traffic;
    }

    @AfterEach
    void shutdown() {
        if (traffic != null) traffic.shutdown();
    }

    /* ------------------------------------------------------------------ */

    @Test
    void reEnablingATrackedMazeTakesNeitherASecondSlotNorASecondTicker() {
        // max-concurrent 1, and this maze is the one tenant: if the second enable re-runs the
        // capacity check instead of returning the existing tracker, it 409s on itself.
        service(1, 5).enable(mazeId);

        assertThatCode(() -> traffic.enable(mazeId))
                .as("idempotent while tracked — a re-enable is not a new tenant")
                .doesNotThrowAnyException();

        assertThat(traffic.trackedCount()).isEqualTo(1);
        assertThat(ticker.live())
                .as("one maze, one ticker, however many times enable is called")
                .isEqualTo(1);
    }

    @Test
    void aMazeThatGoesQuietRetiresItsTrackerAndLeavesNothingScheduled() {
        service(8, 3).enable(mazeId);

        ticker.tick();
        ticker.tick();
        assertThat(traffic.trackedCount()).as("two quiet ticks of three").isEqualTo(1);

        ticker.tick();

        assertThat(traffic.trackedCount()).isZero();
        assertThat(ticker.live()).as("the retired tracker's future is cancelled").isZero();
        assertThat(settledPulses()).isEqualTo(1);
    }

    @Test
    void occupancyRestartsTheQuietCountdownInsteadOfAccumulatingAcrossIt() {
        service(8, 3).enable(mazeId);
        Point cell = gen.find(mazeId).grid().start();

        ticker.tick();
        ticker.tick(); // two quiet ticks — one short of retirement

        traffic.onAgentStepped(new AgentSteppedEvent(this, mazeId, UUID.randomUUID(), cell, cell));
        ticker.tick(); // occupancy applied: this tick changed something, so it is not quiet

        // Decay ticks also change something, so the countdown only restarts once the cell is
        // uniform again. Drive them to completion rather than counting them: how many a bump
        // takes to decay is arithmetic this test has no business pinning.
        for (int i = 0; i < 100 && weightOf(cell) > 1.0; i++) {
            ticker.tick();
        }
        assertThat(weightOf(cell)).as("decay returned the cell to uniform").isEqualTo(1.0);

        ticker.tick();
        ticker.tick(); // two quiet ticks again — again one short, if the counter reset

        assertThat(traffic.trackedCount())
                .as("the countdown runs from the last occupancy, not from enable")
                .isEqualTo(1);
        assertThat(settledPulses()).isZero();
    }

    @Test
    void aTickThatThrowsRetiresItsTrackerInsteadOfSpinningOnABrokenMaze() {
        service(8, 5).enable(mazeId);
        Point cell = gen.find(mazeId).grid().start();

        gen.explode = true; // armed after enable — the wrap-on-enable swap goes through
        traffic.onAgentStepped(new AgentSteppedEvent(this, mazeId, UUID.randomUUID(), cell, cell));
        ticker.tick();

        assertThat(traffic.trackedCount())
                .as("a tracker that cannot commit is retired, not left logging every tick")
                .isZero();
        assertThat(ticker.live()).isZero();
    }

    /* ------------------------------------------------------------------ */

    private double weightOf(Point p) {
        return gen.find(mazeId).grid().weightOf(p.row(), p.col());
    }

    private long settledPulses() {
        return published.stream()
                .filter(TrafficPulseEvent.class::isInstance)
                .map(TrafficPulseEvent.class::cast)
                .filter(TrafficPulseEvent::settled)
                .count();
    }
}
