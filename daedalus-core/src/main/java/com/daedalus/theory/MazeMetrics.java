// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Deque;
import java.util.List;

/**
 * Structural graph metrics over a maze — CLRS Ch. 22 (breadth-first search) applied to the
 * passage graph ({@link MazeGrid#openNeighbors(Point)} is the adjacency, every edge unit length).
 *
 * <p>The headline is {@link #diameter(MazeGrid)}: the longest shortest-path in the maze, found by
 * the classic <em>double BFS</em> — BFS from any cell to its farthest cell {@code u}, then BFS
 * from {@code u} to its farthest cell {@code v}; {@code dist(u, v)} is the diameter. This is
 * <b>exact for perfect mazes</b> (a perfect maze is a spanning tree, and double-BFS is exact on
 * trees). On braided / imperfect mazes with cycles it is a fast lower-bound heuristic, not a
 * guarantee.
 *
 * <p>{@link #placeStartAndGoalAtExtremes(MazeGrid)} uses that to drop the start and goal on the
 * two farthest-apart cells, giving a generated maze its maximum possible challenge for free.
 *
 * <p>All results are deterministic: BFS explores {@code openNeighbors} in a fixed order, and the
 * "farthest" cell is disambiguated by a row-major scan (smallest {@code (row, col)} among ties),
 * so the same maze always yields the same endpoints and path.
 */
public final class MazeMetrics {

    private MazeMetrics() {
    }

    /**
     * The maze's diameter: the two farthest-apart cells, their distance, and one longest
     * shortest-path between them.
     *
     * @param from     one extreme endpoint
     * @param to       the other extreme endpoint
     * @param distance number of steps between them ({@code path.size() - 1})
     * @param path     the cells from {@code from} to {@code to} inclusive
     */
    public record Diameter(Point from, Point to, int distance, List<Point> path) {
        public Diameter {
            path = List.copyOf(path);
        }
    }

    /**
     * Longest shortest-path in the maze via double BFS. Exact for perfect (tree) mazes; a
     * lower-bound heuristic if the maze has cycles. Operates on the connected component of the
     * top-left cell {@code (0, 0)}.
     */
    public static Diameter diameter(MazeGrid grid) {
        Point origin = new Point(0, 0);
        Point u = bfs(grid, origin).farthest;
        Bfs second = bfs(grid, u);
        Point v = second.farthest;
        int distance = second.distance[v.row()][v.col()];
        List<Point> path = reconstruct(second.parent, u, v);
        return new Diameter(u, v, distance, path);
    }

    /**
     * Move the grid's start and goal onto the diameter endpoints (mutates {@code grid}) and
     * return the diameter that was used.
     */
    public static Diameter placeStartAndGoalAtExtremes(MazeGrid grid) {
        Diameter d = diameter(grid);
        grid.setStart(d.from());
        grid.setGoal(d.to());
        return d;
    }

    /** The cell farthest (in passage steps) from {@code source}, within its component. */
    public static Point farthestFrom(MazeGrid grid, Point source) {
        return bfs(grid, source).farthest;
    }

    /**
     * One shortest passage route from {@code from} to {@code to}, inclusive of both ends. Empty if
     * {@code to} is unreachable. Deterministic — BFS explores {@code openNeighbors} in a fixed
     * order.
     */
    public static List<Point> shortestPath(MazeGrid grid, Point from, Point to) {
        Bfs search = bfs(grid, from);
        if (search.distance[to.row()][to.col()] < 0) {
            return List.of();
        }
        return reconstruct(search.parent, from, to);
    }

    /**
     * BFS step-distances from {@code source} to every cell as a fresh {@code rows × cols} grid;
     * unreachable cells (a different component) are {@code -1}. Useful for distance heat-maps.
     */
    public static int[][] distancesFrom(MazeGrid grid, Point source) {
        int[][] distance = bfs(grid, source).distance;
        int[][] copy = new int[distance.length][];
        for (int r = 0; r < distance.length; r++) {
            copy[r] = distance[r].clone();
        }
        return copy;
    }

    private static Bfs bfs(MazeGrid grid, Point source) {
        int rows = grid.rows();
        int cols = grid.cols();
        int[][] distance = new int[rows][cols];
        for (int[] row : distance) {
            Arrays.fill(row, -1);
        }
        Point[][] parent = new Point[rows][cols];

        Deque<Point> queue = new ArrayDeque<>();
        distance[source.row()][source.col()] = 0;
        queue.add(source);
        while (!queue.isEmpty()) {
            Point current = queue.poll();
            int d = distance[current.row()][current.col()];
            for (Point next : grid.openNeighbors(current)) {
                if (distance[next.row()][next.col()] == -1) {
                    distance[next.row()][next.col()] = d + 1;
                    parent[next.row()][next.col()] = current;
                    queue.add(next);
                }
            }
        }

        // Deterministic farthest: row-major scan keeps the smallest (row, col) among ties.
        Point farthest = source;
        int maxDistance = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (distance[r][c] > maxDistance) {
                    maxDistance = distance[r][c];
                    farthest = new Point(r, c);
                }
            }
        }
        return new Bfs(distance, parent, farthest, maxDistance);
    }

    private static List<Point> reconstruct(Point[][] parent, Point source, Point target) {
        List<Point> reversed = new ArrayList<>();
        Point current = target;
        while (current != null) {
            reversed.add(current);
            if (current.equals(source)) {
                break;
            }
            current = parent[current.row()][current.col()];
        }
        Collections.reverse(reversed);
        return reversed;
    }

    private record Bfs(int[][] distance, Point[][] parent, Point farthest, int maxDistance) {
    }
}
