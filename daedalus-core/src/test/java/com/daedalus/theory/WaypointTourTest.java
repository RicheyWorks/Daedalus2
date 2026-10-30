// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.theory.WaypointTour.Tour;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link WaypointTour}. The load-bearing test is the brute-force cross-check: for small waypoint
 * counts the Held–Karp DP must agree exactly with enumerating every visiting order.
 */
class WaypointTourTest {

    @Test
    void corridor_reordersWaypointsOptimally() {
        MazeGrid grid = new MazeGrid(1, 5);
        for (int c = 0; c < 4; c++) {
            grid.carve(new Point(0, c), new Point(0, c + 1));
        }

        // Deliberately supplied far-first; the DP must swap them.
        Tour tour = WaypointTour.shortestTour(grid, new Point(0, 0),
                List.of(new Point(0, 4), new Point(0, 2)));

        assertThat(tour.feasible()).isTrue();
        assertThat(tour.order()).containsExactly(new Point(0, 2), new Point(0, 4));
        assertThat(tour.totalCost()).isEqualTo(4);
        assertThat(tour.path()).hasSize(5);
    }

    @Test
    void noWaypoints_isATrivialTour() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(6, 6, 1L);

        Tour tour = WaypointTour.shortestTour(grid, grid.start(), List.of());

        assertThat(tour.totalCost()).isZero();
        assertThat(tour.path()).containsExactly(grid.start());
        assertThat(tour.feasible()).isTrue();
    }

    @Test
    void waypointsEqualToStart_orDuplicated_areCollapsed() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(8, 8, 2L);
        Point start = grid.start();
        Point target = new Point(4, 4);

        Tour tour = WaypointTour.shortestTour(grid, start, List.of(start, target, target));

        assertThat(tour.order()).containsExactly(target);
    }

    @Test
    void unreachableWaypoint_isInfeasible() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(new Point(0, 0), new Point(0, 1)); // (1,1) walled off

        Tour tour = WaypointTour.shortestTour(grid, new Point(0, 0), List.of(new Point(1, 1)));

        assertThat(tour.feasible()).isFalse();
        assertThat(tour.totalCost()).isEqualTo(-1);
        assertThat(tour.path()).isEmpty();
    }

    @Test
    void matchesBruteForceOptimum_onSmallInstances() {
        List<Point> waypoints = List.of(new Point(1, 1), new Point(8, 3), new Point(4, 7), new Point(9, 9));

        for (long seed = 1; seed <= 6; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator().generate(10, 10, seed);
            Point start = grid.start();

            Tour tour = WaypointTour.shortestTour(grid, start, waypoints);

            assertThat(tour.totalCost())
                    .as("seed %d: Held-Karp must equal the best of all visiting orders", seed)
                    .isEqualTo(bruteForceOptimum(grid, start, waypoints));
        }
    }

    @Test
    void pathIsAConnectedWalk_visitingEveryWaypoint() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, 42L);
        List<Point> waypoints = List.of(new Point(2, 9), new Point(10, 1), new Point(6, 6));

        Tour tour = WaypointTour.shortestTour(grid, grid.start(), waypoints);

        assertThat(tour.path()).hasSize(tour.totalCost() + 1);
        assertThat(tour.path().get(0)).isEqualTo(grid.start());
        assertThat(tour.path()).containsAll(waypoints);
        for (int i = 0; i + 1 < tour.path().size(); i++) {
            assertThat(grid.openNeighbors(tour.path().get(i))).contains(tour.path().get(i + 1));
        }
    }

    @Test
    void tooManyWaypoints_isRejected() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(20, 20, 1L);
        // Start at 1 so none of these collapses into the start cell (0,0) and we really do
        // exceed the cap after de-duplication.
        List<Point> many = new ArrayList<>();
        for (int i = 1; i <= WaypointTour.MAX_WAYPOINTS + 1; i++) {
            many.add(new Point(i, i));
        }

        assertThatThrownBy(() -> WaypointTour.shortestTour(grid, grid.start(), many))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("exponential");
    }

    // ---------- brute-force oracle ----------

    /** Enumerate every visiting order and take the cheapest — the definition Held-Karp accelerates. */
    private static int bruteForceOptimum(MazeGrid grid, Point start, List<Point> waypoints) {
        int[][] startField = MazeMetrics.distancesFrom(grid, start);
        List<int[][]> fields = new ArrayList<>();
        for (Point w : waypoints) {
            fields.add(MazeMetrics.distancesFrom(grid, w));
        }

        List<List<Integer>> orders = new ArrayList<>();
        permute(new ArrayList<>(), new boolean[waypoints.size()], waypoints.size(), orders);

        int best = Integer.MAX_VALUE;
        for (List<Integer> order : orders) {
            Point first = waypoints.get(order.get(0));
            int cost = startField[first.row()][first.col()];
            for (int i = 0; i + 1 < order.size(); i++) {
                Point to = waypoints.get(order.get(i + 1));
                cost += fields.get(order.get(i))[to.row()][to.col()];
            }
            best = Math.min(best, cost);
        }
        return best;
    }

    private static void permute(List<Integer> current, boolean[] used, int n, List<List<Integer>> out) {
        if (current.size() == n) {
            out.add(new ArrayList<>(current));
            return;
        }
        for (int i = 0; i < n; i++) {
            if (!used[i]) {
                used[i] = true;
                current.add(i);
                permute(current, used, n, out);
                current.remove(current.size() - 1);
                used[i] = false;
            }
        }
    }
}
