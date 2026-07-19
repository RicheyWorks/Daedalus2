// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.graph.MazeGraph;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Structural graph metrics over a maze — CLRS Ch. 22 (breadth-first search) applied to the
 * passage graph, now running on the {@link com.daedalus.graph.Graph} seam (ADR-001) with dense
 * node ids and an allocation-free traversal.
 *
 * <p>The headline is {@link #diameter(MazeGrid)}: the longest shortest-path in the maze, found by
 * the classic <em>double BFS</em> — BFS from any cell to its farthest cell {@code u}, then BFS
 * from {@code u} to its farthest cell {@code v}; {@code dist(u, v)} is the diameter. This is
 * <b>exact for perfect mazes</b> (a perfect maze is a spanning tree, and double-BFS is exact on
 * trees). On braided / imperfect mazes with cycles it is a fast lower-bound heuristic.
 *
 * <p>{@link #placeStartAndGoalAtExtremes(MazeGrid)} uses that to drop the start and goal on the
 * two farthest-apart cells, giving a generated maze its maximum possible challenge for free.
 *
 * <p>This class is on the hot path for {@link DistanceOracle} (one BFS per cell) and
 * {@code solver.LandmarkHeuristic}, so the traversal keeps its state in flat arrays and reuses a
 * single adjacency buffer rather than building a neighbour list per cell.
 *
 * <p>All results are deterministic: BFS explores neighbours in a fixed order, and the "farthest"
 * cell is disambiguated by a row-major scan (smallest {@code (row, col)} among ties).
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
        List<Point> path = reconstruct(second.parent, u, v, grid.cols());
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
     * {@code to} is unreachable. Deterministic — BFS explores neighbours in a fixed order.
     */
    public static List<Point> shortestPath(MazeGrid grid, Point from, Point to) {
        Bfs search = bfs(grid, from);
        if (search.distance[to.row()][to.col()] < 0) {
            return List.of();
        }
        return reconstruct(search.parent, from, to, grid.cols());
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
        MazeGraph graph = new MazeGraph(grid);
        int rows = grid.rows();
        int cols = grid.cols();
        int nodes = rows * cols;

        int[][] distance = new int[rows][cols];
        for (int[] row : distance) {
            Arrays.fill(row, -1);
        }
        int[] parent = new int[nodes];
        Arrays.fill(parent, -1);

        // BFS enqueues each cell at most once, so the cell count is an exact capacity bound.
        int[] queue = new int[nodes];
        int head = 0;
        int tail = 0;
        int[] adjacency = new int[graph.maxDegree()];

        distance[source.row()][source.col()] = 0;
        queue[tail++] = source.row() * cols + source.col();
        while (head < tail) {
            int current = queue[head++];
            int d = distance[current / cols][current % cols];
            int degree = graph.neighbors(current, adjacency);
            for (int i = 0; i < degree; i++) {
                int next = adjacency[i];
                int nextRow = next / cols;
                int nextCol = next % cols;
                if (distance[nextRow][nextCol] == -1) {
                    distance[nextRow][nextCol] = d + 1;
                    parent[next] = current;
                    queue[tail++] = next;
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

    private static List<Point> reconstruct(int[] parent, Point source, Point target, int cols) {
        List<Point> reversed = new ArrayList<>();
        int sourceId = source.row() * cols + source.col();
        int current = target.row() * cols + target.col();
        while (current != -1) {
            reversed.add(new Point(current / cols, current % cols));
            if (current == sourceId) {
                break;
            }
            current = parent[current];
        }
        Collections.reverse(reversed);
        return reversed;
    }

    private record Bfs(int[][] distance, int[] parent, Point farthest, int maxDistance) {
    }
}
