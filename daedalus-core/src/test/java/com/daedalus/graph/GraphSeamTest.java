// SPDX-License-Identifier: MIT

package com.daedalus.graph;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The {@link Graph} seam (ADR-001). {@link MazeGraph} must expose exactly the adjacency
 * {@link MazeGrid#openNeighbors} does — that equivalence is what lets every solver move onto the
 * seam without changing behaviour — and {@link CsrGraph} must model a topology nobody could
 * express as a maze.
 */
class GraphSeamTest {

    @Test
    void mazeGraphAdjacencyMatchesOpenNeighborsExactly() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, 42L);
        MazeGraph graph = new MazeGraph(grid);
        int[] buffer = new int[graph.maxDegree()];

        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point here = new Point(r, c);
                int degree = graph.neighbors(graph.idOf(here), buffer);

                List<Point> viaGraph = new ArrayList<>();
                for (int i = 0; i < degree; i++) {
                    viaGraph.add(graph.pointOf(buffer[i]));
                }
                assertThat(viaGraph)
                        .as("cell (%d,%d)", r, c)
                        .containsExactlyInAnyOrderElementsOf(grid.openNeighbors(here));
            }
        }
    }

    @Test
    void mazeGraphIdsMatchGridIndexConvention() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(7, 5, 1L);
        MazeGraph graph = new MazeGraph(grid);

        assertThat(graph.nodeCount()).isEqualTo(35);
        assertThat(graph.idOf(new Point(3, 4))).isEqualTo(3 * 5 + 4);
        assertThat(graph.pointOf(19)).isEqualTo(new Point(3, 4));
    }

    @Test
    void mazeGraphIsALiveView_notASnapshot() {
        MazeGrid grid = new MazeGrid(2, 2);
        MazeGraph graph = new MazeGraph(grid);
        int[] buffer = new int[graph.maxDegree()];

        assertThat(graph.neighbors(0, buffer)).isZero();

        grid.carve(new Point(0, 0), new Point(0, 1)); // carve after construction

        assertThat(graph.neighbors(0, buffer)).isEqualTo(1);
    }

    @Test
    void mazeGraphEdgeWeightFollowsTheDestinationCell() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(5, 5, 1L);

        // Plain grids are uniform cost.
        assertThat(new MazeGraph(grid).edgeWeight(0, 1)).isEqualTo(1.0);
    }

    @Test
    void csrGraphModelsAnArbitraryTopology() {
        // A triangle plus a spur — not expressible as a 4-neighbour grid.
        CsrGraph graph = CsrGraph.builder(4)
                .addUndirected(0, 1, 5.0)
                .addUndirected(1, 2, 2.0)
                .addUndirected(2, 0, 9.0)
                .addUndirected(2, 3, 1.0)
                .build();

        int[] buffer = new int[graph.maxDegree()];
        assertThat(graph.nodeCount()).isEqualTo(4);
        assertThat(graph.neighbors(2, buffer)).isEqualTo(3); // degree 3 — impossible on a grid edge
        assertThat(graph.edgeWeight(0, 1)).isEqualTo(5.0);
        assertThat(graph.edgeWeight(1, 0)).isEqualTo(5.0);
        assertThat(graph.edgeWeight(2, 3)).isEqualTo(1.0);
    }

    @Test
    void csrGraphWeightsAreUpdatableInPlace_forLiveSignals() {
        CsrGraph graph = CsrGraph.builder(2).addUndirected(0, 1, 1.0).build();

        graph.setEdgeWeight(0, 1, 42.0);

        assertThat(graph.edgeWeight(0, 1)).isEqualTo(42.0);
        assertThat(graph.edgeWeight(1, 0)).isEqualTo(1.0); // the reverse direction is its own edge
    }

    @Test
    void csrGraphRejectsBadInput() {
        assertThatThrownBy(() -> CsrGraph.builder(2).addEdge(0, 5, 1.0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CsrGraph.builder(2).addEdge(0, 1, -1.0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CsrGraph.builder(2).build().edgeWeight(0, 1))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
