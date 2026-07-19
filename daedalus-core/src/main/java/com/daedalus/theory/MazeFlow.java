// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.graph.MazeGraph;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

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
        MazeGraph graph = new MazeGraph(grid);
        int cols = grid.cols();
        int cells = graph.nodeCount();
        int nodes = 2 * cells;
        int[] adjacency = new int[graph.maxDegree()];

        // Arc budget: each cell contributes its in->out arc, plus one arc per outgoing passage.
        // Every arc is stored with a zero-capacity reverse twin, which is what carries residual
        // flow back — the standard max-flow representation, in flat arrays rather than a map.
        int arcs = 0;
        for (int v = 0; v < cells; v++) {
            arcs += 2 + 2 * graph.neighbors(v, adjacency);
        }
        int[] tail = new int[arcs];
        int[] target = new int[arcs];
        int[] capacity = new int[arcs];
        int[] twin = new int[arcs];

        int next = 0;
        for (int v = 0; v < cells; v++) {
            next = addArc(tail, target, capacity, twin, next, in(v), out(v)); // the cell's own capacity: 1
            int degree = graph.neighbors(v, adjacency);
            for (int i = 0; i < degree; i++) {
                next = addArc(tail, target, capacity, twin, next, out(v), in(adjacency[i]));
            }
        }

        // Group arc ids by their tail so BFS can sweep a node's arcs contiguously.
        int[] offsets = new int[nodes + 1];
        for (int e = 0; e < arcs; e++) {
            offsets[tail[e] + 1]++;
        }
        for (int v = 0; v < nodes; v++) {
            offsets[v + 1] += offsets[v];
        }
        int[] arcsOf = new int[arcs];
        int[] cursor = offsets.clone();
        for (int e = 0; e < arcs; e++) {
            arcsOf[cursor[tail[e]]++] = e;
        }

        int src = out(id(source, cols));
        int destination = in(id(sink, cols));
        int[] parentArc = new int[nodes];
        int[] queue = new int[nodes];
        int flow = 0;
        while (augment(offsets, arcsOf, target, capacity, parentArc, queue, src, destination)) {
            for (int v = destination; v != src; ) {
                int arc = parentArc[v];
                capacity[arc]--;
                capacity[twin[arc]]++;
                v = tail[arc];
            }
            flow++;
        }
        return flow;
    }

    /** Append a unit-capacity arc plus its zero-capacity residual twin. */
    private static int addArc(int[] tail, int[] target, int[] capacity, int[] twin,
                              int next, int from, int to) {
        tail[next] = from;
        target[next] = to;
        capacity[next] = 1;
        twin[next] = next + 1;
        tail[next + 1] = to;
        target[next + 1] = from;
        capacity[next + 1] = 0;
        twin[next + 1] = next;
        return next + 2;
    }

    /** BFS for an augmenting path over the arc-indexed split graph. */
    private static boolean augment(int[] offsets, int[] arcsOf, int[] target, int[] capacity,
                                   int[] parentArc, int[] queue, int src, int destination) {
        Arrays.fill(parentArc, -1);
        boolean[] seen = new boolean[offsets.length - 1];
        seen[src] = true;
        int head = 0;
        int tail = 0;
        queue[tail++] = src;
        while (head < tail) {
            int u = queue[head++];
            for (int i = offsets[u]; i < offsets[u + 1]; i++) {
                int arc = arcsOf[i];
                int v = target[arc];
                if (!seen[v] && capacity[arc] > 0) {
                    seen[v] = true;
                    parentArc[v] = arc;
                    if (v == destination) {
                        return true;
                    }
                    queue[tail++] = v;
                }
            }
        }
        return false;
    }

    private static int in(int cell) {
        return 2 * cell;
    }

    private static int out(int cell) {
        return 2 * cell + 1;
    }

    /**
     * Minimum {@code source}→{@code sink} cut via Edmonds-Karp on unit-capacity passages.
     */
    public static MinCut minCut(MazeGrid grid, Point source, Point sink) {
        int cols = grid.cols();
        int s = id(source, cols);
        int t = id(sink, cols);
        if (s == t) {
            return new MinCut(source, sink, 0, List.of());
        }

        Residual net = Residual.of(grid);
        int maxFlow = 0;
        int[] parentEdge = new int[net.nodeCount()];
        while (net.augmentingPath(s, t, parentEdge)) {
            for (int v = t; v != s; ) {
                int edge = parentEdge[v];
                net.push(edge);
                v = net.from(edge);
            }
            maxFlow++; // unit capacities, so every augmenting path carries exactly 1
        }

        boolean[] sourceSide = net.reachableFrom(s);
        List<Passage> cut = new ArrayList<>();
        for (int u = 0; u < net.nodeCount(); u++) {
            for (int e = net.edgeStart(u); e < net.edgeEnd(u); e++) {
                int v = net.target(e);
                if (u < v && (sourceSide[u] ^ sourceSide[v])) {
                    cut.add(new Passage(pointOf(u, cols), pointOf(v, cols)));
                }
            }
        }
        cut.sort(Comparator.comparingInt((Passage p) -> p.a().row())
                .thenComparingInt(p -> p.a().col())
                .thenComparingInt(p -> p.b().row())
                .thenComparingInt(p -> p.b().col()));
        return new MinCut(source, sink, maxFlow, cut);
    }

    /**
     * Unit-capacity residual network in compressed-sparse-row form, built from the
     * {@link com.daedalus.graph.Graph} seam.
     *
     * <p>Replaces a {@code Map<Long, Integer>} keyed by packed {@code (from, to)} pairs. That map
     * boxed a {@code Long} on every residual lookup, and max-flow does one per edge per BFS — the
     * single hottest operation in the algorithm.
     */
    private static final class Residual {
        private final int[] offsets;
        private final int[] targets;
        private final int[] owner;    // tail of each directed edge
        private final int[] twin;     // index of the opposing directed edge
        private final int[] capacity;
        private final int[] queue;
        private final int nodes;

        private Residual(int[] offsets, int[] targets, int[] owner, int[] twin, int[] capacity, int nodes) {
            this.offsets = offsets;
            this.targets = targets;
            this.owner = owner;
            this.twin = twin;
            this.capacity = capacity;
            this.queue = new int[nodes];
            this.nodes = nodes;
        }

        static Residual of(MazeGrid grid) {
            MazeGraph graph = new MazeGraph(grid);
            int nodes = graph.nodeCount();
            int[] adjacency = new int[graph.maxDegree()];

            int[] offsets = new int[nodes + 1];
            for (int v = 0; v < nodes; v++) {
                offsets[v + 1] = offsets[v] + graph.neighbors(v, adjacency);
            }
            int edges = offsets[nodes];
            int[] targets = new int[edges];
            int[] owner = new int[edges];
            int[] capacity = new int[edges];
            int[] cursor = offsets.clone();
            for (int v = 0; v < nodes; v++) {
                int degree = graph.neighbors(v, adjacency);
                for (int i = 0; i < degree; i++) {
                    int e = cursor[v]++;
                    targets[e] = adjacency[i];
                    owner[e] = v;
                    capacity[e] = 1;
                }
            }
            int[] twin = new int[edges];
            for (int u = 0; u < nodes; u++) {
                for (int e = offsets[u]; e < offsets[u + 1]; e++) {
                    int v = targets[e];
                    for (int f = offsets[v]; f < offsets[v + 1]; f++) {
                        if (targets[f] == u) {
                            twin[e] = f;
                            break;
                        }
                    }
                }
            }
            return new Residual(offsets, targets, owner, twin, capacity, nodes);
        }

        int nodeCount() {
            return nodes;
        }

        int edgeStart(int node) {
            return offsets[node];
        }

        int edgeEnd(int node) {
            return offsets[node + 1];
        }

        int target(int edge) {
            return targets[edge];
        }

        int from(int edge) {
            return owner[edge];
        }

        /** Send one unit along {@code edge}, crediting its twin. */
        void push(int edge) {
            capacity[edge]--;
            capacity[twin[edge]]++;
        }

        /** BFS for an augmenting path; records the incoming edge per node. */
        boolean augmentingPath(int source, int sink, int[] parentEdge) {
            Arrays.fill(parentEdge, -1);
            boolean[] seen = new boolean[nodes];
            seen[source] = true;
            int head = 0;
            int tail = 0;
            queue[tail++] = source;
            while (head < tail) {
                int u = queue[head++];
                for (int e = offsets[u]; e < offsets[u + 1]; e++) {
                    int v = targets[e];
                    if (!seen[v] && capacity[e] > 0) {
                        seen[v] = true;
                        parentEdge[v] = e;
                        if (v == sink) {
                            return true;
                        }
                        queue[tail++] = v;
                    }
                }
            }
            return false;
        }

        /** Nodes still reachable through residual capacity — the source side of the cut. */
        boolean[] reachableFrom(int source) {
            boolean[] seen = new boolean[nodes];
            seen[source] = true;
            int head = 0;
            int tail = 0;
            queue[tail++] = source;
            while (head < tail) {
                int u = queue[head++];
                for (int e = offsets[u]; e < offsets[u + 1]; e++) {
                    int v = targets[e];
                    if (!seen[v] && capacity[e] > 0) {
                        seen[v] = true;
                        queue[tail++] = v;
                    }
                }
            }
            return seen;
        }
    }

    private static int id(Point p, int cols) {
        return p.row() * cols + p.col();
    }

    private static Point pointOf(int id, int cols) {
        return new Point(id / cols, id % cols);
    }

}
