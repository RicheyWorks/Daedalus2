// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.graph.MazeGraph;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;
import com.daedalus.solver.GridIndex;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Dial's algorithm — Dijkstra with a bucket priority queue (CLRS Ch. 24, and the bounded-key
 * idea of Ch. 20) instead of a comparison heap.
 *
 * <p>When edge weights are small non-negative integers, the tentative distances live in a bounded
 * range, so a vertex at distance {@code d} can be filed in {@code bucket[d]} and the algorithm
 * simply scans buckets in increasing order. That trades Dijkstra's {@code O((V + E) log V)} for
 * {@code O(C·V + E)} where {@code C} is the maximum weight — near-linear on a grid, where the
 * degree (and so the number of relaxations) is bounded by 4.
 *
 * <p>Runs on the {@link com.daedalus.graph.Graph} seam (ADR-001): distance, parent and settled
 * state are cell-id arrays, buckets hold raw {@code int} ids, and adjacency arrives in a reused
 * buffer — no hashing of {@code Point}s and no per-expansion allocation.
 *
 * <p>Reads the same {@link MazeGrid#weightOf(Point)} hook as {@link DijkstraSolver}, so on a plain
 * uniform-cost {@code MazeGrid} it behaves like a BFS by distance and returns an identical optimal
 * path. It <b>requires non-negative integer cell weights</b>: a
 * {@link com.daedalus.engine.WeightedMazeGrid} carrying a fractional weight makes bucketing
 * ill-defined, so this solver throws {@link IllegalStateException} in that case — use
 * {@link DijkstraSolver} for real-valued weights.
 *
 * <p>Deterministic: buckets are FIFO and scanned in ascending order, and neighbours are visited in
 * the grid's fixed direction order, so a given maze always yields the same path.
 */
public class DialSolver extends AbstractMazeSolver {

    private static final double INTEGER_TOLERANCE = 1e-9;
    private static final int UNREACHED = -1;

    @Override public String id() { return "dial"; }

    @Override public String displayName() { return "Dial (bucket-queue Dijkstra)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "solver",
                "O(C*V + E) time, O(C*V) space",
                "Optimal for non-negative integer weights",
                "Dijkstra with a bucket priority queue keyed by integer distance; near-linear when "
                        + "edge weights are small bounded integers. Requires integer weights.");
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats) {
        MazeGraph graph = new MazeGraph(grid);
        GridIndex index = new GridIndex(grid);
        int startId = index.idOf(start);
        int goalId = index.idOf(goal);

        int nodes = graph.nodeCount();
        int[] dist = new int[nodes];
        Arrays.fill(dist, UNREACHED);
        int[] parent = new int[nodes];
        Arrays.fill(parent, -1);
        boolean[] settled = new boolean[nodes];
        int[] adjacency = new int[graph.maxDegree()];

        // Buckets are indexed by distance directly. A HashMap keyed by Integer was measured
        // first and left only a 1.0-1.28x gain: boxing the distance key on every relaxation
        // put hashing right back on the hottest path, which is the whole thing the seam removes.
        IntBucket[] buckets = new IntBucket[64];
        dist[startId] = 0;
        buckets[0] = new IntBucket();
        buckets[0].add(startId);

        int maxKey = 0;
        int frontier = 1; // reached but not yet settled

        for (int k = 0; k <= maxKey; k++) {
            IntBucket bucket = k < buckets.length ? buckets[k] : null;
            if (bucket == null) {
                continue;
            }
            while (bucket.hasNext()) {
                int current = bucket.next();
                if (settled[current] || dist[current] != k) {
                    continue; // stale duplicate left behind by a later, shorter relaxation
                }
                settled[current] = true;
                frontier--;
                stats.recordFrontier(frontier);
                stats.incExplored();

                if (current == goalId) {
                    List<Point> path = reconstruct(parent, startId, goalId, index);
                    stats.setPathLength(path.size());
                    stats.finish(true);
                    return path;
                }

                int degree = graph.neighbors(current, adjacency);
                for (int i = 0; i < degree; i++) {
                    int next = adjacency[i];
                    int tentative = k + integerWeight(graph, current, next);
                    if (dist[next] == UNREACHED || tentative < dist[next]) {
                        if (dist[next] == UNREACHED) {
                            frontier++;
                        }
                        dist[next] = tentative;
                        parent[next] = current;
                        if (tentative >= buckets.length) {
                            buckets = Arrays.copyOf(buckets, Math.max(tentative + 1, buckets.length * 2));
                        }
                        if (buckets[tentative] == null) {
                            buckets[tentative] = new IntBucket();
                        }
                        buckets[tentative].add(next);
                        if (tentative > maxKey) {
                            maxKey = tentative;
                        }
                        stats.incVisited();
                    }
                }
            }
        }

        stats.finish(false);
        return Collections.emptyList();
    }

    /** Edge cost as a non-negative int, or throw if the weight isn't integral. */
    private static int integerWeight(MazeGraph graph, int from, int to) {
        double w = graph.edgeWeight(from, to);
        long rounded = Math.round(w);
        if (w < 0.0 || Double.isNaN(w) || Double.isInfinite(w)
                || Math.abs(w - rounded) > INTEGER_TOLERANCE || rounded > Integer.MAX_VALUE) {
            throw new IllegalStateException(
                    "DialSolver requires non-negative integer cell weights; found " + w
                            + " entering node " + to + " — use DijkstraSolver for fractional weights.");
        }
        return (int) rounded;
    }

    /**
     * A growable FIFO of raw node ids. Deliberately not {@code ArrayDeque<Integer>}: buckets are
     * the hottest structure here and boxing every id would undo the point of the seam. Appending
     * while draining is required — a zero-weight edge files a node back into the bucket currently
     * being processed.
     */
    private static final class IntBucket {
        private int[] items = new int[8];
        private int size;
        private int head;

        void add(int value) {
            if (size == items.length) {
                items = Arrays.copyOf(items, size * 2);
            }
            items[size++] = value;
        }

        boolean hasNext() {
            return head < size;
        }

        int next() {
            return items[head++];
        }
    }
}
