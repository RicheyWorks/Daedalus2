// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;

import java.util.ArrayDeque;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

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
 * <p>Reads the same {@link MazeGrid#weightOf(Point)} hook as {@link DijkstraSolver}, so on a plain
 * uniform-cost {@code MazeGrid} it behaves like a BFS by distance and returns an identical optimal
 * path. It <b>requires non-negative integer cell weights</b>: a
 * {@link com.daedalus.engine.WeightedMazeGrid} carrying a fractional weight makes bucketing
 * ill-defined, so this solver throws {@link IllegalStateException} in that case — use
 * {@link DijkstraSolver} for real-valued weights.
 *
 * <p>Deterministic: buckets are FIFO and scanned in ascending order, and neighbours are visited in
 * {@link MazeGrid#openNeighbors(Point)} order, so a given maze always yields the same path.
 */
public class DialSolver extends AbstractMazeSolver {

    private static final double INTEGER_TOLERANCE = 1e-9;

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
        Map<Point, Integer> dist = new HashMap<>();
        Map<Point, Point> parent = new HashMap<>();
        Map<Integer, ArrayDeque<Point>> buckets = new HashMap<>();
        Set<Point> settled = new HashSet<>();

        dist.put(start, 0);
        parent.put(start, null);
        buckets.computeIfAbsent(0, k -> new ArrayDeque<>()).add(start);

        int maxKey = 0;
        int frontier = 1; // reached but not yet settled

        for (int k = 0; k <= maxKey; k++) {
            ArrayDeque<Point> bucket = buckets.get(k);
            if (bucket == null) {
                continue;
            }
            while (!bucket.isEmpty()) {
                Point cur = bucket.poll();
                Integer known = dist.get(cur);
                if (settled.contains(cur) || known == null || known.intValue() != k) {
                    continue; // stale duplicate left behind by a later, shorter relaxation
                }
                settled.add(cur);
                frontier--;
                stats.recordFrontier(frontier);
                stats.incExplored();

                if (cur.equals(goal)) {
                    List<Point> path = reconstruct(parent, start, goal);
                    stats.setPathLength(path.size());
                    stats.finish(true);
                    return path;
                }

                for (Point next : grid.openNeighbors(cur)) {
                    int tentative = k + integerWeight(grid, next);
                    Integer old = dist.get(next);
                    if (old == null || tentative < old) {
                        if (old == null) {
                            frontier++;
                        }
                        dist.put(next, tentative);
                        parent.put(next, cur);
                        buckets.computeIfAbsent(tentative, x -> new ArrayDeque<>()).add(next);
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

    /** Entry cost of {@code p} as a non-negative int, or throw if the weight isn't integral. */
    private static int integerWeight(MazeGrid grid, Point p) {
        double w = grid.weightOf(p);
        long rounded = Math.round(w);
        if (w < 0.0 || Double.isNaN(w) || Double.isInfinite(w)
                || Math.abs(w - rounded) > INTEGER_TOLERANCE || rounded > Integer.MAX_VALUE) {
            throw new IllegalStateException(
                    "DialSolver requires non-negative integer cell weights; found " + w + " at " + p
                            + " — use DijkstraSolver for fractional weights.");
        }
        return (int) rounded;
    }
}
