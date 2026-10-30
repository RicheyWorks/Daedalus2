// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.AgentSteppedEvent;
import com.github.benmanes.caffeine.cache.Ticker;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The fog-of-war walk's boundaries — the promises {@link AgentWalkServiceTest} does not reach.
 *
 * <p>That suite tests the walk from the caller's side and does it well: the opening view is fog
 * only, a blind agent following real openings reaches the goal, a wall bump is refused without
 * spending budget, the budget is a hard stop, and a living maze changes the world under the
 * agent's feet. Fourteen mutations found seven survivors anyway, and the shape of the gap is
 * consistent: a caller-side test asks whether the walk <em>works</em>. It has no reason to ask
 * whether the walk revealed too much, whether the configured ceiling was honoured, or what
 * happens on the paths a caller cannot reach on purpose.
 *
 * <ul>
 *   <li><b>The fog's second filter.</b> {@code view} reports a direction only if the wall is open
 *       <em>and</em> the neighbour is in bounds. Generated mazes never have an outward-open border
 *       wall — {@code GeneratorInvariantFuzzTest} enforces that as a universal invariant — so the
 *       second half of the condition is defence against a grid the registry did not produce.
 *       Generators are a plugin extension point, so that is not a hypothetical source.
 *   <li><b>The step ceiling.</b> {@code daedalus.agent.max-steps} bounds what one caller can ask
 *       the server to do, both for an explicit request and for the {@code 4·rows·cols} default.
 *       Nothing pinned either clamp.
 *   <li><b>Occupancy.</b> {@code AgentSteppedEvent} is the wire between a blind walk and the
 *       traffic simulation. {@code TrafficServiceTest} publishes that event by hand, so the
 *       traffic side is covered and the <em>wiring</em> was not: dropping the publish left both
 *       suites green while agents stopped raising congestion entirely.
 *   <li><b>The idle bound and the dead maze.</b> Third verse of the same song — a store bounded
 *       only by size, and a walk whose maze has been evicted, which returns 404 by design and
 *       threw a NullPointerException under mutation.
 * </ul>
 */
class AgentWalkContractTest {

    private final List<Object> published = new ArrayList<>();
    private final GeneratorRegistry registry =
            new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator()));

    private ScriptedGen gen;

    @BeforeEach
    void setUp() {
        gen = new ScriptedGen(registry, published::add);
    }

    private AgentWalkService service(int maxSteps) {
        return new AgentWalkService(gen, published::add, 10_000, Duration.ofHours(1), maxSteps);
    }

    /* ------------------------------------------------------------------ */

    @Test
    void theFogNeverReportsAnOpeningThatLeavesTheGrid() {
        // A grid the generators cannot produce, which is the point: the registry is a plugin
        // extension point, and this guard is what stops a third-party generator's stray border
        // opening from becoming a direction the agent is invited to walk through.
        //
        // One row, so every cell is on the north and south edges whichever one `adopt` picks for
        // the start — the first version of this test set the start itself and asserted nothing,
        // because adopt re-places start and goal at the extremes and moved the agent off the
        // doctored cell. It passed with the guard deleted, which is how that was found.
        MazeGrid corridor = new MazeGrid(1, 7);
        for (int c = 0; c < 6; c++) {
            corridor.carve(new Point(0, c), new Point(0, c + 1));
        }
        var cached = gen.adopt(corridor, "hand-made", 3L);
        cached.grid().cell(cached.grid().start()).open(Direction.NORTH); // off the top edge

        var view = service(1000).open(cached.metadata().id(), null);

        assertThat(view.open())
                .as("a direction leading off the grid is not an opening, whatever the wall says")
                .doesNotContain(Direction.NORTH)
                .hasSize(cached.grid().openNeighbors(cached.grid().start()).size());
    }

    @Test
    void theConfiguredStepCeilingBoundsBothTheRequestAndTheDefault() {
        UUID id = gen.generate("recursive-backtracker", 21, 21, 1L).metadata().id();
        var capped = service(50);

        assertThat(capped.open(id, 1_000_000).stepsRemaining())
                .as("a caller asking for a million steps gets the configured ceiling")
                .isEqualTo(50);
        assertThat(capped.open(id, null).stepsRemaining())
                .as("and so does the 4*rows*cols default, which is 1764 on this maze")
                .isEqualTo(50);
        assertThat(service(100_000).open(id, null).stepsRemaining())
                .as("under the ceiling the default is the default")
                .isEqualTo(4 * 21 * 21);
    }

    @Test
    void aStepRaisesTrafficTheSameWayAPlayerMoveDoes() {
        UUID id = gen.generate("recursive-backtracker", 9, 9, 1L).metadata().id();
        var agents = service(1000);
        var opened = agents.open(id, null);
        published.clear();

        Direction first = opened.open().get(0);
        var after = agents.step(opened.agentId(), first);

        assertThat(published)
                .as("without this event a blind walk leaves no footprints and the traffic "
                        + "simulation stops seeing agents at all — TrafficServiceTest publishes "
                        + "the event by hand, so only the wiring is at stake here")
                .anySatisfy(e -> assertThat(e).isInstanceOfSatisfying(AgentSteppedEvent.class,
                        ev -> {
                            assertThat(ev.mazeId()).isEqualTo(id);
                            assertThat(ev.to()).isEqualTo(after.position());
                            assertThat(ev.from()).isEqualTo(opened.position());
                        }));
    }

    @Test
    void theAgentStoreExpiresIdleWalksAndNotOnlyOversizedOnes() {
        FakeClock clock = new FakeClock();
        var agents = new AgentWalkService(gen, published::add, 10_000,
                Duration.ofHours(1), 100_000, clock);
        UUID id = gen.generate("recursive-backtracker", 9, 9, 1L).metadata().id();
        UUID agentId = agents.open(id, null).agentId();
        assertThat(agents.view(agentId)).isNotNull();

        clock.advance(Duration.ofHours(2));

        assertThat(agents.view(agentId))
                .as("size and idle are separate bounds; with only the first, a quiet instance "
                        + "keeps every walk anyone ever opened")
                .isNull();
    }

    @Test
    void aWalkWhoseMazeWasEvictedAnswers404RatherThanFailing() {
        UUID id = gen.generate("recursive-backtracker", 9, 9, 1L).metadata().id();
        var agents = service(1000);
        var opened = agents.open(id, null);

        gen.hidden.add(id); // the maze cache dropped it mid-walk

        assertThat(agents.view(opened.agentId())).isNull();
        assertThat(agents.step(opened.agentId(), opened.open().get(0)))
                .as("the walk dies with its maze — a null is the controller's 404, and anything "
                        + "else here is a 500 for an ordinary eviction")
                .isNull();
    }

    @Test
    void aWallBumpCostsNothing_evenRepeated() {
        // AgentWalkServiceTest pins one bump. This pins the accounting across several, which is
        // what a real exploring client does: the honest agent that probes and backs off must not
        // finish with less budget than one that never probes.
        UUID id = gen.generate("recursive-backtracker", 11, 11, 5L).metadata().id();
        var agents = service(1000);
        var opened = agents.open(id, null);
        int before = opened.stepsRemaining();

        List<Direction> walls = new ArrayList<>(List.of(Direction.values()));
        walls.removeAll(opened.open());
        for (int i = 0; i < 3; i++) {
            for (Direction wall : walls) {
                assertThatThrownBy(() -> agents.step(opened.agentId(), wall))
                        .isInstanceOf(IllegalArgumentException.class);
            }
        }

        assertThat(agents.view(opened.agentId()).stepsRemaining())
                .as("%d wall bumps must cost nothing at all", walls.size() * 3)
                .isEqualTo(before);
        assertThat(agents.view(opened.agentId()).stepsUsed()).isZero();
    }

    /** Moves Caffeine's clock without moving the wall clock. */
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
}
