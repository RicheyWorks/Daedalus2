// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link MazeMetrics#exactDiameter(MazeGrid)} against the fast double-BFS estimate.
 *
 * <p>The two-sweep diameter trick is exact only on a <b>tree</b>. Its correctness argument
 * needs the farthest cell from an arbitrary source to be an endpoint of some diameter, and a
 * single cycle breaks that — a shortcut can land the first sweep somewhere that lies on no
 * diameter at all. On the repository's perfect-maze fixtures the two always agree, which is
 * exactly why the distinction is easy to miss.
 */
class MazeMetricsExactDiameterTest {

    private static MazeGrid maze(int size, long seed, double braid) {
        MazeGrid grid = new RecursiveBacktrackerGenerator()
                .generate(size, size, seed, new MazeStats());
        if (braid > 0.0) {
            Braider.braid(grid, braid, seed);
        }
        return grid;
    }

    /** Brute force, independent of the code under test: BFS from every cell, take the max. */
    private static int bruteForceDiameter(MazeGrid grid) {
        int best = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                for (int[] row : MazeMetrics.distancesFrom(grid, new Point(r, c))) {
                    for (int d : row) {
                        best = Math.max(best, d);
                    }
                }
            }
        }
        return best;
    }

    @ParameterizedTest(name = "braid factor {0}")
    @ValueSource(doubles = {0.0, 0.3, 0.7, 1.0})
    void exactDiameterMatchesBruteForce(double braid) {
        for (long seed = 1; seed <= 6; seed++) {
            MazeGrid grid = maze(14, seed, braid);
            assertThat(MazeMetrics.exactDiameter(grid).distance())
                    .as("seed %d braid %.1f", seed, braid)
                    .isEqualTo(bruteForceDiameter(grid));
        }
    }

    @Test
    void onPerfectMazesTheFastEstimateIsAlreadyExact() {
        // The documented guarantee, and the reason the estimate is the default.
        for (long seed = 1; seed <= 8; seed++) {
            MazeGrid grid = maze(16, seed, 0.0);
            assertThat(MazeMetrics.diameter(grid).distance())
                    .as("double-BFS is exact on a tree (seed %d)", seed)
                    .isEqualTo(MazeMetrics.exactDiameter(grid).distance());
        }
    }

    @Test
    void onBraidedMazesTheFastEstimateIsALowerBound_neverAnOverEstimate() {
        // The direction of the error is the part that matters: callers may safely treat
        // diameter() as "at least this far apart". An over-estimate would be a real defect,
        // because it would understate worst-case route length in planning use.
        for (long seed = 1; seed <= 12; seed++) {
            for (double braid : new double[] {0.3, 0.5, 0.7, 1.0}) {
                MazeGrid grid = maze(16, seed, braid);
                int estimate = MazeMetrics.diameter(grid).distance();
                int exact = MazeMetrics.exactDiameter(grid).distance();
                assertThat(estimate)
                        .as("seed %d braid %.1f: estimate must never exceed the truth",
                                seed, braid)
                        .isLessThanOrEqualTo(exact);
            }
        }
    }

    @Test
    void reportedEndpointsAreReallyThatFarApart() {
        // Guards the record's internal consistency: the endpoints, the distance and the path
        // must all describe the same route.
        MazeGrid grid = maze(16, 3L, 0.7);
        MazeMetrics.Diameter d = MazeMetrics.exactDiameter(grid);
        List<Point> path = d.path();

        assertThat(path).isNotEmpty();
        assertThat(path.get(0)).isEqualTo(d.from());
        assertThat(path.get(path.size() - 1)).isEqualTo(d.to());
        assertThat(path).hasSize(d.distance() + 1);
        assertThat(MazeMetrics.distancesFrom(grid, d.from())[d.to().row()][d.to().col()])
                .isEqualTo(d.distance());
    }

    @Test
    void handlesAGridWithNoPassagesCarved() {
        // Every cell isolated: the widest separation anywhere is zero, and the record must
        // still be internally consistent rather than throwing or returning null.
        MazeMetrics.Diameter d = MazeMetrics.exactDiameter(new MazeGrid(3, 3));

        assertThat(d.distance()).isZero();
        assertThat(d.from()).isEqualTo(d.to());
        assertThat(d.path()).containsExactly(d.from());
    }
}
