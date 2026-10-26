// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.theory.MazeFlow.MinCut;
import com.daedalus.theory.MazeFlow.Passage;
import org.junit.jupiter.api.Test;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link MazeFlow} min-cut / max-flow. A perfect maze has a single route (cut = 1); a braided
 * maze with a loop has two edge-disjoint routes (cut = 2). In every case the returned cut edges
 * must, when removed, actually separate start from goal.
 */
class MazeFlowTest {

    @Test
    void perfectMaze_hasCutSizeOne_andThatEdgeIsABottleneck() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(8, 8, 42L);

        MinCut cut = MazeFlow.minCutStartToGoal(grid);

        assertThat(cut.cutSize()).isEqualTo(1);
        assertThat(cut.cutEdges()).hasSize(1);
        assertThat(connected(grid, grid.start(), grid.goal(), Set.copyOf(cut.cutEdges()))).isFalse();
    }

    @Test
    void braidedRing_hasCutSizeTwo_withTwoEdgeDisjointRoutes() {
        // 2x2 ring: (0,0)-(0,1)-(1,1)-(1,0)-(0,0). Opposite corners have two disjoint routes.
        MazeGrid grid = new MazeGrid(2, 2);
        carve(grid, 0, 0, 0, 1);
        carve(grid, 0, 1, 1, 1);
        carve(grid, 1, 1, 1, 0);
        carve(grid, 1, 0, 0, 0);

        MinCut cut = MazeFlow.minCut(grid, new Point(0, 0), new Point(1, 1));

        assertThat(cut.cutSize()).isEqualTo(2);
        assertThat(cut.cutEdges()).hasSize(2);
        assertThat(connected(grid, new Point(0, 0), new Point(1, 1), Set.copyOf(cut.cutEdges()))).isFalse();
    }

    @Test
    void corridor_hasCutSizeOne() {
        MazeGrid grid = new MazeGrid(1, 4);
        carve(grid, 0, 0, 0, 1);
        carve(grid, 0, 1, 0, 2);
        carve(grid, 0, 2, 0, 3);

        assertThat(MazeFlow.edgeConnectivity(grid, new Point(0, 0), new Point(0, 3))).isEqualTo(1);
    }

    @Test
    void edgeConnectivity_matchesCutSize() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(6, 6, 3L);

        assertThat(MazeFlow.edgeConnectivity(grid, grid.start(), grid.goal()))
                .isEqualTo(MazeFlow.minCutStartToGoal(grid).cutSize());
    }

    @Test
    void sameCell_hasZeroCut() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(5, 5, 1L);

        MinCut cut = MazeFlow.minCut(grid, new Point(2, 2), new Point(2, 2));

        assertThat(cut.cutSize()).isZero();
        assertThat(cut.cutEdges()).isEmpty();
    }

    @Test
    void isDeterministic() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(10, 10, 99L);

        assertThat(MazeFlow.minCutStartToGoal(grid)).isEqualTo(MazeFlow.minCutStartToGoal(grid));
    }

    @Test
    void unitCapacityOverload_matchesTheNoArgCut() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(8, 8, 7L);

        assertThat(MazeFlow.minCut(grid, grid.start(), grid.goal(), MazeFlow.UNIT))
                .isEqualTo(MazeFlow.minCut(grid, grid.start(), grid.goal()));
    }

    @Test
    void uniformCapacity_scalesFlowAndLeavesTheCutSetAlone() {
        // If Residual still hardcodes 1, fat.cutSize stays 2 on this ring.
        MazeGrid ring = ring();
        Point s = new Point(0, 0);
        Point t = new Point(1, 1);

        MinCut unit = MazeFlow.minCut(ring, s, t);
        MinCut fat = MazeFlow.minCut(ring, s, t, (from, to) -> 3);

        assertThat(unit.cutSize()).isEqualTo(2);
        assertThat(fat.cutSize()).isEqualTo(6);
        assertThat(fat.cutEdges()).isEqualTo(unit.cutEdges());
    }

    @Test
    void heterogeneousCapacities_cutValueIsTheSumNotTheCount() {
        // Two routes: north capacity 5, south capacity 1. Bandwidth is 6; two passages.
        // A unit-only implementation reports 2 and hides the fat uplink.
        MazeGrid ring = ring();
        Point s = new Point(0, 0);
        Point t = new Point(1, 1);

        MinCut cut = MazeFlow.minCut(ring, s, t, (from, to) -> north(from, to) ? 5 : 1);

        assertThat(cut.cutSize()).isEqualTo(6);
        assertThat(cut.cutEdges()).hasSize(2);
        assertThat(connected(ring, s, t, Set.copyOf(cut.cutEdges()))).isFalse();
    }

    @Test
    void zeroCapacitySealsAPassageForFlow() {
        MazeGrid ring = ring();
        Point s = new Point(0, 0);
        Point t = new Point(1, 1);

        MinCut cut = MazeFlow.minCut(ring, s, t, (from, to) -> north(from, to) ? 0 : 1);

        assertThat(cut.cutSize()).isEqualTo(1);
    }

    @Test
    void negativeCapacityIsRejected() {
        MazeGrid ring = ring();

        assertThatThrownBy(
                        () -> MazeFlow.minCut(ring, new Point(0, 0), new Point(1, 1), (from, to) -> -1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining(">= 0");
    }

    // ---------- helpers ----------

    /** 2×2 ring: opposite corners have two edge-disjoint routes. */
    private static MazeGrid ring() {
        MazeGrid grid = new MazeGrid(2, 2);
        carve(grid, 0, 0, 0, 1);
        carve(grid, 0, 1, 1, 1);
        carve(grid, 1, 1, 1, 0);
        carve(grid, 1, 0, 0, 0);
        return grid;
    }

    /** The two passages of the top-right path: (0,0)—(0,1) and (0,1)—(1,1). */
    private static boolean north(Point a, Point b) {
        return Math.min(a.row(), b.row()) == 0 && Math.max(a.col(), b.col()) == 1;
    }

    private static void carve(MazeGrid grid, int r1, int c1, int r2, int c2) {
        grid.carve(new Point(r1, c1), new Point(r2, c2));
    }

    /** BFS from {@code s} to {@code t} over open passages, treating {@code blocked} passages as sealed. */
    private static boolean connected(MazeGrid grid, Point s, Point t, Set<Passage> blocked) {
        Set<Point> seen = new HashSet<>();
        Deque<Point> queue = new ArrayDeque<>();
        seen.add(s);
        queue.add(s);
        while (!queue.isEmpty()) {
            Point u = queue.poll();
            if (u.equals(t)) {
                return true;
            }
            for (Point v : grid.openNeighbors(u)) {
                if (!blocked.contains(new Passage(u, v)) && seen.add(v)) {
                    queue.add(v);
                }
            }
        }
        return false;
    }
}
