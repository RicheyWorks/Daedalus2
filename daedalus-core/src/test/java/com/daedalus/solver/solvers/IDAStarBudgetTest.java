// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.Heuristics;
import com.daedalus.solver.SolverBudgetExceededException;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * IDA*'s node budget — the guard on a search that was effectively unbounded.
 *
 * <p>Measured before the budget existed, on mazes the REST surface accepts: a 15×15 dungeon
 * solved instantly, a 21×21 dungeon took 9–16 seconds (~90 million expansions), and a 25×25
 * dungeon was abandoned after <b>300 seconds still running</b>. Every other solver finishes the
 * 21×21 dungeon in under 40 ms, and "Compare all solvers" runs this one alongside them. Four
 * more rows of maze turned a slow reply into one that never arrives.
 */
class IDAStarBudgetTest {

    @Test
    void aDungeonThatUsedToRunForMinutesNowGivesUp() {
        MazeGrid dungeon = new DungeonGenerator().generate(25, 25, 1000L, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(dungeon);
        MazeStats stats = new MazeStats();

        assertThatThrownBy(() -> new IDAStarSolver()
                .solve(dungeon, dungeon.start(), dungeon.goal(), stats))
                .isInstanceOf(SolverBudgetExceededException.class)
                .hasMessageContaining("ida-star")
                .hasMessageContaining("not a statement that the maze is unsolvable");

        assertThat(stats.cellsExplored())
                .as("the budget must actually stop the search, not merely be declared")
                .isEqualTo(IDAStarSolver.DEFAULT_NODE_BUDGET);
    }

    @Test
    void givingUpIsNeverReportedAsUnreachable() {
        // The contract this protects: MazeSolver documents an empty path as "no route exists".
        // A budget-exhausted search knows nothing about reachability, and this maze is solvable
        // — every other solver finds a route through it in milliseconds. Returning empty here
        // would put a confident false claim into the compare table and the sweep.
        MazeGrid dungeon = new DungeonGenerator().generate(25, 25, 1000L, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(dungeon);

        assertThatThrownBy(() -> new IDAStarSolver().solve(dungeon))
                .isInstanceOf(SolverBudgetExceededException.class);

        List<Point> viaBfs = new BfsSolver().solve(dungeon);
        assertThat(viaBfs)
                .as("the maze IDA* gave up on is trivially solvable by BFS")
                .isNotEmpty();
    }

    @Test
    void theBudgetDoesNotSpoilTheMazesThisSolverIsGoodFor() {
        // Perfect mazes are IDA*'s reasonable case and must still solve, optimally.
        for (int size : new int[] {21, 51}) {
            MazeGrid grid = new RecursiveBacktrackerGenerator()
                    .generate(size, size, 1000L, new MazeStats());
            MazeMetrics.placeStartAndGoalAtExtremes(grid);

            List<Point> path = new IDAStarSolver().solve(grid);

            assertThat(path).isNotEmpty();
            assertThat(path).hasSameSizeAs(
                    MazeMetrics.shortestPath(grid, grid.start(), grid.goal()));
        }
    }

    @Test
    void aHugePerfectMazeRefusesRatherThanBlowingTheStack() {
        // The search recurses, so depth follows the f-bound. Without the budget a 512x512 tree
        // is the shape that would eventually overflow; with it, the run ends as a refusal in
        // about a second. Measured, not assumed — this asserts the failure mode is the intended
        // one and not a StackOverflowError wearing its coat.
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(512, 512, 3L, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);

        assertThatThrownBy(() -> new IDAStarSolver().solve(grid))
                .isInstanceOf(SolverBudgetExceededException.class);
    }

    @Test
    void anUnlimitedBudgetIsStillAvailableForBenchmarks() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(11, 11, 5L, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);

        List<Point> path = new IDAStarSolver(Heuristics.MANHATTAN, 0)
                .solve(grid, grid.start(), grid.goal(), new MazeStats());

        assertThat(path).isNotEmpty();
    }

    @Test
    void atinyBudgetGivesUpImmediately_provingTheCounterIsLive() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(21, 21, 1000L, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        MazeStats stats = new MazeStats();

        assertThatThrownBy(() -> new IDAStarSolver(Heuristics.MANHATTAN, 50)
                .solve(grid, grid.start(), grid.goal(), stats))
                .isInstanceOf(SolverBudgetExceededException.class)
                .hasMessageContaining("50 nodes");
        assertThat(stats.cellsExplored()).isEqualTo(50);
    }
}
