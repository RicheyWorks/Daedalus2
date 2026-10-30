// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.engine.Braider.BraidResult;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link Braider} turns a perfect maze (a spanning tree, {@code V-1} edges, plenty of dead ends)
 * into a braided one with real loops. The structural claims: dead ends go away, edge count rises
 * above {@code V-1} (so cycles exist), and the pass is deterministic under a seed.
 */
class BraiderTest {

    private static MazeGrid perfectMaze(int size, long seed) {
        return new RecursiveBacktrackerGenerator().generate(size, size, seed);
    }

    @Test
    void perfectMazeStartsAsATreeWithDeadEnds() {
        MazeGrid grid = perfectMaze(10, 42L);

        assertThat(edgeCount(grid)).isEqualTo(10 * 10 - 1); // spanning tree: V-1 edges
        assertThat(Braider.deadEnds(grid)).isNotEmpty();
    }

    @Test
    void fullBraid_removesEveryDeadEnd_andCreatesCycles() {
        MazeGrid grid = perfectMaze(10, 42L);
        int treeEdges = edgeCount(grid);

        BraidResult result = Braider.braid(grid, 1.0, 7L);

        assertThat(result.deadEndsBefore()).isPositive();
        assertThat(result.wallsOpened()).isPositive();
        assertThat(result.deadEndsAfter()).isZero();
        assertThat(Braider.deadEnds(grid)).isEmpty();

        // Every carve adds one edge; more than V-1 edges on a connected graph means cycles.
        assertThat(edgeCount(grid)).isEqualTo(treeEdges + result.wallsOpened());
        assertThat(edgeCount(grid)).isGreaterThan(10 * 10 - 1);
    }

    @Test
    void zeroFactor_isANoOp() {
        MazeGrid grid = perfectMaze(8, 3L);
        List<String> before = signature(grid);

        BraidResult result = Braider.braid(grid, 0.0, 7L);

        assertThat(result.wallsOpened()).isZero();
        assertThat(result.deadEndsAfter()).isEqualTo(result.deadEndsBefore());
        assertThat(signature(grid)).isEqualTo(before);
    }

    @Test
    void partialFactor_braidsThatFractionOfDeadEnds() {
        MazeGrid grid = perfectMaze(10, 42L);
        int deadEnds = Braider.deadEnds(grid).size();

        BraidResult result = Braider.braid(grid, 0.5, 7L);

        // Every dead end has at least one walled neighbour, so the target is always reachable.
        assertThat(result.wallsOpened()).isEqualTo((int) Math.round(0.5 * deadEnds));
        assertThat(result.deadEndsAfter()).isLessThan(result.deadEndsBefore());
    }

    @Test
    void isDeterministicForAGivenSeed() {
        MazeGrid a = perfectMaze(10, 42L);
        MazeGrid b = perfectMaze(10, 42L);

        BraidResult ra = Braider.braid(a, 1.0, 7L);
        BraidResult rb = Braider.braid(b, 1.0, 7L);

        assertThat(ra).isEqualTo(rb);
        assertThat(signature(a)).isEqualTo(signature(b));
    }

    @Test
    void differentSeeds_generallyProduceDifferentBraids() {
        MazeGrid a = perfectMaze(12, 42L);
        MazeGrid b = perfectMaze(12, 42L);

        Braider.braid(a, 0.5, 1L);
        Braider.braid(b, 0.5, 999L);

        assertThat(signature(a)).isNotEqualTo(signature(b));
    }

    // ---------- helpers ----------

    /** Undirected passage count: each open neighbour pair is seen twice. */
    private static int edgeCount(MazeGrid grid) {
        int halfEdges = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                halfEdges += grid.openNeighbors(new Point(r, c)).size();
            }
        }
        return halfEdges / 2;
    }

    /** A stable description of the maze's passage structure, for equality comparisons. */
    private static List<String> signature(MazeGrid grid) {
        List<String> sig = new ArrayList<>();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                sig.add(p + "->" + grid.openNeighbors(p));
            }
        }
        return sig;
    }
}
