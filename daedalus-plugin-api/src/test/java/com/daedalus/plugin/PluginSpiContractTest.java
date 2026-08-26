// SPDX-License-Identifier: MIT

package com.daedalus.plugin;

import com.daedalus.plugin.events.MazeGeneratedEvent;
import com.daedalus.plugin.events.PluginFailedEvent;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SPI types the seven-method manifest suite never touched. A contracts module
 * whose only tests are constructor null-guards still ships untested events and
 * default lifecycle methods — the audit's B−.
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
}
