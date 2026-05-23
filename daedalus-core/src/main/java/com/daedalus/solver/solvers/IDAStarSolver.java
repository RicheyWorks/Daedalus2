// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;
import com.daedalus.solver.Heuristics;

import java.util.*;
import java.util.function.ToDoubleBiFunction;

/**
 * Iterative-Deepening A*.
 *
 * <p>Same optimality guarantee as A* (admissible heuristic ⇒ optimal path) but uses O(d)
 * memory instead of O(b^d) — depth-first traversal pruned by an f = g + h bound that grows
 * each iteration.
 *
 * <p>Each pass: depth-bounded DFS from start, pruning any branch whose f-value exceeds
 * the current bound. Track the smallest pruned f-value; that becomes the next bound.
 *
 * <p>Uses Manhattan distance — admissible on a 4-connected grid.
 */
public class IDAStarSolver extends AbstractMazeSolver {

    private static final double INF = Double.POSITIVE_INFINITY;

    private final ToDoubleBiFunction<Point, Point> h;

    public IDAStarSolver() {
        this(Heuristics.MANHATTAN);
    }

    public IDAStarSolver(ToDoubleBiFunction<Point, Point> heuristic) {
        this.h = heuristic;
    }

    @Override public String id() { return "ida-star"; }
    @Override public String displayName() { return "IDA*"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "solver",
                "O(b^d) time, O(d) memory — A*'s optimality with DFS's footprint",
                "Optimal with admissible heuristic; constant linear memory",
                "Iterative-deepening DFS with f = g + h pruning. Each pass tightens the bound.");
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats) {
        double bound = h.applyAsDouble(start, goal);
        Deque<Point> path = new ArrayDeque<>();
        path.push(start);
        Set<Point> onPath = new HashSet<>();
        onPath.add(start);

        while (true) {
            double next = search(grid, path, onPath, 0.0, bound, goal, stats);
            if (next < 0) {  // sentinel meaning "found"
                List<Point> result = new ArrayList<>(path);
                Collections.reverse(result);
                stats.setPathLength(result.size());
                stats.finish(true);
                return result;
            }
            if (next == INF) {
                stats.finish(false);
                return Collections.emptyList();
            }
            bound = next;
        }
    }

    /**
     * Recursive bounded DFS.
     * @return -1 if goal found (and {@code path} contains the solution top-to-bottom),
     *         otherwise the minimum f-value that exceeded {@code bound} in this subtree.
     */
    private double search(MazeGrid grid, Deque<Point> path, Set<Point> onPath,
                          double g, double bound, Point goal, MazeStats stats) {
        Point cur = path.peek();
        double f = g + h.applyAsDouble(cur, goal);
        if (f > bound) return f;
        stats.incExplored();
        if (cur.equals(goal)) return -1;

        double min = INF;
        for (Point n : grid.openNeighbors(cur)) {
            if (onPath.contains(n)) continue; // avoid cycles within current DFS path
            path.push(n);
            onPath.add(n);
            stats.incVisited();
            stats.recordFrontier(path.size());
            double t = search(grid, path, onPath, g + 1.0, bound, goal, stats);
            if (t < 0) return -1;
            if (t < min) min = t;
            path.pop();
            onPath.remove(n);
        }
        return min;
    }
}
