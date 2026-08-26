// SPDX-License-Identifier: MIT

package com.daedalus.plugin;

import com.daedalus.plugin.events.AgentSteppedEvent;
import com.daedalus.plugin.events.MazeGeneratedEvent;
import com.daedalus.plugin.events.MazeMutatedEvent;
import com.daedalus.plugin.events.MazeSolvedEvent;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.daedalus.plugin.events.PluginFailedEvent;
import com.daedalus.plugin.events.SessionCompletedEvent;
import com.daedalus.plugin.events.TrafficPulseEvent;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.GameSession;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SPI types the seven-method manifest suite never touched. Events and default
 * lifecycle methods are the contracts plugin authors compile against.
 */
class PluginSpiContractTest {

    @Test
    void mazePluginDefaultsAreEmptyAndSafeToCall() {
        MazePlugin plugin = () -> new PluginManifest("spi", "SPI", "1.0", null, null);
        plugin.init(null);
        plugin.registerAlgorithms(null);
        plugin.start(null);
        plugin.stop(null);
        assertThat(plugin.contributedAlgorithms()).isEmpty();
        assertThat(plugin.version()).isEqualTo("1.0");
    }

    @Test
    void abstractPluginStashesTheContextOnInit() {
        PluginContext ctx = new PluginContext() {
            @Override public com.daedalus.engine.generators.GeneratorRegistry generators() {
                return null;
            }
            @Override public com.daedalus.solver.solvers.SolverRegistry solvers() {
                return null;
            }
            @Override public void publish(com.daedalus.plugin.events.PluginEvent event) { }
            @Override public <T> T bean(Class<T> type) { return null; }
        };
        AbstractPlugin plugin = new AbstractPlugin() {
            @Override
            public PluginManifest manifest() {
                return new PluginManifest("abs", "Abs", "1.0", null, null);
            }
        };
        plugin.init(ctx);
        assertThat(plugin.context).isSameAs(ctx);
    }

    @Test
    void pluginFailedEventSurvivesANullCause() {
        PluginFailedEvent event = new PluginFailedEvent(
                this, "broken", "2.0", PluginFailedEvent.Phase.DISCOVER, null);
        assertThat(event.pluginId()).isEqualTo("broken");
        assertThat(event.pluginVersion()).isEqualTo("2.0");
        assertThat(event.phase()).isEqualTo(PluginFailedEvent.Phase.DISCOVER);
        assertThat(event.errorClass()).isNull();
        assertThat(event.errorMessage()).isNull();
        assertThat(event.getSource()).isSameAs(this);
        assertThat(event.getTimestamp()).isPositive();
    }

    @Test
    void generatedEventCarriesTheGridThatWasBuilt() {
        MazeGrid grid = new MazeGrid(3, 3);
        MazeMetadata meta = MazeMetadata.of(3, 3, 1L, "binary-tree",
                new Point(0, 0), new Point(2, 2));
        MazeStats stats = new MazeStats();
        MazeGeneratedEvent event = new MazeGeneratedEvent(this, meta, grid, stats);
        assertThat(event.grid()).isSameAs(grid);
        assertThat(event.metadata()).isSameAs(meta);
        assertThat(event.stats()).isSameAs(stats);
    }

    @Test
    void lifecycleNamesTheStatesTheHostAdvancesThrough() {
        assertThat(PluginLifecycle.values()).containsExactly(
                PluginLifecycle.DISCOVERED, PluginLifecycle.INITIALIZED,
                PluginLifecycle.REGISTERED, PluginLifecycle.STARTED,
                PluginLifecycle.STOPPED, PluginLifecycle.FAILED);
    }

    @Test
    void solvedEventCarriesThePathThatWasFound() {
        UUID mazeId = UUID.randomUUID();
        List<Point> path = List.of(new Point(0, 0), new Point(0, 1));
        MazeStats stats = new MazeStats();
        MazeSolvedEvent event = new MazeSolvedEvent(this, mazeId, "astar", path, stats);
        assertThat(event.mazeId()).isEqualTo(mazeId);
        assertThat(event.solverId()).isEqualTo("astar");
        assertThat(event.path()).isSameAs(path);
        assertThat(event.stats()).isSameAs(stats);
    }

    @Test
    void playerMovedEventKeepsTheSinglePlayerForm() {
        UUID sessionId = UUID.randomUUID();
        Point from = new Point(0, 0);
        Point to = new Point(0, 1);
        PlayerMovedEvent legacy = new PlayerMovedEvent(this, sessionId, from, to);
        assertThat(legacy.sessionId()).isEqualTo(sessionId);
        assertThat(legacy.player()).isNull();
        assertThat(legacy.from()).isSameAs(from);
        assertThat(legacy.to()).isSameAs(to);
        PlayerMovedEvent named = new PlayerMovedEvent(this, sessionId, "web", from, to);
        assertThat(named.player()).isEqualTo("web");
    }

    @Test
    void sessionCompletedEventCarriesTheFrozenSession() {
        GameSession session = new GameSession(UUID.randomUUID(), "web", new Point(0, 0));
        SessionCompletedEvent event = new SessionCompletedEvent(this, session);
        assertThat(event.session()).isSameAs(session);
    }

    @Test
    void mutatedEventV1ConstructorLeavesWallsClosedAtZero() {
        UUID mazeId = UUID.randomUUID();
        MazeGrid grid = new MazeGrid(3, 3);
        MazeMutatedEvent v1 = new MazeMutatedEvent(this, mazeId, 1, 2, 4, false, grid);
        assertThat(v1.mazeId()).isEqualTo(mazeId);
        assertThat(v1.tick()).isEqualTo(1);
        assertThat(v1.wallsOpened()).isEqualTo(2);
        assertThat(v1.wallsClosed()).isZero();
        assertThat(v1.deadEndsRemaining()).isEqualTo(4);
        assertThat(v1.settled()).isFalse();
        assertThat(v1.grid()).isSameAs(grid);
        MazeMutatedEvent v2 = new MazeMutatedEvent(this, mazeId, 2, 0, 3, 1, true, grid);
        assertThat(v2.wallsClosed()).isEqualTo(3);
        assertThat(v2.settled()).isTrue();
    }

    @Test
    void trafficPulseEventReportsCongestionAndTheNewSnapshot() {
        UUID mazeId = UUID.randomUUID();
        MazeGrid grid = new MazeGrid(3, 3);
        TrafficPulseEvent event = new TrafficPulseEvent(this, mazeId, 4, 2.5, false, grid);
        assertThat(event.mazeId()).isEqualTo(mazeId);
        assertThat(event.congestedCells()).isEqualTo(4);
        assertThat(event.peakCost()).isEqualTo(2.5);
        assertThat(event.settled()).isFalse();
        assertThat(event.grid()).isSameAs(grid);
    }

    @Test
    void agentSteppedEventIsTheOccupancyCounterpartOfAPlayerMove() {
        UUID mazeId = UUID.randomUUID();
        UUID agentId = UUID.randomUUID();
        Point from = new Point(1, 1);
        Point to = new Point(1, 2);
        AgentSteppedEvent event = new AgentSteppedEvent(this, mazeId, agentId, from, to);
        assertThat(event.mazeId()).isEqualTo(mazeId);
        assertThat(event.agentId()).isEqualTo(agentId);
        assertThat(event.from()).isSameAs(from);
        assertThat(event.to()).isSameAs(to);
    }
}
