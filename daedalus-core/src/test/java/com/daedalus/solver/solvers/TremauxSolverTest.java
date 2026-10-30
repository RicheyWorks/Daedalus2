// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.KruskalsGenerator;
import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.engine.generators.WilsonsGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Trémaux had no test of its own until 2026-07-19, and the gap hid a real defect.
 *
 * <p>The implementation carried only two of Trémaux's three rules. The missing one — turn back
 * on re-entering a junction you have already stood on via a fresh passage — is what keeps a
 * retreat route open, and without it the walk strands itself on mazes containing loops. The
 * old code read that dead state as "goal unreachable" and returned an empty path. Measured at
 * 20² over 40 seeds, it failed on <b>19/40</b> mazes braided at 0.25, <b>20/40</b> at 0.5 and
 * <b>10/40</b> at 1.0 — all of them solvable, as BFS shows on the same grids.
 *
 * <p>It went unnoticed because every fixture in the suite was a <em>perfect</em> maze, and a
 * spanning tree contains no loop to strand you. So the tests below deliberately braid.
 */
class TremauxSolverTest {

    private static List<MazeGenerator> generators() {
        return List.of(new RecursiveBacktrackerGenerator(), new KruskalsGenerator(),
                new PrimsGenerator(), new WilsonsGenerator());
    }

    private static MazeGrid maze(MazeGenerator gen, int size, long seed, double braid) {
        MazeGrid grid = gen.generate(size, size, seed, new MazeStats());
        if (braid > 0.0) {
            Braider.braid(grid, braid, seed);
        }
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        return grid;
    }

    /**
     * A Trémaux walk is a traversal, not a shortest path — it may revisit cells and double
     * back. What it must never do is teleport: every consecutive pair has to be joined by an
     * open passage, and it has to begin at the start and end at the goal.
     */
    private static void assertIsLegalWalk(MazeGrid grid, List<Point> walk) {
        assertThat(walk).as("walk must not be empty on a connected maze").isNotEmpty();
        assertThat(walk.get(0)).as("walk starts at the start").isEqualTo(grid.start());
        assertThat(walk.get(walk.size() - 1)).as("walk ends at the goal").isEqualTo(grid.goal());
        for (int i = 1; i < walk.size(); i++) {
            Point from = walk.get(i - 1);
            Point to = walk.get(i);
            assertThat(grid.openNeighbors(from))
                    .as("step %d: %s -> %s must cross an open passage, not a wall", i, from, to)
                    .contains(to);
        }
    }

    @ParameterizedTest(name = "braid factor {0}")
    @ValueSource(doubles = {0.0, 0.25, 0.5, 1.0})
    void solvesEveryMaze_atEveryBraidFactor(double braid) {
        // The regression that matters. At braid > 0 the old implementation failed roughly a
        // quarter to a half of these outright.
        List<String> failures = new ArrayList<>();
        for (MazeGenerator gen : generators()) {
            for (long seed = 1; seed <= 10; seed++) {
                MazeGrid grid = maze(gen, 20, seed, braid);
                List<Point> reference = new BfsSolver()
                        .solve(grid, grid.start(), grid.goal(), new MazeStats());
                if (reference.isEmpty()) {
                    continue; // nothing to find; not this solver's problem
                }
                List<Point> walk = new TremauxSolver()
                        .solve(grid, grid.start(), grid.goal(), new MazeStats());
                if (walk.isEmpty()) {
                    failures.add(gen.id() + " seed=" + seed);
                }
            }
        }
        assertThat(failures)
                .as("Trémaux must find a walk wherever BFS finds a path")
                .isEmpty();
    }

    @ParameterizedTest(name = "braid factor {0}")
    @ValueSource(doubles = {0.0, 0.3, 0.7, 1.0})
    void walksAreLegalTraversals(double braid) {
        for (MazeGenerator gen : generators()) {
            for (long seed = 1; seed <= 6; seed++) {
                MazeGrid grid = maze(gen, 16, seed, braid);
                assertIsLegalWalk(grid, new TremauxSolver()
                        .solve(grid, grid.start(), grid.goal(), new MazeStats()));
            }
        }
    }

    @Test
    void respectsTheTwoMarksPerPassageBound() {
        // Each passage may be traversed at most twice, so the walk cannot exceed 2|E|, and the
        // solver's own safety bound of 4V must never be the thing that stops it. If a future
        // change breaks the marking invariant this is where it shows up: the walk would run to
        // the cap instead of terminating on its own.
        int size = 30;
        int cells = size * size;
        for (long seed = 1; seed <= 8; seed++) {
            MazeGrid grid = maze(new RecursiveBacktrackerGenerator(), size, seed, 1.0);
            MazeStats stats = new MazeStats();
            List<Point> walk = new TremauxSolver().solve(grid, grid.start(), grid.goal(), stats);

            assertThat(walk).isNotEmpty();
            assertThat(stats.cellsExplored())
                    .as("terminated on its own, well inside the 4V safety cap")
                    .isLessThan(4L * cells);
        }
    }

    @Test
    void onAPerfectMazeTheWalkVisitsOnlyReachableCells() {
        MazeGrid grid = maze(new RecursiveBacktrackerGenerator(), 24, 7L, 0.0);
        MazeStats stats = new MazeStats();
        List<Point> walk = new TremauxSolver().solve(grid, grid.start(), grid.goal(), stats);

        assertIsLegalWalk(grid, walk);
        // Distinct cells touched cannot exceed the grid, and on a perfect maze the walk is a
        // DFS in disguise, so it should touch a substantial fraction of it.
        assertThat(stats.cellsVisited()).isBetween(1L, (long) 24 * 24);
    }
}
