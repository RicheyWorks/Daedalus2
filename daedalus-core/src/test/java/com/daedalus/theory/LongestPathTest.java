// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.Braider;
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
    void tinyBudget_fallsBackToTheShortestRoute_labelledInexact() {
        MazeGrid grid = new MazeGrid(2, 3);
        carve(grid, 0, 0, 0, 1);
        carve(grid, 0, 1, 0, 2);
        carve(grid, 0, 2, 1, 2);
        carve(grid, 1, 2, 1, 1);
        carve(grid, 1, 1, 1, 0);
        carve(grid, 1, 0, 0, 0);

        LongPath capped = LongestPath.longestSimplePath(grid, new Point(0, 0), new Point(0, 2), 1L);

        // This test used to assert length -1 and an empty path, which was the old contract: a
        // budget too small to reach the goal produced no answer at all. That contract was wrong
        // in the way that matters — measured on a 41x41 braided maze at the DEFAULT budget, the
        // search wandered two million cells without once arriving, and a "hardest route" feature
        // answered "there is no route" about a maze anyone can walk. The incumbent is now seeded
        // with the BFS shortest path, so a starved search degrades to the short way round rather
        // than to nothing — still honestly flagged inexact.
        assertThat(capped.exact()).isFalse();
        assertThat(capped.length()).isEqualTo(2);
        assertThat(capped.path()).containsExactly(new Point(0, 0), new Point(0, 1), new Point(0, 2));
        assertSimpleWalk(grid, capped);
    }

    @Test
    void noRouteAtAll_stillReportsMinusOne() {
        // The fallback must not invent a route where none exists: two cells, no passage.
        MazeGrid grid = new MazeGrid(1, 2);

        LongPath none = LongestPath.longestSimplePath(grid, new Point(0, 0), new Point(0, 1));

        assertThat(none.length()).isEqualTo(-1);
        assertThat(none.path()).isEmpty();
    }

    @Test
    void aRouteIsAlwaysFoundOnTheBraidedSizesThatUsedToReturnNothing() {
        // The measured regression case. At 41x41 braid 0.5 (and 61x61 braid 1.0) the DFS spends
        // its whole budget in the cycle-rich middle of the maze and never reaches the goal; the
        // old code returned -1. The floor is now the shortest route, so the answer is a real
        // walk whatever the search manages to do with its budget.
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(41, 41, 7L, new MazeStats());
        Braider.braid(grid, 0.5, 7L);
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        int shortest = MazeMetrics.shortestPath(grid, grid.start(), grid.goal()).size() - 1;

        LongPath hardest = LongestPath.hardestRoute(grid);

        assertThat(hardest.length())
                .as("the hardest route can never be shorter than the shortest one")
                .isGreaterThanOrEqualTo(shortest);
        assertThat(hardest.path()).isNotEmpty();
        assertSimpleWalk(grid, hardest);
    }

    @Test
    void aPerfectMazeTallerThanTheJvmStackDoesNotBlowIt() {
        // 300x300 is a tree whose unique start-to-goal path runs tens of thousands of cells
        // deep. The recursive version of this search threw StackOverflowError on every perfect
        // maze from 200x200 up — an Error escaping a public API, on a size the REST surface
        // accepts (rows and cols are capped at 512, not 199). Braided mazes never caught it
        // because the visit budget ran out long before the stack did.
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(300, 300, 3L, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);

        LongPath hardest = LongestPath.hardestRoute(grid);

        assertThat(hardest.length())
                .as("a 300x300 tree's unique route is far deeper than the default JVM stack")
                .isGreaterThan(10_000);
        assertThat(hardest.exact()).isTrue();
        assertSimpleWalk(grid, hardest);
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
