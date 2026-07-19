// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

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
}
