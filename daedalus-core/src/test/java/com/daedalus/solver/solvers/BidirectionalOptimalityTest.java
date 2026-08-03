// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link BidirectionalSolver} claims to return "the same shortest path as BFS on unweighted
 * grids". On a perfect maze that's trivially true — there is only one route — so the claim is
 * never actually exercised by the other tests.
 *
 * <p>This test braids the maze first ({@link Braider}), creating loops and therefore genuine route
 * choice, which is the only situation where a bidirectional search's termination rule can go
 * wrong: stopping at the *first* frontier touch can return a path one step longer than optimal,
 * because a cheaper meeting point may still be pending in the frontier.
 */
class BidirectionalOptimalityTest {

    @Test
    void bidirectional_matchesBfsShortestLength_onBraidedMazes() {
        for (long seed = 1; seed <= 40; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, seed);
            Braider.braid(grid, 1.0, seed);

            List<Point> bidirectional =
                    new BidirectionalSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
            List<Point> bfs =
                    new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());

            assertThat(bidirectional)
                    .as("braided maze seed %d: bidirectional must be as short as BFS", seed)
                    .hasSameSizeAs(bfs);
        }
    }

    @Test
    void bidirectional_returnsAValidConnectedWalk_onBraidedMazes() {
        for (long seed = 1; seed <= 10; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator().generate(10, 10, seed);
            Braider.braid(grid, 1.0, seed);

            List<Point> path =
                    new BidirectionalSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());

            assertThat(path).isNotEmpty();
            assertThat(path.get(0)).isEqualTo(grid.start());
            assertThat(path.get(path.size() - 1)).isEqualTo(grid.goal());
            for (int i = 0; i + 1 < path.size(); i++) {
                assertThat(grid.openNeighbors(path.get(i)))
                        .as("seed %d step %d", seed, i)
                        .contains(path.get(i + 1));
            }
        }
    }

    /**
     * The performance claim, which is load-bearing for the correctness one.
     *
     * <p>This solver stops at the first frontier touch. Its javadoc concedes that a naive
     * first-touch stop can, in a general graph, return a path one step longer than optimal, and
     * argues the case is safe here because expansion always comes from the <em>smaller</em>
     * frontier — the balance keeps the two search depths close enough that the pathology cannot
     * arise. That argument is only as good as the balancing actually happening, and mutation
     * found it unpinned: flipping the comparison so the <em>larger</em> frontier is expanded
     * returns byte-identical paths on every fixture in this class and in the property suite. The
     * b^(d/2) advantage evaporates, every correctness assertion stays green, and the premise the
     * first-touch stop rests on is gone with it.
     *
     * <p>Two things had to be measured before this could be asserted, and both changed the test.
     *
     * <p><b>"Fewer cells than BFS" does not discriminate.</b> That was the first version of this
     * assertion and it is nearly worthless: with the larger frontier expanded, this solver still
     * explores fewer cells than BFS on every fixture measured — by about half a percent. The
     * mutant beats BFS by a nose and passes. What separates them is the <em>margin</em>: 0.67 of
     * BFS's expansions on average with the balance in place, 0.997 without it. So the threshold
     * is the assertion, and 0.85 sits in a gap between a measured worst case of 0.743 and a
     * measured mutant best case of 0.991.
     *
     * <p><b>Perfect mazes are the wrong fixture, and not for the usual reason.</b> On 120 perfect
     * mazes across four sizes, bidirectional expanded <em>more</em> cells than BFS on 34 of them —
     * the advantage is exponential in branching factor, and a perfect maze is a tree of long
     * one-wide corridors where there is barely any branching to halve. Worse, the goal-side search
     * spends its budget on dead ends hanging off the far side of the goal, which BFS never reaches
     * because it stops when it pops the goal. Braiding is what puts real branching in, which is
     * the same reason the two tests above braid — a different consequence of the same fact.
     */
    @Test
    void bidirectional_expandsFarFewerCellsThanBfs_whichIsTheWholePointOfIt() {
        List<String> tooClose = new ArrayList<>();
        double worst = 0.0;

        for (long seed = 1; seed <= 8; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator()
                    .generate(41, 41, seed, new MazeStats());
            Braider.braid(grid, 1.0, seed);

            MazeStats bidi = new MazeStats();
            MazeStats bfs = new MazeStats();
            new BidirectionalSolver().solve(grid, grid.start(), grid.goal(), bidi);
            new BfsSolver().solve(grid, grid.start(), grid.goal(), bfs);

            double ratio = (double) bidi.cellsExplored() / bfs.cellsExplored();
            worst = Math.max(worst, ratio);
            if (ratio > 0.85) {
                tooClose.add("seed %d: %d expansions against BFS's %d (%.3f)"
                        .formatted(seed, bidi.cellsExplored(), bfs.cellsExplored(), ratio));
            }
        }

        assertThat(tooClose)
                .as("expanding the smaller frontier is what buys the b^(d/2) advantage and what "
                        + "makes the first-touch stop safe; measured at 0.67 of BFS on average "
                        + "and 0.743 at worst, against 0.997 when the balance is removed. Worst "
                        + "here was %.3f. Fixtures at or above the 0.85 line: %s", worst, tooClose)
                .isEmpty();
    }
}
