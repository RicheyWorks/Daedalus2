// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link DialSolver} (bucket-queue Dijkstra). Its optimal path must match {@link DijkstraSolver}
 * on uniform and integer-weighted grids, it must route around expensive cells, and it must refuse
 * fractional weights (where bucketing is ill-defined).
 */
class DialSolverTest {

    private static final Point START = new Point(0, 0);
    private static final Point GOAL = new Point(0, 4);

    /** Two-corridor maze (from WeightedRoutingTest): short top (cost 4), long detour (cost 8). */
    private static void carveTwoCorridorMaze(MazeGrid g) {
        g.carve(new Point(0, 0), new Point(0, 1));
        g.carve(new Point(0, 1), new Point(0, 2));
        g.carve(new Point(0, 2), new Point(0, 3));
        g.carve(new Point(0, 3), new Point(0, 4));
        g.carve(new Point(2, 0), new Point(2, 1));
        g.carve(new Point(2, 1), new Point(2, 2));
        g.carve(new Point(2, 2), new Point(2, 3));
        g.carve(new Point(2, 3), new Point(2, 4));
        g.carve(new Point(0, 0), new Point(1, 0));
        g.carve(new Point(1, 0), new Point(2, 0));
        g.carve(new Point(0, 4), new Point(1, 4));
        g.carve(new Point(1, 4), new Point(2, 4));
        g.setStart(START);
        g.setGoal(GOAL);
    }

    @Test
    void uniformGrid_takesShortTopCorridor_matchingDijkstra() {
        MazeGrid grid = new MazeGrid(3, 5);
        carveTwoCorridorMaze(grid);

        List<Point> dial = new DialSolver().solve(grid, START, GOAL, new MazeStats());
        List<Point> dijkstra = new DijkstraSolver().solve(grid, START, GOAL, new MazeStats());

        assertThat(dial).hasSize(5).contains(new Point(0, 2)).doesNotContain(new Point(2, 2));
        assertThat(dial).isEqualTo(dijkstra);
    }

    @Test
    void integerWeightedGrid_detoursAroundExpensiveCell_matchingDijkstra() {
        WeightedMazeGrid grid = new WeightedMazeGrid(3, 5);
        carveTwoCorridorMaze(grid);
        grid.setWeight(new Point(0, 2), 100.0); // integer weight — Dial's can bucket it

        List<Point> dial = new DialSolver().solve(grid, START, GOAL, new MazeStats());
        List<Point> dijkstra = new DijkstraSolver().solve(grid, START, GOAL, new MazeStats());

        assertThat(dial).hasSize(9).contains(new Point(2, 2)).doesNotContain(new Point(0, 2));
        assertThat(dial).isEqualTo(dijkstra);
    }

    @Test
    void fractionalWeight_isRejected() {
        WeightedMazeGrid grid = new WeightedMazeGrid(3, 5);
        carveTwoCorridorMaze(grid);
        grid.setWeight(new Point(0, 2), 2.5);

        assertThatThrownBy(() -> new DialSolver().solve(grid, START, GOAL, new MazeStats()))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("integer");
    }

    @Test
    void perfectMaze_matchesDijkstrasOptimalPath() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, 42L);

        List<Point> dial = new DialSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
        List<Point> dijkstra = new DijkstraSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());

        assertThat(dial).isEqualTo(dijkstra);
        assertThat(dial.get(0)).isEqualTo(grid.start());
        assertThat(dial.get(dial.size() - 1)).isEqualTo(grid.goal());
        for (int i = 0; i + 1 < dial.size(); i++) {
            assertThat(grid.openNeighbors(dial.get(i))).contains(dial.get(i + 1));
        }
    }

    @Test
    void unreachableGoal_returnsEmpty() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(new Point(0, 0), new Point(0, 1)); // (1,1) walled off

        MazeStats stats = new MazeStats();
        List<Point> path = new DialSolver().solve(grid, new Point(0, 0), new Point(1, 1), stats);

        assertThat(path).isEmpty();
        assertThat(stats.success()).isFalse();
    }

    @Test
    void startEqualsGoal_returnsSingletonPath() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(6, 6, 1L);
        Point p = new Point(3, 3);

        assertThat(new DialSolver().solve(grid, p, p, new MazeStats())).containsExactly(p);
    }

    @Test
    void isDeterministic() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(10, 10, 99L);

        List<Point> first = new DialSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
        List<Point> second = new DialSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
        assertThat(first).isEqualTo(second);
    }
}
