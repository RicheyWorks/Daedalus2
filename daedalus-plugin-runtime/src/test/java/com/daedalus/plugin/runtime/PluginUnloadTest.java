// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginContext;
import com.daedalus.plugin.PluginManifest;
import com.daedalus.solver.solvers.SolverRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationContext;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * A stopped plugin's algorithms leave with it.
 *
 * <h3>What "shutdown" used to mean</h3>
 *
 * <p>{@code shutdownAll()} called {@code stop()} on each plugin and closed the external
 * {@code URLClassLoader}s — and neither registry had any removal path, so the generators and
 * solvers the plugin had contributed stayed in the global maps. Closing a loader does not unload
 * classes already loaded from it, so those objects remained perfectly alive: a "stopped" plugin's
 * generator was still listed by {@code /api/v1/algorithms}, still resolvable by {@code require},
 * and still able to serve a request. On Windows the JAR also stays locked while its classes are
 * reachable, which is the file-handle problem the classloader hygiene work was meant to solve.
 *
 * <h3>The awkward part: nobody records who registered what</h3>
 *
 * <p>Every plugin shares one {@code PluginContext} and therefore one registry, and
 * {@code register} takes only the algorithm. So {@code PluginManager} attributes by diffing the
 * registry's id set across each plugin's boot. That is honest about its own limits — a plugin
 * that registers later, from a thread it started, is unattributable and is left alone rather
 * than guessed at — and it needs no change to the SPI that plugin authors compile against.
 */
class PluginUnloadTest {

    private static final class ContributedGenerator implements MazeGenerator {
        private final String id;

        ContributedGenerator(String id) {
            this.id = id;
        }

        @Override public String id() {
            return id;
        }

        @Override public String displayName() {
            return "Contributed " + id;
        }

        @Override public AlgorithmDescriptor descriptor() {
            return new AlgorithmDescriptor(id, displayName(), "generator", "O(n)", "n/a", "from a plugin");
        }

        @Override public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
            return new MazeGrid(rows, cols);
        }
    }

    private static final class ContributedSolver implements com.daedalus.solver.MazeSolver {
        private final String id;

        ContributedSolver(String id) {
            this.id = id;
        }

        @Override public String id() {
            return id;
        }

        @Override public String displayName() {
            return "Contributed " + id;
        }

        @Override public AlgorithmDescriptor descriptor() {
            return new AlgorithmDescriptor(id, displayName(), "solver", "O(n)", "no", "plugin");
        }

        @Override public List<com.daedalus.model.Point> solve(
                MazeGrid grid, com.daedalus.model.Point start,
                com.daedalus.model.Point goal, MazeStats stats) {
            return List.of();
        }
    }

    /** Contributes a solver as well, so the solver half of the unload is exercised. */
    private static final class SolverContributingPlugin implements MazePlugin {
        @Override public PluginManifest manifest() {
            return new PluginManifest("solvers", "solvers", "1.0.0", "test", "contributes solvers");
        }

        @Override public void registerAlgorithms(PluginContext ctx) {
            ctx.solvers().register(new ContributedSolver("plugin-solver"));
        }
    }

    /** Registers two generators, one during REGISTER_ALGORITHMS and one during START. */
    private static final class ContributingPlugin implements MazePlugin {
        private final String pluginId;
        private final boolean throwOnStart;

        ContributingPlugin(String pluginId, boolean throwOnStart) {
            this.pluginId = pluginId;
            this.throwOnStart = throwOnStart;
        }

        @Override public PluginManifest manifest() {
            return new PluginManifest(pluginId, pluginId, "1.0.0", "test",
                    "contributes generators");
        }

        @Override public void registerAlgorithms(PluginContext ctx) {
            ctx.generators().register(new ContributedGenerator(pluginId + "-early"));
        }

        @Override public void start(PluginContext ctx) {
            // Registering from start() is why the diff brackets the whole boot rather than just
            // the registerAlgorithms call.
            ctx.generators().register(new ContributedGenerator(pluginId + "-late"));
            if (throwOnStart) {
                throw new IllegalStateException("boom in start for " + pluginId);
            }
        }
    }

    private record Fixture(PluginManager manager, GeneratorRegistry generators,
                           SolverRegistry solvers) {}

    private Fixture fixture(MazePlugin... plugins) {
        var generators = new GeneratorRegistry(List.of(
                new RecursiveBacktrackerGenerator(), new BinaryTreeGenerator()));
        var solvers = new SolverRegistry(List.of());
        ApplicationContext spring = mock(ApplicationContext.class);
        when(spring.getBean(GeneratorRegistry.class)).thenReturn(generators);
        when(spring.getBean(SolverRegistry.class)).thenReturn(solvers);

        var pluginRegistry = new PluginRegistry();
        for (MazePlugin plugin : plugins) {
            pluginRegistry.put(plugin);
        }
        // No plugin directory: these plugins are handed in directly, which keeps the test on the
        // lifecycle and off JAR discovery.
        var manager = new PluginManager(pluginRegistry, spring, "no-such-plugin-dir");
        manager.bootAll();
        return new Fixture(manager, generators, solvers);
    }

    @Test
    void shutdownTakesTheContributedAlgorithmsWithIt() {
        var f = fixture(new ContributingPlugin("alpha", false));
        assertThat(f.generators().ids())
                .as("both registration points must land before shutdown means anything")
                .contains("alpha-early", "alpha-late");

        f.manager().shutdownAll();

        assertThat(f.generators().ids())
                .as("a stopped plugin's generators must not still be listed and callable")
                .doesNotContain("alpha-early", "alpha-late");
        assertThat(f.generators().find("alpha-early")).isEmpty();
    }

    @Test
    void theBuiltInsAreUntouchedByAnUnload() {
        // The assertion that stops this fix becoming a worse bug than the one it replaces. A
        // removal path reachable from teardown could take a shipped algorithm with it, which
        // would undo the collision guard from the other side — a plugin that cannot *replace*
        // a built-in could otherwise simply delete one.
        var f = fixture(new ContributingPlugin("alpha", false));
        f.manager().shutdownAll();

        assertThat(f.generators().ids()).contains("recursive-backtracker", "binary-tree");
        assertThat(f.generators().find("recursive-backtracker")).isPresent();
        assertThatThrownBy(() -> f.generators().unregister("recursive-backtracker"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("built-in");
    }

    @Test
    void aPluginThatFailedPartWayThroughStillHasItsRegistrationsRemoved() {
        // This one registered, then threw in start(), so it never reached STARTED. Its two
        // generators are in the registry all the same, and an unload keyed on "STARTED plugins
        // only" would leave exactly them behind — the failure case leaking where the healthy
        // case does not.
        var f = fixture(new ContributingPlugin("broken", true));
        assertThat(f.generators().ids()).contains("broken-early", "broken-late");

        f.manager().shutdownAll();

        assertThat(f.generators().ids()).doesNotContain("broken-early", "broken-late");
    }

    @Test
    void oneUnloadDoesNotTakeAnotherPluginsAlgorithms() {
        // Attribution is by diff, and diffs are easy to get wrong in a way that attributes
        // everything to the first or last plugin to boot.
        var f = fixture(new ContributingPlugin("alpha", false), new ContributingPlugin("beta", false));
        assertThat(f.generators().ids())
                .contains("alpha-early", "alpha-late", "beta-early", "beta-late");

        f.manager().shutdownAll();

        assertThat(f.generators().ids())
                .doesNotContain("alpha-early", "alpha-late", "beta-early", "beta-late");
        assertThat(f.generators().ids()).contains("recursive-backtracker", "binary-tree");
    }

    @Test
    void solverContributionsAreUnloadedToo() {
        // The first version of this test only registered generators, and the coverage ratchet
        // caught it: the entire solver branch of the unload was dead code as far as the suite
        // was concerned. Two registries, two loops, and one of them was being taken on trust —
        // exactly the asymmetry the collision guard had to be tested for separately.
        var f = fixture(new SolverContributingPlugin());
        assertThat(f.solvers().ids()).contains("plugin-solver");

        f.manager().shutdownAll();

        assertThat(f.solvers().ids()).doesNotContain("plugin-solver");
    }

    @Test
    void shutdownWithoutABootDoesNotThrow() {
        // Spring calls the shutdown hook whether or not startup got as far as bootAll(), so a
        // failure earlier in context refresh would otherwise turn one problem into two.
        var generators = new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator()));
        var solvers = new SolverRegistry(List.of());
        ApplicationContext spring = mock(ApplicationContext.class);
        when(spring.getBean(GeneratorRegistry.class)).thenReturn(generators);
        when(spring.getBean(SolverRegistry.class)).thenReturn(solvers);
        var manager = new PluginManager(new PluginRegistry(), spring, "no-such-plugin-dir");

        manager.shutdownAll();

        assertThat(generators.ids()).contains("recursive-backtracker");
    }
}
