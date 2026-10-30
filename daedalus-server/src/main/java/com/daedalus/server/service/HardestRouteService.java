// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.theory.LongestPath;
import com.daedalus.theory.MazeMetrics;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

/**
 * Hardest-route mode (ADR-007 idea 3) — the cruellest walk from start to goal that never
 * revisits a cell.
 *
 * <p><b>What the audit assumed, and what measurement said.</b> ADR-007 proposed this as
 * "place start and goal on the longest simple path instead of the extremes". Measurement
 * killed that framing: a perfect maze is a tree, a tree has exactly <em>one</em> simple path
 * between any two cells, and so on 22 of the 23 registered generators the longest route
 * between the extremes <em>is</em> the route between the extremes. Measured on a 15×15
 * recursive-backtracker maze, extremes placement and hardest-route placement agree to the
 * step (145 and 145). Shipping "hardest route" as a placement mode would have been a button
 * that changes nothing on almost every maze this project makes.
 *
 * <p><b>What it is instead.</b> The interesting quantity is the gap between the shortest and
 * the longest simple route on the maze <em>as it currently stands</em> — which is zero on a
 * tree and dramatic once the maze has loops. Braid the same 21×21 maze and the shortest route
 * falls to 56 steps while the hardest climbs to 260, a 4.6× detour. Erosion (living mazes) and
 * the Dungeon generator open loops the same way: a dungeon measures 40 against 122. So this
 * reports both numbers, their ratio, and how many independent loops the maze contains — and on
 * a tree it says plainly that there is only one route and why.
 *
 * <p>Cost is bounded by {@link LongestPath}'s visit budget rather than by maze size, which
 * measured at 40–105 ms across 15×15 to 512×512. That is solve-shaped, so the endpoint shares
 * the {@code mazeSolve} budget. Nothing is cached: like {@code /analysis}, this reads the
 * maze's current snapshot, so a living maze answers differently as it erodes — which is the
 * point, not a cache miss.
 */
@Service
public class HardestRouteService {

    private final MazeGenerationService mazes;

    public HardestRouteService(MazeGenerationService mazes) {
        this.mazes = mazes;
    }

    /**
     * The two routes and what separates them.
     *
     * @param shortestLength steps in the shortest route, or {@code -1} if the goal is unreachable
     * @param hardestLength  steps in the longest simple route found
     * @param detour         {@code hardestLength / shortestLength} — 1.0 on a tree
     * @param exact          whether the search proved its answer optimal within budget
     * @param loops          independent cycles in the maze; 0 means a tree, so one route only
     * @param note           the honest reading of the numbers above
     * @param path           the hardest route, cell by cell
     */
    public record HardestRoute(UUID mazeId, int rows, int cols, Point from, Point to,
                               int shortestLength, int hardestLength, double detour,
                               boolean exact, int loops, String note, List<Point> path) {
        public HardestRoute {
            path = List.copyOf(path);
        }
    }

    /** {@code null} when the maze is unknown, so the controller can 404. */
    public HardestRoute forMaze(UUID mazeId) {
        var cached = mazes.find(mazeId);
        if (cached == null) {
            return null;
        }
        MazeGrid grid = cached.grid();
        Point from = grid.start();
        Point to = grid.goal();

        List<Point> shortest = MazeMetrics.shortestPath(grid, from, to);
        int shortestLength = shortest.isEmpty() ? -1 : shortest.size() - 1;
        LongestPath.LongPath hardest = LongestPath.hardestRoute(grid);
        int loops = independentLoops(grid);
        double detour = shortestLength > 0 && hardest.length() > 0
                ? (double) hardest.length() / shortestLength : 1.0;

        return new HardestRoute(mazeId, grid.rows(), grid.cols(), from, to,
                shortestLength, hardest.length(), round(detour), hardest.exact(), loops,
                note(loops, shortestLength, hardest), hardest.path());
    }

    /**
     * Cycles in the habitable subgraph: {@code passages - (cells - components)}. Zero means the
     * maze is a forest, and a forest has one route between any two connected cells — which is
     * the whole explanation for why this feature is inert on perfect mazes.
     */
    private static int independentLoops(MazeGrid grid) {
        int habitable = 0;
        int passages = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                if (grid.openNeighbors(p).isEmpty()) {
                    continue;
                }
                habitable++;
                if (c + 1 < grid.cols() && grid.cell(r, c).isOpen(Direction.EAST)) {
                    passages++;
                }
                if (r + 1 < grid.rows() && grid.cell(r, c).isOpen(Direction.SOUTH)) {
                    passages++;
                }
            }
        }
        int components = componentsOf(grid, habitable);
        return Math.max(0, passages - (habitable - components));
    }

    private static int componentsOf(MazeGrid grid, int habitable) {
        if (habitable == 0) {
            return 0;
        }
        boolean[][] seen = new boolean[grid.rows()][grid.cols()];
        int components = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                if (seen[r][c] || grid.openNeighbors(p).isEmpty()) {
                    continue;
                }
                components++;
                int[][] reach = MazeMetrics.distancesFrom(grid, p);
                for (int rr = 0; rr < grid.rows(); rr++) {
                    for (int cc = 0; cc < grid.cols(); cc++) {
                        if (reach[rr][cc] >= 0) {
                            seen[rr][cc] = true;
                        }
                    }
                }
            }
        }
        return components;
    }

    private static String note(int loops, int shortestLength, LongestPath.LongPath hardest) {
        if (hardest.length() < 0) {
            return "The goal cannot be reached from the start at all, so neither route exists.";
        }
        if (loops == 0) {
            return "This maze is a tree: exactly one simple path exists between any two cells, "
                    + "so the hardest route IS the shortest route. Braid it, erode it (Bring to "
                    + "life) or generate a dungeon to open loops worth choosing between.";
        }
        if (hardest.length() == shortestLength) {
            return loops + " loops exist, but the search did not find a route longer than the "
                    + "shortest one within its visit budget, so this is a lower bound.";
        }
        return hardest.exact()
                ? "Proven optimal: no simple route from start to goal is longer than this one."
                : "A lower bound — the search ran out of visit budget, so a crueller route may "
                        + "exist. It is a real walk either way: every cell is entered once.";
    }

    private static double round(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}
