// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.BfsSolver;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The fog-of-war walk contract (ADR-006 idea #7): what the agent can see, what a step
 * costs, when a walk ends — and the composition the ADR was built for: visibility reads
 * the maze cache's <em>live</em> grid, so a living maze changes under the agent's feet.
 */
class AgentWalkServiceTest {

    private MazeGenerationService gen;
    private AgentWalkService agents;
    private UUID mazeId;
    private MazeGrid grid;

    @BeforeEach
    void setUp() {
        gen = new MazeGenerationService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                event -> { }, new SimpleMeterRegistry());
        agents = new AgentWalkService(gen, event -> { }, 10_000, Duration.ofHours(1), 100_000);
        var cached = gen.generate("recursive-backtracker", 11, 11, 42L);
        mazeId = cached.metadata().id();
        grid = cached.grid();
    }

    @Test
    void theOpeningViewIsFogOnly_positionGoalAndLocalOpenings() {
        var view = agents.open(mazeId, null);

        assertThat(view.position()).isEqualTo(grid.start());
        assertThat(view.goal()).isEqualTo(grid.goal());
        assertThat(view.stepsRemaining()).isEqualTo(4 * 11 * 11); // the default budget
        assertThat(view.arrived()).isFalse();

        // The visible world is exactly the current cell's openings — nothing more.
        for (Direction d : Direction.values()) {
            boolean actuallyOpen = grid.cell(grid.start()).isOpen(d)
                    && grid.inBounds(grid.start().step(d));
            assertThat(view.open().contains(d))
                    .as("visibility of %s must mirror the real grid", d)
                    .isEqualTo(actuallyOpen);
        }
    }

    @Test
    void aBlindAgentFollowingRealOpeningsReachesTheGoal() {
        // Drive the agent along the true shortest path (the test may peek; the agent never
        // does — every step is validated against fog rules like any other caller's).
        List<Point> path = new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
        var view = agents.open(mazeId, null);

        for (int i = 1; i < path.size(); i++) {
            Direction d = MazeGrid.directionBetween(path.get(i - 1), path.get(i));
            view = agents.step(view.agentId(), d);
            assertThat(view.position()).isEqualTo(path.get(i));
        }

        assertThat(view.arrived()).isTrue();
        assertThat(view.stepsUsed()).isEqualTo(path.size() - 1);

        var arrived = view;
        assertThatThrownBy(() -> agents.step(arrived.agentId(), arrived.open().get(0)))
                .as("an arrived walk is over — no victory laps")
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void walkingIntoAWallIsRejectedWithoutConsumingBudget() {
        var view = agents.open(mazeId, null);
        Direction blocked = null;
        for (Direction d : Direction.values()) {
            if (!view.open().contains(d)) { blocked = d; break; }
        }
        assertThat(blocked).as("a perfect maze's start cell always has a wall").isNotNull();

        UUID id = view.agentId();
        Direction wall = blocked;
        assertThatThrownBy(() -> agents.step(id, wall))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("no opening");
        assertThat(agents.view(id).stepsUsed())
                .as("the view already told the caller the openings — a wall-bump is a "
                        + "caller bug, not an exploration cost")
                .isZero();
    }

    @Test
    void theStepBudgetIsAHardStop() {
        var view = agents.open(mazeId, 1);
        assertThat(view.stepsRemaining()).isEqualTo(1);

        view = agents.step(view.agentId(), view.open().get(0));
        assertThat(view.expired()).as("1 step spent, not at goal → expired").isTrue();
        assertThat(view.stepsRemaining()).isZero();

        var expired = view;
        assertThatThrownBy(() -> agents.step(expired.agentId(), expired.open().get(0)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("budget");
    }

    @Test
    void aLivingMazeChangesTheWorldUnderTheAgentsFeet() {
        var view = agents.open(mazeId, null);

        // Erode exactly one wall at the agent's position, the way a living-maze tick
        // does: copy, mutate, atomically swap into the cache.
        Direction walled = null;
        for (Direction d : Direction.values()) {
            if (!view.open().contains(d) && grid.inBounds(grid.start().step(d))) {
                walled = d;
                break;
            }
        }
        assertThat(walled).isNotNull();
        MazeGrid eroded = grid.copy();
        eroded.carve(eroded.cell(grid.start()), walled);
        var cached = gen.find(mazeId);
        assertThat(gen.replace(mazeId, new MazeGenerationService.Cached(
                cached.metadata(), eroded, cached.stats(), cached.hotspots()))).isTrue();

        var after = agents.view(view.agentId());
        assertThat(after.open())
                .as("visibility must read the LIVE grid — yesterday's wall is today's "
                        + "shortcut, which is the entire point of walking a living maze")
                .contains(walled);
        assertThat(after.stepsUsed()).as("polling is free").isZero();

        // And the new opening is genuinely walkable.
        var stepped = agents.step(view.agentId(), walled);
        assertThat(stepped.position()).isEqualTo(grid.start().step(walled));
    }

    @Test
    void deadAgentsAndDeadMazesAnswerNull() {
        assertThat(agents.view(UUID.randomUUID())).isNull();
        assertThat(agents.step(UUID.randomUUID(), Direction.NORTH)).isNull();
        assertThat(agents.open(UUID.randomUUID(), null))
                .as("unknown maze → null → controller 404")
                .isNull();
    }

    @Test
    void openingPastTheWalkCapRefusesInsteadOfEvictingAMidHuntWalk() {
        var capped = new AgentWalkService(gen, event -> { }, 2, Duration.ofHours(1), 100_000);
        var first = capped.open(mazeId, 8);
        assertThat(first).isNotNull();
        capped.step(first.agentId(), first.open().get(0));
        var second = capped.open(mazeId, 8);
        assertThat(second).isNotNull();

        assertThatThrownBy(() -> capped.open(mazeId, 8))
                .as("Caffeine put at maximumSize used to LRU-evict the older walk; "
                        + "the next view then 404ed after an unrelated open")
                .isInstanceOf(AgentWalkService.CapacityExceededException.class);

        assertThat(capped.view(first.agentId()))
                .as("the mid-hunt walk must still be queryable after the refused open")
                .isNotNull();
        assertThat(capped.view(first.agentId()).stepsUsed()).isEqualTo(1);
        assertThat(capped.view(second.agentId())).isNotNull();
    }

    @Test
    void twoFirstWalksCannotBothTakeTheLastSlot() throws Exception {
        var capped = new AgentWalkService(gen, event -> { }, 1, Duration.ofHours(1), 100_000);
        var go = new java.util.concurrent.CountDownLatch(1);
        var accepted = new java.util.concurrent.CopyOnWriteArrayList<UUID>();
        var refused = new java.util.concurrent.atomic.AtomicInteger();
        try (var pool = java.util.concurrent.Executors.newFixedThreadPool(2)) {
            var a = pool.submit(() -> raceOpen(capped, mazeId, go, accepted, refused));
            var b = pool.submit(() -> raceOpen(capped, mazeId, go, accepted, refused));
            go.countDown();
            a.get(2, java.util.concurrent.TimeUnit.SECONDS);
            b.get(2, java.util.concurrent.TimeUnit.SECONDS);
        }
        assertThat(accepted).as("exactly one first walk owns the only slot").hasSize(1);
        assertThat(refused.get()).isEqualTo(1);
        assertThat(capped.view(accepted.get(0)))
                .as("the walk that won the slot is still live")
                .isNotNull();
    }

    private static void raceOpen(AgentWalkService agents, UUID mazeId,
                                 java.util.concurrent.CountDownLatch go,
                                 java.util.concurrent.CopyOnWriteArrayList<UUID> accepted,
                                 java.util.concurrent.atomic.AtomicInteger refused) {
        try {
            go.await();
            accepted.add(agents.open(mazeId, 8).agentId());
        } catch (AgentWalkService.CapacityExceededException e) {
            refused.incrementAndGet();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(e);
        }
    }
}
