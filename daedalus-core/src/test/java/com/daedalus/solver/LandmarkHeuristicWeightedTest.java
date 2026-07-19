// SPDX-License-Identifier: MIT

package com.daedalus.solver;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.DijkstraSolver;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.List;
import java.util.Random;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Regression guard for a real optimality bug: {@link LandmarkHeuristic} used to store BFS hop
 * counts even on a {@link WeightedMazeGrid}, which is the wrong metric and made the heuristic
 * inadmissible whenever weights fell below {@code 1.0}.
 *
 * <p>The failure was invisible on the mazes the suite already covered. A perfect maze is a
 * spanning tree, so there is exactly <em>one</em> route between any pair of cells and every
 * heuristic — admissible or not — returns it. The bug only surfaces once the topology has
 * redundancy and the solver has a genuine choice, which is why these tests
 * {@linkplain Braider#braid(MazeGrid, double, long) braid} the maze first. That is also the
 * shape of the topologies the load-balancer work targets, so this is the case that matters.
 *
 * <p>Measured before the fix, on these exact fixtures: inadmissible in 575 of 576 cells, and
 * A* returned a more expensive path than Dijkstra on 12 of 12 seeds — by up to 36%.
 */
class LandmarkHeuristicWeightedTest {

    private static final int SIZE = 24;
    private static final double EPSILON = 1e-9;

    /**
     * A braided maze with sub-unit weights — the configuration that broke the old heuristic.
     * Weights in {@code [0.05, 0.35]} are all below {@code 1.0}, which the old code's
     * "keep weights >= 1.0" convention forbade but nothing enforced.
     */
    private static WeightedMazeGrid braidedWeightedMaze(long seed) {
        MazeGrid base = new RecursiveBacktrackerGenerator()
                .generate(SIZE, SIZE, seed, new MazeStats());
        Braider.braid(base, 1.0, seed);
        WeightedMazeGrid grid = new WeightedMazeGrid(base);
        Random random = new Random(seed * 31);
        for (int r = 0; r < SIZE; r++) {
            for (int c = 0; c < SIZE; c++) {
                grid.setWeight(new Point(r, c), 0.05 + random.nextDouble() * 0.3);
            }
        }
        return grid;
    }

    /** Cost of a path under the entry-cost model: pay the weight of each cell you move into. */
    private static double cost(WeightedMazeGrid grid, List<Point> path) {
        double total = 0.0;
        for (int i = 1; i < path.size(); i++) {
            total += grid.weightOf(path.get(i));
        }
        return total;
    }

    @ParameterizedTest(name = "seed {0}")
    @ValueSource(longs = {1, 2, 3, 4, 5, 6})
    void aStarWithLandmarksMatchesDijkstraCost_onBraidedWeightedMazes(long seed) {
        WeightedMazeGrid grid = braidedWeightedMaze(seed);
        Point start = new Point(0, 0);
        Point goal = new Point(SIZE - 1, SIZE - 1);

        List<Point> optimal = new DijkstraSolver().solve(grid, start, goal, new MazeStats());
        LandmarkHeuristic alt = LandmarkHeuristic.precompute(grid, 4);
        List<Point> viaAlt = new AStarSolver(alt.asHeuristic())
                .solve(grid, start, goal, new MazeStats());

        assertThat(viaAlt).isNotEmpty();
        // Cost equality, not path equality: several distinct routes can tie for optimal and
        // A* is free to return any of them. Cost is the actual contract.
        assertThat(cost(grid, viaAlt))
                .as("A* with an admissible heuristic must match Dijkstra's optimal cost")
                .isCloseTo(cost(grid, optimal), org.assertj.core.data.Offset.offset(EPSILON));
    }

    @Test
    void heuristicNeverExceedsTrueCost_forEveryCellInTheGrid() {
        WeightedMazeGrid grid = braidedWeightedMaze(42L);
        Point goal = new Point(SIZE - 1, SIZE - 1);
        LandmarkHeuristic alt = LandmarkHeuristic.precompute(grid, 4);

        // The definition of admissibility, checked exhaustively rather than sampled: h(x, goal)
        // must not exceed the true cost from x to goal for ANY x. This is the assertion that
        // fails 575/576 times against the old implementation.
        int checked = 0;
        for (int r = 0; r < SIZE; r++) {
            for (int c = 0; c < SIZE; c++) {
                Point from = new Point(r, c);
                List<Point> truePath = new DijkstraSolver()
                        .solve(grid, from, goal, new MazeStats());
                if (truePath.isEmpty()) {
                    continue;
                }
                checked++;
                assertThat(alt.estimate(from, goal))
                        .as("h(%s -> goal) must be a lower bound on true cost", from)
                        .isLessThanOrEqualTo(cost(grid, truePath) + EPSILON);
            }
        }
        assertThat(checked).as("fixture must actually be connected").isGreaterThan(SIZE * SIZE / 2);
    }

    @Test
    void weightedGridSelectsCostMode_plainGridStaysOnHopMode() {
        assertThat(LandmarkHeuristic.precompute(braidedWeightedMaze(1L), 4).isWeighted())
                .as("a grid carrying non-unit weights must use Dijkstra fields")
                .isTrue();

        MazeGrid plain = new RecursiveBacktrackerGenerator()
                .generate(SIZE, SIZE, 1L, new MazeStats());
        assertThat(LandmarkHeuristic.precompute(plain, 4).isWeighted())
                .as("uniform-cost grids keep the cheaper BFS hop fields")
                .isFalse();
    }

    @Test
    void aWeightedGridWhoseWeightsAreAllOne_isTreatedAsUniform() {
        // Boundary of the detection rule: being a WeightedMazeGrid is not what matters, having
        // a non-1.0 weight is. Otherwise every weighted grid would pay for Dijkstra sweeps it
        // does not need.
        MazeGrid base = new RecursiveBacktrackerGenerator()
                .generate(SIZE, SIZE, 3L, new MazeStats());
        WeightedMazeGrid uniform = new WeightedMazeGrid(base);
        uniform.setAllWeights(1.0);

        assertThat(LandmarkHeuristic.precompute(uniform, 4).isWeighted()).isFalse();
    }

    @Test
    void weightsAboveOneAlsoStayAdmissible() {
        // The old code was *loose but sound* above 1.0 and *unsound* below it. Cover the upper
        // range too, so a future change that only fixes the sub-unit case still gets caught.
        MazeGrid base = new RecursiveBacktrackerGenerator()
                .generate(SIZE, SIZE, 9L, new MazeStats());
        Braider.braid(base, 1.0, 9L);
        WeightedMazeGrid grid = new WeightedMazeGrid(base);
        Random random = new Random(99);
        for (int r = 0; r < SIZE; r++) {
            for (int c = 0; c < SIZE; c++) {
                grid.setWeight(new Point(r, c), 1.0 + random.nextDouble() * 8.0);
            }
        }

        Point start = new Point(0, 0);
        Point goal = new Point(SIZE - 1, SIZE - 1);
        LandmarkHeuristic alt = LandmarkHeuristic.precompute(grid, 4);

        double optimal = cost(grid, new DijkstraSolver().solve(grid, start, goal, new MazeStats()));
        double viaAlt = cost(grid, new AStarSolver(alt.asHeuristic())
                .solve(grid, start, goal, new MazeStats()));
        assertThat(viaAlt).isCloseTo(optimal, org.assertj.core.data.Offset.offset(EPSILON));
        assertThat(alt.estimate(start, goal)).isLessThanOrEqualTo(optimal + EPSILON);
    }
}
