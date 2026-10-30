// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.theory.MazeMetrics.Diameter;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link MazeMetrics} on mazes whose diameter is known by construction (a bent corridor, a
 * branching tree, a single cell), plus a real perfect maze where the double-BFS result must be a
 * genuine longest shortest-path.
 */
class MazeMetricsTest {

    @Test
    void bentCorridor_diameterSpansEveryCell() {
        // 2x3 snake: (0,0)-(0,1)-(0,2)-(1,2)-(1,1)-(1,0) — one line of 6 cells with two bends.
        MazeGrid grid = new MazeGrid(2, 3);
        carve(grid, 0, 0, 0, 1);
        carve(grid, 0, 1, 0, 2);
        carve(grid, 0, 2, 1, 2);
        carve(grid, 1, 2, 1, 1);
        carve(grid, 1, 1, 1, 0);

        Diameter d = MazeMetrics.diameter(grid);

        assertThat(d.distance()).isEqualTo(5);
        assertThat(d.path()).hasSize(6);
        assertEndpoints(d, new Point(0, 0), new Point(1, 0));
        assertPathIsAConnectedWalk(grid, d);
    }

    @Test
    void branchingTree_diameterIsTheLongestRootToLeafToLeaf() {
        // 2x4 tree: spine (0,0)-(0,1)-(0,2)-(0,3) with stubs (0,1)-(1,1) and (0,2)-(1,2).
        MazeGrid grid = new MazeGrid(2, 4);
        carve(grid, 0, 0, 0, 1);
        carve(grid, 0, 1, 0, 2);
        carve(grid, 0, 2, 0, 3);
        carve(grid, 0, 1, 1, 1);
        carve(grid, 0, 2, 1, 2);

        Diameter d = MazeMetrics.diameter(grid);

        assertThat(d.distance()).isEqualTo(3);
        assertEndpoints(d, new Point(0, 0), new Point(0, 3));
        assertPathIsAConnectedWalk(grid, d);
    }

    @Test
    void singleCell_hasZeroDiameter() {
        Diameter d = MazeMetrics.diameter(new MazeGrid(1, 1));

        assertThat(d.distance()).isZero();
        assertThat(d.from()).isEqualTo(new Point(0, 0));
        assertThat(d.to()).isEqualTo(new Point(0, 0));
        assertThat(d.path()).containsExactly(new Point(0, 0));
    }

    @Test
    void distancesFrom_marksUnreachableCellsMinusOne() {
        MazeGrid grid = new MazeGrid(2, 2);
        carve(grid, 0, 0, 0, 1); // (1,0) and (1,1) stay walled off

        int[][] dist = MazeMetrics.distancesFrom(grid, new Point(0, 0));

        assertThat(dist[0][0]).isZero();
        assertThat(dist[0][1]).isEqualTo(1);
        assertThat(dist[1][0]).isEqualTo(-1);
        assertThat(dist[1][1]).isEqualTo(-1);
    }

    @Test
    void perfectMaze_diameterEndpointsAreTrulyFarthestApart_andDeterministic() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(8, 8, 42L);

        Diameter d = MazeMetrics.diameter(grid);

        // Path integrity: it's a real walk of length == distance, ending on the endpoints.
        assertThat(d.distance()).isPositive();
        assertThat(d.path()).hasSize(d.distance() + 1);
        assertThat(d.path().get(0)).isEqualTo(d.from());
        assertThat(d.path().get(d.path().size() - 1)).isEqualTo(d.to());
        assertPathIsAConnectedWalk(grid, d);

        // 'to' really is the farthest cell from 'from', and the distance matches.
        int[][] fromDist = MazeMetrics.distancesFrom(grid, d.from());
        assertThat(fromDist[d.to().row()][d.to().col()]).isEqualTo(d.distance());
        assertThat(maxOf(fromDist)).isEqualTo(d.distance());

        // Deterministic: same maze, same verdict.
        assertThat(MazeMetrics.diameter(grid)).isEqualTo(d);
    }

    @Test
    void placeStartAndGoalAtExtremes_movesStartAndGoalOntoTheEndpoints() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(8, 8, 7L);

        Diameter d = MazeMetrics.placeStartAndGoalAtExtremes(grid);

        assertThat(grid.start()).isEqualTo(d.from());
        assertThat(grid.goal()).isEqualTo(d.to());
        assertThat(d.distance()).isPositive();
    }

    // ---------- helpers ----------

    private static void carve(MazeGrid grid, int r1, int c1, int r2, int c2) {
        grid.carve(new Point(r1, c1), new Point(r2, c2));
    }

    private static void assertEndpoints(Diameter d, Point a, Point b) {
        assertThat(d.from()).isIn(a, b);
        assertThat(d.to()).isIn(a, b);
        assertThat(d.from()).isNotEqualTo(d.to());
    }

    private static void assertPathIsAConnectedWalk(MazeGrid grid, Diameter d) {
        for (int i = 0; i + 1 < d.path().size(); i++) {
            assertThat(grid.openNeighbors(d.path().get(i))).contains(d.path().get(i + 1));
        }
    }

    private static int maxOf(int[][] grid) {
        int max = 0;
        for (int[] row : grid) {
            for (int v : row) {
                max = Math.max(max, v);
            }
        }
        return max;
    }
}
