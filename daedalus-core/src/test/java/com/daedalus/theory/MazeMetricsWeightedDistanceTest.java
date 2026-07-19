// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Covers the two Dijkstra distance fields that {@link com.daedalus.solver.LandmarkHeuristic}
 * needs on weighted grids.
 *
 * <p>The interesting assertion here is {@link #theTwoSweepsDisagree_becauseTheCostModelIsDirected()}
 * — it exists to stop someone deleting one of the two sweeps as apparent duplication.
 */
class MazeMetricsWeightedDistanceTest {

    private static final double EPSILON = 1e-9;

    private static MazeGrid maze(int size, long seed) {
        return new RecursiveBacktrackerGenerator().generate(size, size, seed, new MazeStats());
    }

    @Test
    void onAUniformGrid_theCostFieldEqualsTheHopField() {
        MazeGrid grid = maze(16, 1L);
        Point source = new Point(0, 0);

        int[][] hops = MazeMetrics.distancesFrom(grid, source);
        double[][] costs = MazeMetrics.weightedDistancesFrom(grid, source);

        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (hops[r][c] < 0) {
                    assertThat(costs[r][c]).isEqualTo(Double.POSITIVE_INFINITY);
                } else {
                    assertThat(costs[r][c]).isCloseTo(hops[r][c],
                            org.assertj.core.data.Offset.offset(EPSILON));
                }
            }
        }
    }

    @Test
    void theTwoSweepsDisagree_becauseTheCostModelIsDirected() {
        // MazeGrid charges the weight of the cell being ENTERED. So travelling a -> b pays
        // w(b) on arrival while b -> a pays w(a): the two differ by exactly w(b) - w(a), and
        // the graph is directed even though the passages are not.
        //
        // This is why LandmarkHeuristic keeps a forward AND a backward field per landmark, and
        // why the symmetric |d(L,b) - d(L,a)| bound is invalid on weighted grids.
        int size = 12;
        WeightedMazeGrid grid = new WeightedMazeGrid(maze(size, 5L));
        grid.setAllWeights(1.0);
        Point origin = new Point(0, 0);
        Point far = new Point(size - 1, size - 1);
        grid.setWeight(origin, 7.0);   // expensive to enter the origin...
        grid.setWeight(far, 0.25);     // ...cheap to enter the far corner

        double outbound = MazeMetrics.weightedDistancesFrom(grid, origin)[far.row()][far.col()];
        double inbound = MazeMetrics.weightedDistancesTo(grid, origin)[far.row()][far.col()];

        assertThat(outbound).as("d(origin, far)").isFinite();
        assertThat(inbound).as("d(far, origin)").isFinite();
        assertThat(inbound - outbound)
                .as("the gap is exactly w(origin) - w(far), the endpoints' entry costs")
                .isCloseTo(7.0 - 0.25, org.assertj.core.data.Offset.offset(EPSILON));
    }

    @Test
    void weightsChangeWhichRouteIsCheapest() {
        // Guards against the sweep silently ignoring weightOf and degenerating into BFS.
        int size = 16;
        WeightedMazeGrid grid = new WeightedMazeGrid(maze(size, 11L));
        Point source = new Point(0, 0);

        grid.setAllWeights(1.0);
        double uniform = MazeMetrics.weightedDistancesFrom(grid, source)[size - 1][size - 1];

        grid.setAllWeights(3.0);
        double tripled = MazeMetrics.weightedDistancesFrom(grid, source)[size - 1][size - 1];

        assertThat(tripled).isCloseTo(uniform * 3.0, org.assertj.core.data.Offset.offset(EPSILON));
    }

    @Test
    void unreachableCellsAreInfinite() {
        // A 2x2 grid with no passages carved: only the source is reachable.
        MazeGrid isolated = new MazeGrid(2, 2);
        double[][] out = MazeMetrics.weightedDistancesFrom(isolated, new Point(0, 0));

        assertThat(out[0][0]).isZero();
        assertThat(out[0][1]).isEqualTo(Double.POSITIVE_INFINITY);
        assertThat(out[1][0]).isEqualTo(Double.POSITIVE_INFINITY);
        assertThat(out[1][1]).isEqualTo(Double.POSITIVE_INFINITY);
    }

    @Test
    void zeroWeightCellsAreHandled() {
        // Dijkstra requires non-negative, not strictly positive. WeightedMazeGrid permits 0.0,
        // so make sure a zero-cost region doesn't break the sweep or loop forever.
        WeightedMazeGrid grid = new WeightedMazeGrid(maze(10, 13L));
        grid.setAllWeights(0.0);

        double[][] out = MazeMetrics.weightedDistancesFrom(grid, new Point(0, 0));
        assertThat(out[9][9]).as("every reachable cell costs nothing to reach").isZero();
    }
}
