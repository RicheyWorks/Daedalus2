// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Max-flow / min-cut over the maze passage graph — CLRS Ch. 26, applied to level analysis.
 *
 * <p>Model every open passage as an undirected edge of capacity 1. The minimum start→goal cut
 * (equal to the max flow, by the max-flow–min-cut theorem) is then the <b>fewest passages you'd
 * have to wall off to seal the goal from the start</b> — and the cut edges are exactly those
 * bottleneck passages. It's also the start↔goal <b>edge connectivity</b>: the number of
 * edge-disjoint routes between them.
 *
 * <p>As a difficulty / structure signal: a perfect maze has a single route, so its min cut is
 * always {@code 1} (every passage on the unique solution is a chokepoint). A braided maze with
 * loops has connectivity {@code ≥ 2} — more independent routes, no single sealing passage.
 *
 * <p>Grid degree is at most 4, so the connectivity is at most 4 and Edmonds-Karp converges in a
 * handful of BFS augmentations. Deterministic: augmenting paths follow the fixed
 * {@link MazeGrid#openNeighbors(Point)} order, and the cut edge list is sorted.
 */
public final class MazeFlow {

    private MazeFlow() {
    }

    /** An undirected passage between two adjacent cells, normalized so {@code a} precedes {@code b}. */
    public record Passage(Point a, Point b) {
        public Passage {
            if (!isBefore(a, b)) {
                Point swap = a;
                a = b;
                b = swap;
            }
        }

        private static boolean isBefore(Point x, Point y) {
            return x.row() != y.row() ? x.row() < y.row() : x.col() <= y.col();
        }
    }

    /**
     * The minimum cut between two cells.
     *
     * @param source   start cell
     * @param sink     goal cell
     * @param cutSize  fewest passages to seal {@code source} from {@code sink} (= max flow =
     *                 edge connectivity); {@code 0} if they're the same cell or already separated
     * @param cutEdges the bottleneck passages forming that cut ({@code cutEdges.size() == cutSize})
     */
    public record MinCut(Point source, Point sink, int cutSize, List<Passage> cutEdges) {
        public MinCut {
            cutEdges = List.copyOf(cutEdges);
        }
    }

    /** Minimum cut between the grid's current start and goal. */
    public static MinCut minCutStartToGoal(MazeGrid grid) {
        return minCut(grid, grid.start(), grid.goal());
    }

    /** Start↔goal edge connectivity (the size of the minimum cut). */
    public static int edgeConnectivity(MazeGrid grid, Point source, Point sink) {
        return minCut(grid, source, sink).cutSize();
    }

    /**
     * Number of <b>internally vertex-disjoint</b> routes from {@code source} to {@code sink} —
     * routes that share no cell except the two endpoints. By Menger's theorem this also equals the
     * fewest intermediate cells you'd have to block to sever them, making it a route-redundancy
     * measure: how many independent ways through the maze exist, and how fragile they are.
     *
     * <p>Computed with the standard vertex-splitting reduction to max flow (CLRS Ch. 26): every
     * cell {@code v} becomes a pair {@code v_in → v_out} joined by a capacity-1 arc, so no cell can
     * carry two routes, and each passage {@code (u,v)} becomes {@code u_out → v_in} and
     * {@code v_out → u_in}. Flowing from {@code source_out} to {@code sink_in} then counts exactly
     * the vertex-disjoint routes.
     *
     * <p>Always {@code <=} {@link #edgeConnectivity} — blocking cells is at least as powerful as
     * blocking passages. On a perfect maze it is {@code 1} (a tree has a single route); braiding
     * (see {@code engine.Braider}) is what pushes it higher.
     */
    public static int vertexDisjointPaths(MazeGrid grid, Point source, Point sink) {
        if (source.equals(sink)) {
            return 0;
        }
        int cols = grid.cols();
        int cells = grid.rows() * cols;
        int nodes = 2 * cells;

        List<List<Integer>> adjacency = new ArrayList<>(nodes);
        for (int i = 0; i < nodes; i++) {
            adjacency.add(new ArrayList<>(4));
        }
        Map<Long, Integer> residual = new HashMap<>();

        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < cols; c++) {
                int v = r * cols + c;
                addArc(adjacency, residual, in(v), out(v), nodes); // the cell's own capacity: 1
                for (Point q : grid.openNeighbors(new Point(r, c))) {
                    int u = id(q, cols);
                    addArc(adjacency, residual, out(v), in(u), nodes);
                }
            }
        }

        int src = out(id(source, cols));
        int sink0 = in(id(sink, cols));
        int flow = 0;
        int[] parent = new int[nodes];
        while (findAugmentingPath(adjacency, residual, nodes, src, sink0, parent)) {
            for (int v = sink0; v != src; v = parent[v]) {
                residual.merge(key(parent[v], v, nodes), -1, Integer::sum);
                residual.merge(key(v, parent[v], nodes), 1, Integer::sum);
            }
            flow++;
        }
        return flow;
    }

    private static int in(int cell) {
        return 2 * cell;
    }

    private static int out(int cell) {
        return 2 * cell + 1;
    }

    /** Register a unit-capacity arc plus its residual counterpart. */
    private static void addArc(List<List<Integer>> adjacency, Map<Long, Integer> residual,
                               int from, int to, int nodes) {
        adjacency.get(from).add(to);
        adjacency.get(to).add(from);
        residual.merge(key(from, to, nodes), 1, Integer::sum);
    }

    /** BFS for an augmenting path in the split graph. */
    private static boolean findAugmentingPath(List<List<Integer>> adjacency, Map<Long, Integer> residual,
                                              int nodes, int src, int sink, int[] parent) {
        Arrays.fill(parent, -1);
        parent[src] = src;
        Deque<Integer> queue = new ArrayDeque<>();
        queue.add(src);
        while (!queue.isEmpty()) {
            int u = queue.poll();
            for (int v : adjacency.get(u)) {
                if (parent[v] == -1 && residual.getOrDefault(key(u, v, nodes), 0) > 0) {
                    parent[v] = u;
                    if (v == sink) {
                        return true;
                    }
                    queue.add(v);
                }
            }
        }
        return false;
    }

    /**
     * Minimum {@code source}→{@code sink} cut via Edmonds-Karp on unit-capacity passages.
     */
    public static MinCut minCut(MazeGrid grid, Point source, Point sink) {
        int rows = grid.rows();
        int cols = grid.cols();
        int n = rows * cols;
        int s = id(source, cols);
        int t = id(sink, cols);

        if (s == t) {
            return new MinCut(source, sink, 0, List.of());
        }

        // Residual capacities keyed by directed (u -> v); each undirected passage seeds both ways.
        Map<Long, Integer> residual = new HashMap<>();
        List<int[]> passages = new ArrayList<>();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int u = r * cols + c;
                for (Point q : grid.openNeighbors(new Point(r, c))) {
                    int v = id(q, cols);
                    if (u < v) {
                        passages.add(new int[] {u, v});
                        residual.merge(key(u, v, n), 1, Integer::sum);
                        residual.merge(key(v, u, n), 1, Integer::sum);
                    }
                }
            }
        }

        int maxFlow = 0;
        int[] parent = new int[n];
        while (augment(grid, cols, n, s, t, residual, parent)) {
            int bottleneck = Integer.MAX_VALUE;
            for (int v = t; v != s; v = parent[v]) {
                bottleneck = Math.min(bottleneck, residual.get(key(parent[v], v, n)));
            }
            for (int v = t; v != s; v = parent[v]) {
                int u = parent[v];
                residual.merge(key(u, v, n), -bottleneck, Integer::sum);
                residual.merge(key(v, u, n), bottleneck, Integer::sum);
            }
            maxFlow += bottleneck;
        }

        boolean[] sourceSide = reachable(grid, cols, n, s, residual);
        List<Passage> cut = new ArrayList<>();
        for (int[] edge : passages) {
            if (sourceSide[edge[0]] ^ sourceSide[edge[1]]) {
                cut.add(new Passage(pointOf(edge[0], cols), pointOf(edge[1], cols)));
            }
        }
        cut.sort(Comparator.comparingInt((Passage p) -> p.a().row())
                .thenComparingInt(p -> p.a().col())
                .thenComparingInt(p -> p.b().row())
                .thenComparingInt(p -> p.b().col()));
        return new MinCut(source, sink, maxFlow, cut);
    }

    /** One BFS for an augmenting path in the residual graph; fills {@code parent}, returns whether sink was reached. */
    private static boolean augment(MazeGrid grid, int cols, int n, int s, int t,
                                   Map<Long, Integer> residual, int[] parent) {
        Arrays.fill(parent, -1);
        parent[s] = s;
        Deque<Integer> queue = new ArrayDeque<>();
        queue.add(s);
        while (!queue.isEmpty()) {
            int u = queue.poll();
            for (Point q : grid.openNeighbors(pointOf(u, cols))) {
                int v = id(q, cols);
                if (parent[v] == -1 && residual.getOrDefault(key(u, v, n), 0) > 0) {
                    parent[v] = u;
                    if (v == t) {
                        return true;
                    }
                    queue.add(v);
                }
            }
        }
        return false;
    }

    /** Cells reachable from {@code s} in the residual graph — the source side of the min cut. */
    private static boolean[] reachable(MazeGrid grid, int cols, int n, int s, Map<Long, Integer> residual) {
        boolean[] seen = new boolean[n];
        seen[s] = true;
        Deque<Integer> queue = new ArrayDeque<>();
        queue.add(s);
        while (!queue.isEmpty()) {
            int u = queue.poll();
            for (Point q : grid.openNeighbors(pointOf(u, cols))) {
                int v = id(q, cols);
                if (!seen[v] && residual.getOrDefault(key(u, v, n), 0) > 0) {
                    seen[v] = true;
                    queue.add(v);
                }
            }
        }
        return seen;
    }

    private static int id(Point p, int cols) {
        return p.row() * cols + p.col();
    }

    private static Point pointOf(int id, int cols) {
        return new Point(id / cols, id % cols);
    }

    private static long key(int u, int v, int n) {
        return (long) u * n + v;
    }
}
