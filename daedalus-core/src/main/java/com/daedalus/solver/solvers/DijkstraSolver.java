// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;

import java.util.*;

/**
 * Dijkstra's shortest-path algorithm.
 *
 * <p>On a uniform-cost grid this produces the same path as BFS — but the algorithm
 * generalizes to weighted edges where BFS no longer guarantees optimality. Edge cost
 * from the current cell to a neighbour is read from {@link MazeGrid#weightOf(Point)}
 * applied to the neighbour, so passing a {@link com.daedalus.engine.WeightedMazeGrid}
 * yields cost-aware routing transparently and a plain {@code MazeGrid} continues to
 * behave as a uniform-cost graph (every step costs {@code 1.0}).
 *
 * <p>Complexity: O((V + E) log V) with a binary-heap priority queue.
 */
public class DijkstraSolver extends AbstractMazeSolver {

    @Override public String id() { return "dijkstra"; }
    @Override public String displayName() { return "Dijkstra"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "solver",
                "O((V + E) log V) time, O(V) space",
                "Optimal on any non-negative-weight graph",
                "Greedy expansion ranked by tentative distance from start. Generalizes BFS to weighted edges.");
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats) {
        Map<Point, Point> parent = new HashMap<>();
        Map<Point, Double> dist = new HashMap<>();
        dist.put(start, 0.0);
        parent.put(start, null);

        PriorityQueue<Node> open = new PriorityQueue<>(Comparator.comparingDouble(Node::d));
        open.add(new Node(start, 0.0));
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
                double tentative = cur.d + grid.weightOf(n); // 1.0 on plain grids, per-cell on WeightedMazeGrid
                if (tentative < dist.getOrDefault(n, Double.POSITIVE_INFINITY)) {
                    parent.put(n, cur.p);
                    dist.put(n, tentative);
                    open.add(new Node(n, tentative));
                    stats.incVisited();
                }
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }

    private record Node(Point p, double d) {}
}
