// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.graph.Graph;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.MazeSolver;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.solver.solvers.SolverRegistry;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.ServiceLoader;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * An algorithm id is claimed once. A plugin cannot become a built-in.
 *
 * <h3>What this was like before</h3>
 *
 * <p>{@code register} was {@code map.put(gen.id(), gen)}, and {@code PluginContext} hands every
 * plugin the live registries — so a third-party JAR could declare
 * {@code id() == "recursive-backtracker"} and take the name. Measured with a hostile generator:
 * the registry's size did not change, the algorithm catalogue still advertised the id (carrying
 * the impostor's description), {@code require} returned the impostor, and there was no
 * unregister, so the substitution was permanent for the life of the process.
 *
 * <p>Everything this project says about reproducibility resolves through that lookup — the daily
 * challenge, campaign stages, the seeded waypoint tour, and the cross-process digests in
 * {@code DeterminismGoldenTest}. A plugin could move all of them at once, and the only symptom
 * visible from outside would be that yesterday's seed makes a different maze today.
 */
class RegistryCollisionTest {

    /** A generator that wants to be Recursive Backtracker. */
    private static final class Impostor implements MazeGenerator {
        @Override public String id() {
            return "recursive-backtracker";
        }

        @Override public String displayName() {
            return "Definitely The Real One";
        }

        @Override public AlgorithmDescriptor descriptor() {
            return new AlgorithmDescriptor(id(), displayName(), "generator", "O(1)", "n/a",
                    "an impostor");
        }

        @Override public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
            return new MazeGrid(rows, cols);
        }
    }

    /** A solver that wants to be A*. */
    private static final class SolverImpostor implements MazeSolver {
        @Override public String id() {
            return "astar";
        }

        @Override public String displayName() {
            return "Not A Star";
        }

        @Override public AlgorithmDescriptor descriptor() {
            return new AlgorithmDescriptor(id(), displayName(), "solver", "O(1)", "no", "impostor");
        }

        @Override public List<Point> solve(MazeGrid grid, Point start, Point goal,
                                           MazeStats stats) {
            return List.of();
        }
    }

    private GeneratorRegistry generators() {
        return new GeneratorRegistry(List.of(
                new RecursiveBacktrackerGenerator(), new BinaryTreeGenerator()));
    }

    @Test
    void aPluginCannotTakeABuiltInsId() {
        var registry = generators();
        var incumbent = registry.require("recursive-backtracker");

        assertThatThrownBy(() -> registry.register(new Impostor()))
                .isInstanceOf(DuplicateAlgorithmException.class)
                .hasMessageContaining("recursive-backtracker")
                .hasMessageContaining("RecursiveBacktrackerGenerator")
                .hasMessageContaining("Impostor");

        // The assertion that actually matters. Refusing is only useful if refusing leaves the
        // registry untouched — a guard that throws *after* corrupting the map would satisfy the
        // one above and still lose the built-in.
        assertThat(registry.require("recursive-backtracker"))
                .as("the incumbent must survive the refusal, not merely be reported")
                .isSameAs(incumbent);
        assertThat(registry.all()).hasSize(2);
        assertThat(registry.descriptors())
                .filteredOn(d -> d.id().equals("recursive-backtracker"))
                .singleElement()
                .satisfies(d -> assertThat(d.description()).doesNotContain("impostor"));
    }

    @Test
    void solversAreProtectedTheSameWay() {
        // Same hole, same fix, different registry — and the two are separate classes, so one
        // being guarded says nothing about the other.
        var registry = new SolverRegistry(List.of(new AStarSolver(), new BfsSolver()));
        var incumbent = registry.require("astar");

        assertThatThrownBy(() -> registry.register(new SolverImpostor()))
                .isInstanceOf(DuplicateAlgorithmException.class)
                .hasMessageContaining("astar");
        assertThat(registry.require("astar")).isSameAs(incumbent);
        assertThat(registry.all()).hasSize(2);
    }

    @Test
    void aTakenIdIsTakenEvenForTheIdenticalInstance() {
        // The first version of the guard exempted re-registering the *same object*, on the
        // theory that a double-boot should not fail. Writing the test for it showed nobody could
        // name a path that reaches it — the plugin lifecycle instantiates afresh — so the
        // exemption was permission granted for a case that does not exist, which is how the
        // ALLOW_EMPTY_404 flag and the one-sided coverage ratchet each started. One rule now:
        // a taken id is taken, and something registering twice is worth failing over.
        var registry = new GeneratorRegistry(List.of());
        var same = new RecursiveBacktrackerGenerator();
        assertThatCode(() -> registry.register(same)).doesNotThrowAnyException();
        assertThatThrownBy(() -> registry.register(same))
                .isInstanceOf(DuplicateAlgorithmException.class);
        assertThat(registry.all()).hasSize(1);
    }

    @Test
    void theBuiltInsThemselvesDoNotCollide() {
        // The constructor now registers through the same guarded path, so a duplicate id among
        // the built-ins would fail at startup rather than silently dropping one of them. This
        // asserts the whole shipped set is clean — loaded the way the application loads it.
        List<MazeGenerator> builtInGenerators = ServiceLoader.load(MazeGenerator.class).stream()
                .map(ServiceLoader.Provider::get).toList();
        if (!builtInGenerators.isEmpty()) {
            assertThatCode(() -> new GeneratorRegistry(builtInGenerators))
                    .as("two shipped generators claim the same id")
                    .doesNotThrowAnyException();
            assertThat(builtInGenerators.stream().map(MazeGenerator::id).distinct().count())
                    .isEqualTo(builtInGenerators.size());
        }

        List<MazeSolver> builtInSolvers = ServiceLoader.load(MazeSolver.class).stream()
                .map(ServiceLoader.Provider::get).toList();
        if (!builtInSolvers.isEmpty()) {
            assertThatCode(() -> new SolverRegistry(builtInSolvers))
                    .as("two shipped solvers claim the same id").doesNotThrowAnyException();
        }
    }

    @Test
    void theConstructorGoesThroughTheGuardToo() {
        // The mutation harness found this gap: changing the constructor from
        // `builtIn.forEach(this::register)` to a raw `put` survived every other test, because
        // the shipped set happens to have no duplicates so the bypass is unobservable today.
        // It would stop being unobservable on the day somebody adds a generator whose id is
        // already taken — and the failure would be one of them silently missing at startup,
        // which is the worst possible time to find out. Feeding the constructor a duplicate
        // pins the path rather than the current contents.
        var duplicate = List.<MazeGenerator>of(
                new RecursiveBacktrackerGenerator(), new RecursiveBacktrackerGenerator());
        assertThatThrownBy(() -> new GeneratorRegistry(duplicate))
                .as("built-ins must register through the same guard a plugin does")
                .isInstanceOf(DuplicateAlgorithmException.class);

        assertThatThrownBy(() -> new SolverRegistry(List.of(new AStarSolver(), new AStarSolver())))
                .isInstanceOf(DuplicateAlgorithmException.class);
    }

    @Test
    void theRefusalNamesBothSidesSoTheLogIsActionable() {
        // A plugin author reading "duplicate id" learns nothing. The message has to say which
        // class holds the id and which one was turned away, or the first thing they do is ask.
        var registry = generators();
        assertThatThrownBy(() -> registry.register(new Impostor()))
                .satisfies(e -> {
                    var d = (DuplicateAlgorithmException) e;
                    assertThat(d.kind()).isEqualTo("generator");
                    assertThat(d.id()).isEqualTo("recursive-backtracker");
                    assertThat(d.getMessage()).contains("distinct id");
                });
    }

    /** Unused import guard: {@link Graph} keeps the solver SPI import honest. */
    @SuppressWarnings("unused")
    private Graph unused;
}
