// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link MazeFlow#vertexDisjointPaths} — route redundancy via Menger's theorem. A perfect maze
 * has exactly one route; braiding is what creates genuinely independent alternatives.
 */
class MazeFlowVertexDisjointTest {

    @Test
    void perfectMaze_hasExactlyOneRoute() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(10, 10, 42L);

        assertThat(MazeFlow.vertexDisjointPaths(grid, grid.start(), grid.goal())).isEqualTo(1);
    }

    @Test
    void braidedRing_hasTwoIndependentRoutes() {
        // 2x2 ring: the two corners are joined by two routes sharing no intermediate cell.
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(new Point(0, 0), new Point(0, 1));
        grid.carve(new Point(0, 1), new Point(1, 1));
        grid.carve(new Point(1, 1), new Point(1, 0));
        grid.carve(new Point(1, 0), new Point(0, 0));

        assertThat(MazeFlow.vertexDisjointPaths(grid, new Point(0, 0), new Point(1, 1))).isEqualTo(2);
    }

    @Test
    void corridor_hasOneRoute() {
        MazeGrid grid = new MazeGrid(1, 4);
        grid.carve(new Point(0, 0), new Point(0, 1));
        grid.carve(new Point(0, 1), new Point(0, 2));
        grid.carve(new Point(0, 2), new Point(0, 3));

        assertThat(MazeFlow.vertexDisjointPaths(grid, new Point(0, 0), new Point(0, 3))).isEqualTo(1);
    }

    @Test
    void adjacentCells_countTheDirectPassage() {
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(new Point(0, 0), new Point(0, 1));

        assertThat(MazeFlow.vertexDisjointPaths(grid, new Point(0, 0), new Point(0, 1))).isEqualTo(1);
    }

    @Test
    void sameCell_isZero() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(5, 5, 1L);

        assertThat(MazeFlow.vertexDisjointPaths(grid, new Point(2, 2), new Point(2, 2))).isZero();
    }

    @Test
    void disconnectedCells_haveNoRoute() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(new Point(0, 0), new Point(0, 1)); // (1,1) walled off

        assertThat(MazeFlow.vertexDisjointPaths(grid, new Point(0, 0), new Point(1, 1))).isZero();
    }

    @Test
    void vertexConnectivityNeverExceedsEdgeConnectivity_onBraidedMazes() {
        for (long seed = 1; seed <= 15; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, seed);
            Braider.braid(grid, 1.0, seed);

            int vertex = MazeFlow.vertexDisjointPaths(grid, grid.start(), grid.goal());
            int edge = MazeFlow.edgeConnectivity(grid, grid.start(), grid.goal());

            assertThat(vertex).as("seed %d: blocking cells is at least as strong as blocking passages", seed)
                    .isLessThanOrEqualTo(edge);
            assertThat(vertex).isPositive();
        }
    }

    @Test
    void braidingCreatesRedundancy_wherePerfectMazesHaveNone() {
        int improved = 0;
        for (long seed = 1; seed <= 15; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, seed);
            assertThat(MazeFlow.vertexDisjointPaths(grid, grid.start(), grid.goal())).isEqualTo(1);

            Braider.braid(grid, 1.0, seed);
            if (MazeFlow.vertexDisjointPaths(grid, grid.start(), grid.goal()) > 1) {
                improved++;
            }
        }
        assertThat(improved)
                .as("full braiding should give most mazes more than one independent route")
                .isGreaterThan(0);
    }
}
