// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Shortest route from a start cell that visits every one of a set of waypoints — the "collect all
 * the coins" problem — solved exactly by the Held–Karp dynamic program (CLRS Ch. 15's
 * subset-DP technique applied to the TSP-path variant of Ch. 34).
 *
 * <h3>Why a DP and not a greedy walk</h3>
 *
 * <p>Visiting waypoints nearest-first is not optimal; choosing the order is the hard part, and the
 * problem is NP-hard in general (it contains TSP). Held–Karp trades the factorial of brute force
 * for {@code O(2^k · k²)} time and {@code O(2^k · k)} memory by keying the DP on
 * <em>(set of waypoints already collected, waypoint you're standing on)</em> rather than on the
 * full ordering. That's exponential in the number of waypoints but polynomial in the maze size, so
 * it stays practical exactly where a game mode needs it: a handful of coins in a large maze.
 *
 * <p>{@code k} is therefore capped at {@link #MAX_WAYPOINTS}; beyond that the subset table stops
 * being reasonable and you'd want a heuristic tour instead.
 *
 * <p>Distances between waypoints come from BFS fields ({@link MazeMetrics#distancesFrom}), so this
 * measures unit-cost passage steps. Deterministic throughout.
 */
public final class WaypointTour {

    /** Above this the {@code 2^k} subset table stops being sensible. */
    public static final int MAX_WAYPOINTS = 16;

    private static final int INFINITE = Integer.MAX_VALUE / 4;

    private WaypointTour() {
    }

    /**
     * An optimal waypoint tour.
     *
     * @param start     where the route begins
     * @param order     the waypoints in the order they should be visited
     * @param totalCost total steps walked ({@code path.size() - 1}); {@code -1} if infeasible
     * @param path      every cell walked, start through final waypoint; empty if infeasible
     * @param feasible  {@code false} when some waypoint is unreachable from {@code start}
     */
    public record Tour(Point start, List<Point> order, int totalCost, List<Point> path, boolean feasible) {
        public Tour {
            order = List.copyOf(order);
            path = List.copyOf(path);
        }
    }

    /**
     * Shortest route from {@code start} visiting every waypoint, in the best possible order.
     * Duplicate waypoints, and any equal to {@code start}, are collapsed away first.
     *
     * @throws IllegalArgumentException if more than {@link #MAX_WAYPOINTS} distinct waypoints remain
     */
    public static Tour shortestTour(MazeGrid grid, Point start, List<Point> waypoints) {
        List<Point> targets = distinctTargets(start, waypoints);
        if (targets.size() > MAX_WAYPOINTS) {
            throw new IllegalArgumentException(
                    "Held-Karp is exponential in the waypoint count; at most " + MAX_WAYPOINTS
                            + " are supported, got " + targets.size());
        }
        if (targets.isEmpty()) {
            return new Tour(start, List.of(), 0, List.of(start), true);
        }

        int k = targets.size();
        int[] fromStart = new int[k];
        int[][] between = new int[k][k];
        if (!buildDistanceTables(grid, start, targets, fromStart, between)) {
            return new Tour(start, List.of(), -1, List.of(), false);
        }

        int[][] best = new int[1 << k][k];
        int[][] cameFrom = new int[1 << k][k];
        for (int[] row : best) {
            Arrays.fill(row, INFINITE);
        }
        for (int[] row : cameFrom) {
            Arrays.fill(row, -1);
        }
        for (int i = 0; i < k; i++) {
            best[1 << i][i] = fromStart[i];
        }

        int full = (1 << k) - 1;
        for (int mask = 1; mask <= full; mask++) {
            for (int at = 0; at < k; at++) {
                int cost = best[mask][at];
                if (cost >= INFINITE || (mask & (1 << at)) == 0) {
                    continue;
                }
                for (int next = 0; next < k; next++) {
                    if ((mask & (1 << next)) != 0) {
                        continue;
                    }
                    int nextMask = mask | (1 << next);
                    int candidate = cost + between[at][next];
                    if (candidate < best[nextMask][next]) {
                        best[nextMask][next] = candidate;
                        cameFrom[nextMask][next] = at;
                    }
                }
            }
        }

        int endAt = 0;
        for (int i = 1; i < k; i++) {
            if (best[full][i] < best[full][endAt]) {
                endAt = i;
            }
        }

        List<Point> order = recoverOrder(targets, cameFrom, full, endAt);
        List<Point> path = stitch(grid, start, order);
        return new Tour(start, order, path.size() - 1, path, true);
    }

    /** Waypoints with duplicates and the start cell removed, in first-seen order. */
    private static List<Point> distinctTargets(Point start, List<Point> waypoints) {
        Set<Point> seen = new LinkedHashSet<>(waypoints);
        seen.remove(start);
        return new ArrayList<>(seen);
    }

    /** Fill start→waypoint and waypoint→waypoint step counts; false if any is unreachable. */
    private static boolean buildDistanceTables(MazeGrid grid, Point start, List<Point> targets,
                                               int[] fromStart, int[][] between) {
        int[][] startField = MazeMetrics.distancesFrom(grid, start);
        for (int i = 0; i < targets.size(); i++) {
            Point t = targets.get(i);
            int d = startField[t.row()][t.col()];
            if (d < 0) {
                return false; // unreachable, so no tour exists
            }
            fromStart[i] = d;
        }
        for (int i = 0; i < targets.size(); i++) {
            int[][] field = MazeMetrics.distancesFrom(grid, targets.get(i));
            for (int j = 0; j < targets.size(); j++) {
                Point t = targets.get(j);
                between[i][j] = field[t.row()][t.col()];
            }
        }
        return true;
    }

    private static List<Point> recoverOrder(List<Point> targets, int[][] cameFrom, int full, int endAt) {
        List<Point> reversed = new ArrayList<>();
        int mask = full;
        int at = endAt;
        while (at != -1) {
            reversed.add(targets.get(at));
            int previous = cameFrom[mask][at];
            mask &= ~(1 << at);
            at = previous;
        }
        List<Point> order = new ArrayList<>(reversed);
        java.util.Collections.reverse(order);
        return order;
    }

    /** Walk the chosen order for real, concatenating shortest legs without repeating joints. */
    private static List<Point> stitch(MazeGrid grid, Point start, List<Point> order) {
        List<Point> path = new ArrayList<>();
        path.add(start);
        Point cursor = start;
        for (Point target : order) {
            List<Point> leg = MazeMetrics.shortestPath(grid, cursor, target);
            path.addAll(leg.subList(1, leg.size())); // skip the joint we're already standing on
            cursor = target;
        }
        return path;
    }
}
