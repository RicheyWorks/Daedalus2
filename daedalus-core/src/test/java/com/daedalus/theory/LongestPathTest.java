// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.DijkstraSolver;
import com.daedalus.theory.LongestPath.LongPath;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link LongestPath}. On a braided maze the longest simple route is strictly longer than the
 * shortest (and finding it needs search); on a perfect maze it collapses to the unique route.
 */
class LongestPathTest {

    @Test
    void braidedRing_longestRouteTakesTheLongWayAround() {
        // 2x3 ring (6-cycle): (0,0)-(0,1)-(0,2)-(1,2)-(1,1)-(1,0)-(0,0). Start (0,0), goal (0,2).
        MazeGrid grid = new MazeGrid(2, 3);
        carve(grid, 0, 0, 0, 1);
        carve(grid, 0, 1, 0, 2);
        carve(grid, 0, 2, 1, 2);
        carve(grid, 1, 2, 1, 1);
        carve(grid, 1, 1, 1, 0);
        carve(grid, 1, 0, 0, 0);

        LongPath longest = LongestPath.longestSimplePath(grid, new Point(0, 0), new Point(0, 2));

        // Short route is 2 steps; the long way around is 4 steps through the bottom row.
        assertThat(longest.length()).isEqualTo(4);
        assertThat(longest.path()).hasSize(5).contains(new Point(1, 0), new Point(1, 1), new Point(1, 2));
        assertThat(longest.exact()).isTrue();
        assertSimpleWalk(grid, longest);
    }

    @Test
    void perfectMaze_longestRouteIsTheUniquePath_matchingDijkstra() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(10, 10, 42L);

        LongPath longest = LongestPath.longestSimplePath(grid, grid.start(), grid.goal());
        List<Point> dijkstra = new DijkstraSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());

        // In a tree there is exactly one simple path between two cells, so longest == shortest.
        assertThat(longest.path()).isEqualTo(dijkstra);
        assertThat(longest.exact()).isTrue();
        assertSimpleWalk(grid, longest);
    }

    @Test
    void startEqualsGoal_isLengthZero() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(6, 6, 1L);
        Point p = new Point(2, 2);

        LongPath longest = LongestPath.longestSimplePath(grid, p, p);

        assertThat(longest.length()).isZero();
        assertThat(longest.path()).containsExactly(p);
        assertThat(longest.exact()).isTrue();
    }

    @Test
    void tinyBudget_returnsInexactResult_notAWrongOne() {
        MazeGrid grid = new MazeGrid(2, 3);
        carve(grid, 0, 0, 0, 1);
        carve(grid, 0, 1, 0, 2);
        carve(grid, 0, 2, 1, 2);
        carve(grid, 1, 2, 1, 1);
        carve(grid, 1, 1, 1, 0);
        carve(grid, 1, 0, 0, 0);

        LongPath capped = LongestPath.longestSimplePath(grid, new Point(0, 0), new Point(0, 2), 1L);

        // One cell visited can't reach the goal — reported honestly as inexact, no fabricated path.
        assertThat(capped.exact()).isFalse();
        assertThat(capped.length()).isEqualTo(-1);
        assertThat(capped.path()).isEmpty();
    }

    @Test
    void isDeterministic() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(8, 8, 99L);

        assertThat(LongestPath.hardestRoute(grid)).isEqualTo(LongestPath.hardestRoute(grid));
    }

    // ---------- helpers ----------

    private static void carve(MazeGrid grid, int r1, int c1, int r2, int c2) {
        grid.carve(new Point(r1, c1), new Point(r2, c2));
    }

    private static void assertSimpleWalk(MazeGrid grid, LongPath lp) {
        List<Point> path = lp.path();
        assertThat(new HashSet<>(path)).hasSameSizeAs(path); // simple: no repeated cell
        assertThat(path.get(0)).isEqualTo(lp.from());
        assertThat(path.get(path.size() - 1)).isEqualTo(lp.to());
        assertThat(lp.length()).isEqualTo(path.size() - 1);
        for (int i = 0; i + 1 < path.size(); i++) {
            assertThat(grid.openNeighbors(path.get(i))).contains(path.get(i + 1));
        }
    }
}
