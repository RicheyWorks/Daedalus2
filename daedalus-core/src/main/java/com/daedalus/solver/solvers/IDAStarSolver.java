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
 * <p>Uses Manhattan distance by default — admissible on a 4-connected grid.
 *
 * <h3>⚠️ Heuristic quality matters far more here than for A*</h3>
 *
 * <p>Benchmarking every solver over 12 mazes at 80x80 found this one costing <b>876 ms</b> while
 * BFS took 2.7 ms and the next-slowest took 20 ms — roughly <b>300x BFS</b>. That is not a data
 * structure problem, so no amount of tuning the traversal fixes it. It is inherent to
 * iterative deepening: each pass re-searches from scratch under a slightly larger f-bound, and
 * with unit costs the bound rises by 1 per pass, so a maze whose optimal path is hundreds of
 * steps long is re-explored hundreds of times.
 *
 * <p>A tighter heuristic attacks both halves of that — it prunes each pass <em>and</em> reduces
 * the number of passes. Measured over 6 mazes at 60x60:
 *
 * <pre>
 *   IDA* + Manhattan                 342.7 ms
 *   IDA* + LandmarkHeuristic (ALT)     8.4 ms      41x faster
 * </pre>
 *
 * <p>For comparison, the same heuristic swap saves A* only about 55% of its expansions. IDA*
 * gains 41x from it, because re-expansion multiplies every saving.
 *
 * <p><b>How to choose:</b>
 * <ul>
 *   <li>Solving the same maze repeatedly — precompute
 *       {@link com.daedalus.solver.LandmarkHeuristic} once and pass it in. This is the
 *       configuration worth using.</li>
 *   <li>One-shot solve — prefer {@link AStarSolver} or {@link BfsSolver}. ALT's precompute is a
 *       handful of BFS sweeps, which costs about as much as simply solving the maze outright, so
 *       it cannot pay for itself in a single query.</li>
 *   <li>Memory-constrained — this is the actual reason to choose IDA*: {@code O(d)} memory
 *       rather than A*'s {@code O(b^d)}. It is a memory-optimised algorithm, not a
 *       time-optimised one, and the default Manhattan heuristic makes that trade steeply.</li>
 * </ul>
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
