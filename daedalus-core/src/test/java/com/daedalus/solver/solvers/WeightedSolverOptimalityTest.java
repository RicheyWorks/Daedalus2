// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.MazeSolver;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The optimal solvers, on grids that actually cost something.
 *
 * <p>{@code SolverBraidedMazePropertyTest} opens by explaining why it braids: a perfect maze has
 * exactly one route between any two cells, so every solver returns the optimal path whatever it
 * does internally, and a suite built on perfect mazes proves nothing about optimality. That
 * reasoning is right and it stops one dimension short. Braided mazes give the solvers a *choice*
 * of route; uniform costs still make every choice of equal length the same answer, so the
 * arithmetic that separates a cost-aware solver from a hop-counting one is never exercised.
 *
 * <p>Mutation is what sent this test looking, and then corrected it. Deleting
 * {@code tentative < dist[next]} from Dial's relaxation — the textbook way this algorithm fails —
 * passes the whole core suite. The first reading was that weights would expose it. They do not,
 * and the reason is worth more than the test would have been: under this engine's <em>entry-cost</em>
 * model every edge into a node costs the same, so a node's first relaxation is always its cheapest
 * and that branch cannot be taken. Instrumented over 640 weighted grids it fired 0 times in 231,734
 * relaxations. It is dead code guarding against a {@code Graph} contract change, now documented as
 * such in {@link DialSolver} rather than pinned by a test that could never fail.
 *
 * <p>What weights <em>do</em> expose is below, and it is a different thing entirely: which solvers
 * read {@code weightOf} at all. That distinction lived in one service's prose and in no test.
 *
 * <p>So this sweeps braided mazes with entry costs and holds every optimal solver to Dijkstra's
 * <em>cost</em> rather than to anyone's hop count. Two further properties come along for the ride
 * because they are only reachable here: Dial's bucket array has to grow for a single heavy cell,
 * and Dial documents that it refuses fractional weights rather than silently rounding them.
 */
class WeightedSolverOptimalityTest {

    /** Cost of walking a route: the entry weight of every cell after the first. */
    private static double costOf(WeightedMazeGrid grid, List<Point> path) {
        double total = 0.0;
        for (int i = 1; i < path.size(); i++) {
            total += grid.weightOf(path.get(i).row(), path.get(i).col());
        }
        return total;
    }

    /**
     * A braided maze whose cells carry integer entry costs — integer so that Dial is in scope,
     * since it is the solver with the most arithmetic to get wrong.
     */
    private static WeightedMazeGrid weightedBraided(int size, long seed, double braid) {
        MazeGrid base = new RecursiveBacktrackerGenerator().generate(size, size, seed, new MazeStats());
        Braider.braid(base, braid, seed);
        WeightedMazeGrid grid = new WeightedMazeGrid(base);
        Random rng = new Random(seed * 31 + 7);
        for (int r = 0; r < size; r++) {
            for (int c = 0; c < size; c++) {
                // 1..9, so a detour can genuinely beat a shorter route and no single cell
                // dominates the whole grid.
                grid.setWeight(new Point(r, c), 1 + rng.nextInt(9));
            }
        }
        return grid;
    }

    /**
     * The split this test exists to record, and which nothing else in the suite states.
     *
     * <p>{@code SolverBraidedMazePropertyTest} keeps one roster, {@code OPTIMAL}, holding seven
     * solvers to BFS's <em>hop count</em>. That is the right assertion on a uniform grid and it
     * hides a second distinction entirely: of those seven, only Dijkstra, A* and Dial read
     * {@link com.daedalus.engine.MazeGrid#weightOf}. BFS, IDA* and dead-end filling optimise
     * hops, so on a weighted maze they return a legal shortest-<em>hop</em> route that can cost
     * more than the cheapest one — measured here at 116 against 108, and 199 against 174.
     *
     * <p>That is not a defect in IDA*: {@code TrafficService}'s javadoc names exactly Dijkstra,
     * A* and Dial as the weight-aware set, and the traffic feature routes around congestion on
     * that basis. It is a distinction that lived in one service's prose and in no test, which is
     * how a fourth cost-aware solver would arrive one day without anyone noticing it counts hops.
     */
    private static final List<MazeSolver> COST_AWARE =
            List.of(new DijkstraSolver(), new DialSolver(), new AStarSolver());

    /** Optimal by hop count, and therefore free to be pricier — never cheaper — under weights. */
    private static final List<MazeSolver> HOP_COUNTERS =
            List.of(new BfsSolver(), new IDAStarSolver(), new DeadEndFillingSolver());

    private static List<MazeSolver> optimalSolvers() {
        List<MazeSolver> all = new ArrayList<>(COST_AWARE);
        all.addAll(HOP_COUNTERS);
        return all;
    }

    @Test
    void everyCostAwareSolverMatchesDijkstrasCost_notItsHopCount() {
        List<String> failures = new ArrayList<>();

        for (long seed : new long[] {1L, 7L, 42L, 99L}) {
            for (double braid : new double[] {0.2, 0.5}) {
                WeightedMazeGrid grid = weightedBraided(11, seed, braid);
                Point start = grid.start();
                Point goal = grid.goal();
                List<Point> reference = new DijkstraSolver().solve(grid, start, goal, new MazeStats());
                double best = costOf(grid, reference);

                for (MazeSolver solver : optimalSolvers()) {
                    List<Point> path = solver.solve(grid, start, goal, new MazeStats());
                    if (path.isEmpty()) {
                        failures.add("%s seed=%d braid=%.1f: found no route where Dijkstra did"
                                .formatted(solver.id(), seed, braid));
                        continue;
                    }
                    double cost = costOf(grid, path);
                    // The hop counters are on the roster as controls: they are allowed to be
                    // worse under weights, and asserting otherwise would be asserting that
                    // weights do not matter. What nothing may ever be is cheaper than optimal —
                    // that would mean Dijkstra is wrong.
                    boolean hopCounter = HOP_COUNTERS.stream()
                            .anyMatch(s -> s.id().equals(solver.id()));
                    if (cost < best - 1e-9) {
                        failures.add("%s seed=%d braid=%.1f: %.1f beats Dijkstra's %.1f, so one "
                                .formatted(solver.id(), seed, braid, cost, best)
                                + "of them is wrong");
                    } else if (!hopCounter && cost > best + 1e-9) {
                        failures.add("%s seed=%d braid=%.1f: %.1f against an optimal %.1f"
                                .formatted(solver.id(), seed, braid, cost, best));
                    }
                }
            }
        }

        assertThat(failures)
                .as("a cost-aware solver that returns a legal but pricier route is the exact "
                        + "failure a uniform-cost suite cannot see: %s", failures)
                .isEmpty();
    }

    @Test
    void bfsIsGenuinelyBeatenOnCost_soTheSweepAboveIsNotVacuous() {
        // Without this, "every optimal solver matches Dijkstra" would still pass if the fixtures
        // happened to make the shortest route also the cheapest one — the same vacuity that made
        // perfect mazes useless for testing optimality. At least one fixture must separate them.
        int separated = 0;
        for (long seed : new long[] {1L, 7L, 42L, 99L}) {
            WeightedMazeGrid grid = weightedBraided(11, seed, 0.5);
            double bfs = costOf(grid, new BfsSolver()
                    .solve(grid, grid.start(), grid.goal(), new MazeStats()));
            double dijkstra = costOf(grid, new DijkstraSolver()
                    .solve(grid, grid.start(), grid.goal(), new MazeStats()));
            if (bfs > dijkstra + 1e-9) {
                separated++;
            }
        }

        assertThat(separated)
                .as("on every fixture the shortest route was also the cheapest, so the sweep "
                        + "above proves nothing about cost")
                .isPositive();
    }

    @Test
    void dialGrowsItsBucketArrayForACellHeavierThanTheArrayIsLong() {
        // Dial files a node at distance d in bucket[d] and grows the array on demand. The growth
        // takes Math.max(tentative + 1, length * 2), and the + 1 only matters when one edge
        // jumps past twice the current length — 64 buckets initially, so a single cell costing
        // more than 128 is what reaches it. The maze API allows up to 1000.
        WeightedMazeGrid grid = new WeightedMazeGrid(3, 7);
        for (int c = 0; c < 6; c++) {
            grid.carve(new Point(1, c), new Point(1, c + 1));
        }
        grid.setStart(new Point(1, 0));
        grid.setGoal(new Point(1, 6));
        grid.setWeight(new Point(1, 3), 400.0);

        List<Point> path = new DialSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());

        assertThat(path).as("the only corridor there is").hasSize(7);
        assertThat(costOf(grid, path)).isEqualTo(405.0);
    }

    @Test
    void dialRefusesFractionalWeightsInsteadOfRoundingThemSilently() {
        // Its own javadoc: bucketing needs integer keys, and the honest response to 1.5 is to
        // send the caller to Dijkstra rather than to quietly solve a different maze.
        WeightedMazeGrid grid = new WeightedMazeGrid(3, 5);
        for (int c = 0; c < 4; c++) {
            grid.carve(new Point(1, c), new Point(1, c + 1));
        }
        grid.setStart(new Point(1, 0));
        grid.setGoal(new Point(1, 4));
        grid.setWeight(new Point(1, 2), 1.5);

        assertThat(org.assertj.core.api.Assertions.catchThrowable(
                () -> new DialSolver().solve(grid, grid.start(), grid.goal(), new MazeStats())))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("DijkstraSolver");
    }
}
