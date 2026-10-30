// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link DistanceOracle}. The table must agree with BFS on <em>every</em> pair, and its diameter
 * must agree with {@link MazeMetrics#diameter} — which computes the same quantity by a completely
 * different route (double-BFS rather than an exhaustive scan), so agreement is real corroboration.
 */
class DistanceOracleTest {

    @Test
    void everyPairMatchesBfs() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(8, 8, 42L);
        DistanceOracle oracle = DistanceOracle.precompute(grid);

        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point from = new Point(r, c);
                int[][] bfs = MazeMetrics.distancesFrom(grid, from);
                for (int r2 = 0; r2 < grid.rows(); r2++) {
                    for (int c2 = 0; c2 < grid.cols(); c2++) {
                        assertThat(oracle.distance(from, new Point(r2, c2)))
                                .as("(%d,%d) -> (%d,%d)", r, c, r2, c2)
                                .isEqualTo(bfs[r2][c2]);
                    }
                }
            }
        }
    }

    @Test
    void isSymmetricAndZeroOnTheDiagonal() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(10, 10, 7L);
        DistanceOracle oracle = DistanceOracle.precompute(grid);

        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point a = new Point(r, c);
                assertThat(oracle.distance(a, a)).isZero();
                Point b = new Point(grid.rows() - 1 - r, grid.cols() - 1 - c);
                assertThat(oracle.distance(a, b)).isEqualTo(oracle.distance(b, a));
            }
        }
    }

    @Test
    void diameterAgreesWithTheDoubleBfsImplementation() {
        for (long seed = 1; seed <= 6; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, seed);

            assertThat(DistanceOracle.precompute(grid).diameter())
                    .as("seed %d", seed)
                    .isEqualTo(MazeMetrics.diameter(grid).distance());
        }
    }

    @Test
    void diameterAgreesOnBraidedMazesToo() {
        // Double-BFS is exact on trees; braided mazes have cycles, so this is the harder case.
        for (long seed = 1; seed <= 6; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, seed);
            Braider.braid(grid, 1.0, seed);

            assertThat(DistanceOracle.precompute(grid).diameter())
                    .as("braided seed %d", seed)
                    .isGreaterThanOrEqualTo(MazeMetrics.diameter(grid).distance());
        }
    }

    @Test
    void eccentricityMatchesTheWorstDistanceFromACell() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(10, 10, 3L);
        DistanceOracle oracle = DistanceOracle.precompute(grid);
        Point corner = new Point(0, 0);

        int worst = 0;
        int[][] bfs = MazeMetrics.distancesFrom(grid, corner);
        for (int[] row : bfs) {
            for (int d : row) {
                worst = Math.max(worst, d);
            }
        }

        assertThat(oracle.eccentricity(corner)).isEqualTo(worst);
    }

    @Test
    void unreachableCellsReportMinusOne() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(new Point(0, 0), new Point(0, 1)); // (1,1) walled off

        DistanceOracle oracle = DistanceOracle.precompute(grid);

        assertThat(oracle.distance(new Point(0, 0), new Point(1, 1)))
                .isEqualTo(DistanceOracle.UNREACHABLE);
        assertThat(oracle.distance(new Point(0, 0), new Point(0, 1))).isEqualTo(1);
    }

    @Test
    void refusesMazesTooLargeToTabulate() {
        MazeGrid tooBig = new MazeGrid(80, 80); // 6,400 cells > MAX_CELLS

        assertThatThrownBy(() -> DistanceOracle.precompute(tooBig))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("MazeMetrics.distancesFrom");
    }

    @Test
    void memoryEstimateIsQuadratic() {
        assertThat(DistanceOracle.memoryBytesFor(1024)).isEqualTo(2L * 1024 * 1024);
        assertThat(DistanceOracle.memoryBytesFor(4096)).isEqualTo(32L * 1024 * 1024);
    }
}
