// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.graph.MazeGraph;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.PriorityQueue;

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
     * Longest shortest-path in the maze via double BFS — O(V + E). Exact for perfect (tree)
     * mazes; a lower-bound heuristic if the maze has cycles. Operates on the connected
     * component of the top-left cell {@code (0, 0)}.
     *
     * <p><b>How loose is the bound?</b> Measured over 15 mazes at 20² per setting, against the
     * true diameter from {@link #exactDiameter(MazeGrid)}:
     *
     * <pre>
     *   braid factor   mean error   worst error
     *   0.0 (perfect)        0.0%          0.0%
     *   0.1                  0.5%          9.6%
     *   0.3                  0.6%          8.4%
     *   0.5                  1.4%         20.0%
     *   0.7                  3.4%          9.5%
     *   1.0                  2.5%         13.6%
     * </pre>
     *
     * <p>So on average the estimate is tight — within a few percent — but on an individual
     * looped maze it can be <b>20% low</b>. That distinction matters by use case: for ranking
     * generators or placing a start and goal far apart, the fast estimate is fine. For
     * capacity or latency planning over a braided topology, where the diameter <em>is</em> the
     * worst-case route length, use {@link #exactDiameter(MazeGrid)} and pay the O(V²).
     *
     * @see #exactDiameter(MazeGrid)
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
     * The maze's <b>true</b> diameter — BFS from every cell, taking the largest eccentricity.
     * O(V · (V + E)), which on a grid is O(V²).
     *
     * <p>Exists because the classic double-BFS in {@link #diameter(MazeGrid)} is only exact on
     * a <em>tree</em>. The two-sweep argument relies on the farthest cell from any starting
     * point being an endpoint of some diameter, and that property fails as soon as the graph
     * has a cycle — a shortcut edge can make the first sweep land somewhere that is not on any
     * diameter at all. The estimate is then a lower bound, measured up to 20% low on
     * individual braided mazes (see {@link #diameter(MazeGrid)} for the full table).
     *
     * <p>Use this when the number is a planning input rather than a ranking: worst-case route
     * length across a topology, latency budgets, capacity headroom. Use the fast estimate when
     * you only need "two cells that are far apart" — which is what
     * {@link #placeStartAndGoalAtExtremes(MazeGrid)} wants, and why it keeps using it.
     *
     * <p>Unlike {@link #diameter(MazeGrid)} this considers <em>every</em> component, not just
     * the one containing {@code (0, 0)}: it reports the largest distance found anywhere in the
     * grid. On a disconnected maze that is the widest component's diameter.
     *
     * <p>Deterministic: sources are scanned row-major and ties keep the earliest.
     */
    public static Diameter exactDiameter(MazeGrid grid) {
        Point bestFrom = new Point(0, 0);
        Point bestTo = new Point(0, 0);
        int best = -1;
        Bfs bestSearch = null;

        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point source = new Point(r, c);
                Bfs search = bfs(grid, source);
                // Strict > keeps the first (row-major smallest) source among ties.
                if (search.maxDistance > best) {
                    best = search.maxDistance;
                    bestFrom = source;
                    bestTo = search.farthest;
                    bestSearch = search;
                }
            }
        }

        List<Point> path = bestSearch == null
                ? List.of(bestFrom)
                : reconstruct(bestSearch.parent, bestFrom, bestTo, grid.cols());
        return new Diameter(bestFrom, bestTo, Math.max(best, 0), path);
    }

    /**
     * Move the grid's start and goal onto the diameter endpoints (mutates {@code grid}) and
     * return the diameter that was used.
     *
     * <p>Deliberately uses the fast {@link #diameter(MazeGrid)} estimate: the goal here is two
     * cells that are far apart, not an exact extremal pair, and paying O(V²) to move the start
     * a few cells would be a poor trade.
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

    /**
     * Dijkstra cost-distances <em>from</em> {@code source} to every cell — {@code d(source, x)} —
     * as a fresh {@code rows × cols} grid. Unreachable cells are
     * {@link Double#POSITIVE_INFINITY}.
     *
     * <p>This is the weighted counterpart of {@link #distancesFrom(MazeGrid, Point)}. On a plain
     * {@link MazeGrid} every edge costs {@code 1.0} and the result equals the BFS field, but
     * BFS gets there in O(V + E) against Dijkstra's O((V + E) log V) — so prefer the BFS form
     * when the grid is uniform-cost.
     *
     * <p><b>Direction matters.</b> {@code MazeGrid}'s cost model charges the weight of the cell
     * being <em>entered</em>, so {@code d(a, b) != d(b, a)} in general (they differ by
     * {@code w(b) - w(a)}). This method answers "outbound from source". For the other
     * direction use {@link #weightedDistancesTo(MazeGrid, Point)}; do not assume one can be
     * read backwards for the other.
     */
    public static double[][] weightedDistancesFrom(MazeGrid grid, Point source) {
        return dijkstra(grid, source, true);
    }

    /**
     * Dijkstra cost-distances <em>to</em> {@code target} from every cell — {@code d(x, target)} —
     * as a fresh {@code rows × cols} grid. Unreachable cells are
     * {@link Double#POSITIVE_INFINITY}.
     *
     * <p>Computed by running Dijkstra over the reverse graph: passages are undirected, so the
     * reverse graph has the same adjacency, but the cost of the reversed arc {@code v -> u} is
     * the weight of {@code v} (the cell a forward traveller would be entering). That single
     * change is the whole difference between the two sweeps.
     */
    public static double[][] weightedDistancesTo(MazeGrid grid, Point target) {
        return dijkstra(grid, target, false);
    }

    /**
     * Shared Dijkstra over the {@link MazeGraph} seam.
     *
     * @param forward {@code true} for {@code d(origin, x)} — relax into a neighbour at the
     *                neighbour's weight; {@code false} for {@code d(x, origin)} — relax at the
     *                weight of the node being left, which is what the reversed arc costs.
     */
    private static double[][] dijkstra(MazeGrid grid, Point origin, boolean forward) {
        MazeGraph graph = new MazeGraph(grid);
        int rows = grid.rows();
        int cols = grid.cols();

        double[][] distance = new double[rows][cols];
        for (double[] row : distance) {
            Arrays.fill(row, Double.POSITIVE_INFINITY);
        }
        boolean[] settled = new boolean[rows * cols];
        int[] adjacency = new int[graph.maxDegree()];

        int start = origin.row() * cols + origin.col();
        distance[origin.row()][origin.col()] = 0.0;

        // Lazy-deletion queue: push on improvement, discard stale pops. Avoids needing
        // decrease-key, at the cost of at most E entries.
        PriorityQueue<long[]> queue = new PriorityQueue<>(
                (x, y) -> Double.compare(Double.longBitsToDouble(x[0]), Double.longBitsToDouble(y[0])));
        queue.add(new long[] {Double.doubleToRawLongBits(0.0), start});

        while (!queue.isEmpty()) {
            long[] top = queue.poll();
            int current = (int) top[1];
            if (settled[current]) {
                continue;
            }
            settled[current] = true;
            int curRow = current / cols;
            int curCol = current % cols;
            double d = distance[curRow][curCol];

            int degree = graph.neighbors(current, adjacency);
            for (int i = 0; i < degree; i++) {
                int next = adjacency[i];
                int nextRow = next / cols;
                int nextCol = next % cols;
                double step = forward ? grid.weightOf(nextRow, nextCol) : grid.weightOf(curRow, curCol);
                double candidate = d + step;
                if (candidate < distance[nextRow][nextCol]) {
                    distance[nextRow][nextCol] = candidate;
                    queue.add(new long[] {Double.doubleToRawLongBits(candidate), next});
                }
            }
        }
        return distance;
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
