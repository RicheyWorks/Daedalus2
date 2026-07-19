// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.graph.MazeGraph;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;
import com.daedalus.solver.GridIndex;

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
        // State lives in cell-id-indexed arrays rather than Point-keyed hash collections —
        // measured 1.47-2.00x faster on an 80^2 workload. See GridIndex.
        // Adjacency comes through the Graph seam (ADR-001) into a reused buffer, so the
        // expansion loop no longer allocates a list per node either.
        MazeGraph graph = new MazeGraph(grid);
        int[] adjacency = new int[graph.maxDegree()];
        GridIndex index = new GridIndex(grid);
        int startId = index.idOf(start);
        int goalId = index.idOf(goal);

        double[] dist = new double[index.size()];
        Arrays.fill(dist, Double.POSITIVE_INFINITY);
        int[] parent = new int[index.size()];
        Arrays.fill(parent, -1);
        boolean[] closed = new boolean[index.size()];
        dist[startId] = 0.0;

        PriorityQueue<Node> open = new PriorityQueue<>(Comparator.comparingDouble(Node::d));
        open.add(new Node(startId, 0.0));

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
                double tentative = cur.d() + graph.edgeWeight(cur.id(), nextId); // per-cell on WeightedMazeGrid
                if (tentative < dist[nextId]) {
                    parent[nextId] = cur.id();
                    dist[nextId] = tentative;
                    open.add(new Node(nextId, tentative));
                    stats.incVisited();
                }
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }

    private record Node(int id, double d) {}
}
