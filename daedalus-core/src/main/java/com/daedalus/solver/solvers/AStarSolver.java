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
 * A* with Manhattan heuristic. Admissible + consistent on a uniform-cost 4-connected
 * grid, so the result is provably optimal — same path as BFS, fewer expansions.
 *
 * <p>Edge cost into a neighbour is read from {@link MazeGrid#weightOf(Point)} so a
 * {@link com.daedalus.engine.WeightedMazeGrid} produces cost-aware routing and a plain
 * {@code MazeGrid} keeps the uniform-cost behaviour. The default Manhattan heuristic
 * remains admissible whenever every weight is {@code >= 1.0}; if your weights drop
 * below {@code 1.0}, pass a custom heuristic to the secondary constructor (e.g.
 * {@code (a, b) -> a.manhattan(b) * minWeight}) to keep optimality.
 */
public class AStarSolver extends AbstractMazeSolver {

    private final ToDoubleBiFunction<Point, Point> h;

    public AStarSolver() {
        this(Heuristics.MANHATTAN);
    }

    public AStarSolver(ToDoubleBiFunction<Point, Point> heuristic) {
        this.h = heuristic;
    }

    @Override public String id() { return "astar"; }
    @Override public String displayName() { return "A*"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "solver",
                "O(b^d) worst case; far better in practice",
                "Optimal with admissible heuristic; far fewer expansions than BFS",
                "Best-first search ranked by f(n) = g(n) + h(n).");
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats) {
        Map<Point, Point> parent = new HashMap<>();
        Map<Point, Double> gScore = new HashMap<>();
        gScore.put(start, 0.0);
        parent.put(start, null);

        PriorityQueue<Node> open = new PriorityQueue<>(Comparator.comparingDouble(Node::f));
        open.add(new Node(start, 0.0, h.applyAsDouble(start, goal)));
        Set<Point> closed = new HashSet<>();

        while (!open.isEmpty()) {
            stats.recordFrontier(open.size());
            Node cur = open.poll();
            if (!closed.add(cur.p)) continue;
            stats.incExplored();
            if (cur.p.equals(goal)) {
                List<Point> path = reconstruct(parent, start, goal);
                stats.setPathLength(path.size());
                stats.finish(true);
                return path;
            }
            for (Point n : grid.openNeighbors(cur.p)) {
                double tentative = cur.g + grid.weightOf(n); // 1.0 on plain grids, per-cell on WeightedMazeGrid
                if (tentative < gScore.getOrDefault(n, Double.POSITIVE_INFINITY)) {
                    parent.put(n, cur.p);
                    gScore.put(n, tentative);
                    open.add(new Node(n, tentative, tentative + h.applyAsDouble(n, goal)));
                    stats.incVisited();
                }
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }

    private record Node(Point p, double g, double f) {}
}
