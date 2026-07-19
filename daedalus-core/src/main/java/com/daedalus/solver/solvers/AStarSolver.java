// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.graph.MazeGraph;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;
import com.daedalus.solver.GridIndex;
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
        // Cell-id-indexed arrays instead of Point-keyed hash collections — see GridIndex.
        // Adjacency arrives through the Graph seam (ADR-001) in a reused buffer.
        MazeGraph graph = new MazeGraph(grid);
        int[] adjacency = new int[graph.maxDegree()];
        GridIndex index = new GridIndex(grid);
        int startId = index.idOf(start);
        int goalId = index.idOf(goal);

        double[] gScore = new double[index.size()];
        Arrays.fill(gScore, Double.POSITIVE_INFINITY);
        int[] parent = new int[index.size()];
        Arrays.fill(parent, -1);
        boolean[] closed = new boolean[index.size()];
        gScore[startId] = 0.0;

        PriorityQueue<Node> open = new PriorityQueue<>(Comparator.comparingDouble(Node::f));
        open.add(new Node(startId, 0.0, h.applyAsDouble(start, goal)));

        while (!open.isEmpty()) {
            stats.recordFrontier(open.size());
            Node cur = open.poll();
            if (closed[cur.id()]) continue;
            closed[cur.id()] = true;
            stats.incExplored();
            if (cur.id() == goalId) {
                List<Point> path = reconstruct(parent, startId, goalId, index);
                stats.setPathLength(path.size());
                stats.finish(true);
                return path;
            }
            int degree = graph.neighbors(cur.id(), adjacency);
            for (int i = 0; i < degree; i++) {
                int nextId = adjacency[i];
                double tentative = cur.g() + graph.edgeWeight(cur.id(), nextId); // per-cell on WeightedMazeGrid
                if (tentative < gScore[nextId]) {
                    parent[nextId] = cur.id();
                    gScore[nextId] = tentative;
                    // The heuristic is a Point-based contract, so materialise the cell only here.
                    Point next = index.pointOf(nextId);
                    open.add(new Node(nextId, tentative, tentative + h.applyAsDouble(next, goal)));
                    stats.incVisited();
                }
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }

    private record Node(int id, double g, double f) {}
}
