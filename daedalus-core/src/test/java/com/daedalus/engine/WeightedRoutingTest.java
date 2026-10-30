// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.DijkstraSolver;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Routing-level test for {@link WeightedMazeGrid}: with per-cell weights in play,
 * cost-aware solvers should prefer a longer-but-cheaper detour over a short corridor
 * that contains a heavily-weighted cell. Plain {@link MazeGrid} (uniform cost) must
 * keep its old behaviour — picking the short path — so the change to the solvers is
 * a transparent generalisation, not a behavioural break.
 *
 * <h3>Test geometry</h3>
 *
 * <pre>{@code
 *   (0,0) ─ (0,1) ─ (0,2) ─ (0,3) ─ (0,4)     top corridor: 4 cells entered
 *     │                                 │
 *   (1,0)                             (1,4)
 *     │                                 │
 *   (2,0) ─ (2,1) ─ (2,2) ─ (2,3) ─ (2,4)     detour:       8 cells entered
 * }</pre>
 *
 * <p>Start = {@code (0,0)}, goal = {@code (0,4)}. With every weight at the uniform
 * default of {@code 1.0} the top corridor costs {@code 4}, the detour costs {@code 8},
 * so any optimal solver picks the top. Spike {@code weightOf(0,2)} to {@code 100.0}
 * and the top corridor's cost balloons to {@code 103}, so the detour wins {@code 8}
 * to {@code 103}. We verify the two solvers under both regimes.
 */
class WeightedRoutingTest {

    private static final Point START = new Point(0, 0);
    private static final Point GOAL = new Point(0, 4);

    /** Carve the two-corridor topology into any {@link MazeGrid} (plain or weighted). */
    private static void carveTwoCorridorMaze(MazeGrid g) {
        // Top corridor
        g.carve(new Point(0, 0), new Point(0, 1));
        g.carve(new Point(0, 1), new Point(0, 2));
        g.carve(new Point(0, 2), new Point(0, 3));
        g.carve(new Point(0, 3), new Point(0, 4));
        // Bottom corridor
        g.carve(new Point(2, 0), new Point(2, 1));
        g.carve(new Point(2, 1), new Point(2, 2));
        g.carve(new Point(2, 2), new Point(2, 3));
        g.carve(new Point(2, 3), new Point(2, 4));
        // Left vertical link
        g.carve(new Point(0, 0), new Point(1, 0));
        g.carve(new Point(1, 0), new Point(2, 0));
        // Right vertical link
        g.carve(new Point(0, 4), new Point(1, 4));
        g.carve(new Point(1, 4), new Point(2, 4));

        g.setStart(START);
        g.setGoal(GOAL);
    }

    @Test
    void plainGridDijkstraTakesShortTopCorridor() {
        MazeGrid grid = new MazeGrid(3, 5);
        carveTwoCorridorMaze(grid);

        List<Point> path = new DijkstraSolver().solve(grid, START, GOAL, new MazeStats());

        // 5 cells on the path: start + 4 entered = (0,0),(0,1),(0,2),(0,3),(0,4)
        assertThat(path).hasSize(5);
        assertThat(path).contains(new Point(0, 2));   // through the middle of the top
        assertThat(path).doesNotContain(new Point(2, 2));
    }

    @Test
    void plainGridAStarTakesShortTopCorridor() {
        MazeGrid grid = new MazeGrid(3, 5);
        carveTwoCorridorMaze(grid);

        List<Point> path = new AStarSolver().solve(grid, START, GOAL, new MazeStats());

        assertThat(path).hasSize(5);
        assertThat(path).contains(new Point(0, 2));
        assertThat(path).doesNotContain(new Point(2, 2));
    }

    @Test
    void weightedGridDijkstraDetoursAroundExpensiveCell() {
        WeightedMazeGrid grid = new WeightedMazeGrid(3, 5);
        carveTwoCorridorMaze(grid);
        grid.setWeight(new Point(0, 2), 100.0);   // make the short path prohibitively expensive

        List<Point> path = new DijkstraSolver().solve(grid, START, GOAL, new MazeStats());

        // Detour: (0,0) -> (1,0) -> (2,0) -> (2,1) -> (2,2) -> (2,3) -> (2,4) -> (1,4) -> (0,4)
        assertThat(path).hasSize(9);
        assertThat(path).contains(new Point(2, 2));
        assertThat(path).doesNotContain(new Point(0, 2));
    }

    @Test
    void weightedGridAStarDetoursAroundExpensiveCell() {
        WeightedMazeGrid grid = new WeightedMazeGrid(3, 5);
        carveTwoCorridorMaze(grid);
        grid.setWeight(new Point(0, 2), 100.0);

        List<Point> path = new AStarSolver().solve(grid, START, GOAL, new MazeStats());

        assertThat(path).hasSize(9);
        assertThat(path).contains(new Point(2, 2));
        assertThat(path).doesNotContain(new Point(0, 2));
    }

    @Test
    void modestWeightDoesNotFlipTheChoice() {
        // With weight(0,2) = 2.5, top cost = 1 + 2.5 + 1 + 1 = 5.5; detour cost = 8.
        // Both solvers must still pick the top corridor.
        WeightedMazeGrid grid = new WeightedMazeGrid(3, 5);
        carveTwoCorridorMaze(grid);
        grid.setWeight(new Point(0, 2), 2.5);

        List<Point> dPath = new DijkstraSolver().solve(grid, START, GOAL, new MazeStats());
        List<Point> aPath = new AStarSolver().solve(grid, START, GOAL, new MazeStats());

        assertThat(dPath).hasSize(5);
        assertThat(aPath).hasSize(5);
    }

    @Test
    void weightedGridWithUniformDefaultsMatchesPlainGrid() {
        // A WeightedMazeGrid with no setWeight calls must produce the same path as a plain
        // MazeGrid — locking in that the change to the solvers is a transparent generalisation.
        MazeGrid plain = new MazeGrid(3, 5);
        carveTwoCorridorMaze(plain);
        WeightedMazeGrid weighted = new WeightedMazeGrid(3, 5);
        carveTwoCorridorMaze(weighted);

        List<Point> plainDijkstra = new DijkstraSolver().solve(plain, START, GOAL, new MazeStats());
        List<Point> weightedDijkstra = new DijkstraSolver().solve(weighted, START, GOAL, new MazeStats());
        List<Point> plainAStar = new AStarSolver().solve(plain, START, GOAL, new MazeStats());
        List<Point> weightedAStar = new AStarSolver().solve(weighted, START, GOAL, new MazeStats());

        assertThat(weightedDijkstra).isEqualTo(plainDijkstra);
        assertThat(weightedAStar).isEqualTo(plainAStar);
    }
}
