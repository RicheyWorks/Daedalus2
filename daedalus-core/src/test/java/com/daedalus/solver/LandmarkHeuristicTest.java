// SPDX-License-Identifier: MIT

package com.daedalus.solver;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link LandmarkHeuristic} (ALT). The two properties that matter: the bound must never exceed
 * the true distance (admissibility — otherwise A* stops being optimal), and it must be tight
 * enough to actually save work versus Manhattan.
 */
class LandmarkHeuristicTest {

    private static MazeGrid maze(int size, long seed) {
        return new RecursiveBacktrackerGenerator().generate(size, size, seed);
    }

    @Test
    void estimateNeverExceedsTrueDistance_forEveryCell() {
        for (long seed = 1; seed <= 5; seed++) {
            MazeGrid grid = maze(15, seed);
            Point goal = grid.goal();
            LandmarkHeuristic alt = LandmarkHeuristic.precompute(grid, 4);
            int[][] trueDistance = MazeMetrics.distancesFrom(grid, goal);

            for (int r = 0; r < grid.rows(); r++) {
                for (int c = 0; c < grid.cols(); c++) {
                    int actual = trueDistance[r][c];
                    if (actual < 0) {
                        continue; // unreachable
                    }
                    assertThat(alt.estimate(new Point(r, c), goal))
                            .as("seed %d cell (%d,%d) must be an underestimate", seed, r, c)
                            .isLessThanOrEqualTo(actual);
                }
            }
        }
    }

    @Test
    void aStarWithLandmarks_findsTheSameOptimalLength_asBfs() {
        for (long seed = 1; seed <= 8; seed++) {
            MazeGrid grid = maze(20, seed);
            LandmarkHeuristic alt = LandmarkHeuristic.precompute(grid, 4);

            List<Point> viaAlt = new AStarSolver(alt.asHeuristic())
                    .solve(grid, grid.start(), grid.goal(), new MazeStats());
            List<Point> viaBfs = new BfsSolver()
                    .solve(grid, grid.start(), grid.goal(), new MazeStats());

            assertThat(viaAlt).as("seed %d", seed).hasSameSizeAs(viaBfs);
        }
    }

    @Test
    void landmarks_beatManhattan_onTotalExpansions() {
        long manhattanExpansions = 0;
        long landmarkExpansions = 0;

        for (long seed = 1; seed <= 10; seed++) {
            MazeGrid grid = maze(25, seed);
            LandmarkHeuristic alt = LandmarkHeuristic.precompute(grid, 4);

            MazeStats manhattanStats = new MazeStats();
            new AStarSolver(Heuristics.MANHATTAN).solve(grid, grid.start(), grid.goal(), manhattanStats);

            MazeStats landmarkStats = new MazeStats();
            new AStarSolver(alt.asHeuristic()).solve(grid, grid.start(), grid.goal(), landmarkStats);

            manhattanExpansions += manhattanStats.cellsExplored();
            landmarkExpansions += landmarkStats.cellsExplored();
        }

        assertThat(landmarkExpansions)
                .as("ALT should expand strictly fewer cells in aggregate than Manhattan")
                .isLessThan(manhattanExpansions);
    }

    @Test
    void picksTheRequestedNumberOfDistinctLandmarks_deterministically() {
        MazeGrid grid = maze(20, 42L);

        LandmarkHeuristic first = LandmarkHeuristic.precompute(grid, 4);
        LandmarkHeuristic second = LandmarkHeuristic.precompute(grid, 4);

        assertThat(first.landmarks()).hasSize(4).doesNotHaveDuplicates();
        assertThat(first.landmarks()).isEqualTo(second.landmarks());
    }

    @Test
    void zeroLandmarks_isStillAdmissible_justUseless() {
        MazeGrid grid = maze(10, 1L);
        LandmarkHeuristic none = LandmarkHeuristic.precompute(grid, 0);

        assertThat(none.landmarks()).isEmpty();
        assertThat(none.estimate(grid.start(), grid.goal())).isZero();
    }
}
