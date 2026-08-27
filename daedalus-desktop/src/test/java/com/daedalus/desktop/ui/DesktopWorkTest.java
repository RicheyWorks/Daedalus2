// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.daedalus.solver.SolverBudgetExceededException;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.solver.solvers.IDAStarSolver;
import com.daedalus.solver.solvers.SolverRegistry;
import com.daedalus.theory.MazeMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The desktop's background work, tested without a JavaFX toolkit.
 *
 * <p>That is the reason {@link DesktopWork} exists as plain {@link java.util.concurrent.Callable}s
 * rather than as {@code Task}s: a Task routes its state transitions through
 * {@code Platform.runLater} and cannot run headless, and this module deliberately carries no
 * TestFX or Monocle. Splitting the work from the wrapper keeps the part with actual behaviour
 * testable and leaves only glue in the controller.
 */
class DesktopWorkTest {

    private MazeGenerationService generation;
    private DesktopWork work;
    private final AtomicInteger generationsPerformed = new AtomicInteger();

    @BeforeEach
    void setUp() {
        generation = new MazeGenerationService(
                new GeneratorRegistry(List.of(
                        new RecursiveBacktrackerGenerator(), new DungeonGenerator())),
                event -> generationsPerformed.incrementAndGet(), new SimpleMeterRegistry());
        MazeSolverService solving = new MazeSolverService(
                new SolverRegistry(List.of(new AStarSolver(), new BfsSolver(),
                        new IDAStarSolver())),
                event -> { }, new SimpleMeterRegistry());
        work = new DesktopWork(generation, solving);
    }

    @Test
    void theGenerateJobDoesNothingUntilItIsCalled() throws Exception {
        // The point of returning a Callable is that construction is free and the work happens on
        // whichever thread runs it. If building the job did the generating, moving it to a Task
        // would have changed nothing at all — the freeze would just have moved to the click.
        var job = work.generateJob("recursive-backtracker", 21, 21, 7L);

        // Asserting the job is non-null proves nothing — that was the first version of this
        // test, and a mutation that generated eagerly and returned the finished maze from the
        // lambda survived it untouched. The service publishes an event per generation, so the
        // counter is the observable difference between lazy and eager.
        assertThat(generationsPerformed)
                .as("building the job must not do the work; otherwise the freeze just moves "
                        + "from the Task to the button click")
                .hasValue(0);

        var cached = job.call();

        assertThat(generationsPerformed).hasValue(1);
        assertThat(cached.grid().rows()).isEqualTo(21);
        assertThat(generation.find(cached.metadata().id())).isNotNull();
    }

    @Test
    void aBraidOpensDeadEndsOnTheSameSeed() throws Exception {
        var tree = work.generateJob("recursive-backtracker", 21, 31, 7L, null, 0.0).call();
        var loops = work.generateJob("recursive-backtracker", 21, 31, 7L, null, 0.8).call();
        assertThat(tree.braid()).isNull();
        assertThat(loops.braid()).isEqualTo(0.8);
        assertThat(openPassages(loops.grid()))
                .as("0.8 braid must open dead ends the tree kept closed")
                .isGreaterThan(openPassages(tree.grid()));
    }

    private static int openPassages(MazeGrid grid) {
        int n = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (grid.isOpen(r, c, Direction.EAST)) {
                    n++;
                }
                if (grid.isOpen(r, c, Direction.SOUTH)) {
                    n++;
                }
            }
        }
        return n;
    }

    @Test
    void theSolveJobReturnsARouteForTheMazeItWasGiven() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 21, 21, 7L).call();

        var result = work.solveJob("astar", cached.grid(), cached.metadata().id()).call();

        assertThat(result.path()).isNotEmpty();
        assertThat(result.path().get(0)).isEqualTo(cached.grid().start());
        assertThat(result.path().get(result.path().size() - 1)).isEqualTo(cached.grid().goal());
    }

    @Test
    void aSolverGivingUpSurfacesItsOwnExplanation_notAStackTrace() {
        // IDA* refuses on a dungeon of this size. The desktop is a second consumer of the same
        // core exception the REST layer turns into a 422, and it had no handling of its own —
        // this pins that the message a user sees is the one the exception was written to give,
        // rather than a class name or a bare "null".
        MazeGrid dungeon = new DungeonGenerator().generate(25, 25, 1000L, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(dungeon);
        var adopted = generation.adopt(dungeon, "dungeon", 1000L);

        var job = work.solveJob("ida-star", adopted.grid(), adopted.metadata().id());

        assertThatThrownBy(job::call).isInstanceOf(SolverBudgetExceededException.class);

        String shown = DesktopWork.describeFailure("Solve",
                new SolverBudgetExceededException("ida-star", 5_000_000L));
        assertThat(shown)
                .contains("ida-star")
                .contains("not a statement that the maze is unsolvable")
                .doesNotContain("Solve failed:");
    }

    @Test
    void anUnexpectedFailureKeepsItsIdentity_ratherThanReadingAsRoutine() {
        // The inverse of the case above. A budget refusal is normal and gets its own words; a
        // genuine bug must not be dressed up to look like one, or it never gets reported.
        String shown = DesktopWork.describeFailure("Generation",
                new IllegalStateException("generator returned null grid: broken"));

        assertThat(shown).isEqualTo("Generation failed: generator returned null grid: broken");
    }

    @Test
    void aWrappedFailureIsUnwrapped_becauseThatIsHowATaskReportsIt() {
        // Task.getException() hands back what the Callable threw, but a job run through a
        // Future arrives wrapped. Reporting "ExecutionException: null" to a user would be
        // useless, so the cause is unwrapped before it reaches the status bar.
        String shown = DesktopWork.describeFailure("Solve",
                new ExecutionException(new SolverBudgetExceededException("ida-star", 42L)));

        // `contains("ida-star")` was the first version and it could not fail: an
        // ExecutionException's own message is the cause's toString, so the wrapped text
        // contains every substring the unwrapped text does. The difference is what is NOT
        // there — no wrapper class name, and no "Solve failed:" prefix, because a budget
        // refusal is not a crash.
        assertThat(shown).isEqualTo(new SolverBudgetExceededException("ida-star", 42L).getMessage());
        assertThat(shown)
                .doesNotContain("SolverBudgetExceededException")
                .doesNotContain("Solve failed:");
    }

    @Test
    void aFailureWithNoMessageStillSaysSomethingUseful() {
        String shown = DesktopWork.describeFailure("Generation", new NullPointerException());

        assertThat(shown).isEqualTo("Generation failed: NullPointerException");
    }
}
