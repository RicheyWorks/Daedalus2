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
 * Breadth-first search — the first solver moved onto the {@link com.daedalus.graph.Graph} seam
 * (ADR-001).
 *
 * <p>Traversal now runs entirely on dense node ids: an {@code int[]} ring buffer instead of a
 * {@code Queue<Point>}, {@code boolean[]}/{@code int[]} instead of {@code HashSet}/{@code HashMap},
 * and a reused adjacency buffer instead of a fresh {@code ArrayList} per expansion. Same algorithm,
 * same output, no hashing and no per-node allocation.
 */
public class BfsSolver extends AbstractMazeSolver {

    @Override public String id() { return "bfs"; }

    @Override public String displayName() { return "Breadth-First Search"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "solver",
                "O(V + E) time, O(V) space",
                "Optimal on unweighted graphs",
                "Layer-by-layer expansion. Shortest path guaranteed in unweighted mazes.");
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats) {
        MazeGraph graph = new MazeGraph(grid);
        GridIndex index = new GridIndex(grid);
        int startId = index.idOf(start);
        int goalId = index.idOf(goal);

        int nodes = graph.nodeCount();
        int[] parent = new int[nodes];
        Arrays.fill(parent, -1);
        boolean[] seen = new boolean[nodes];

        // BFS enqueues each node at most once, so the grid size is an exact capacity bound.
        int[] queue = new int[nodes];
        int head = 0;
        int tail = 0;
        int[] adjacency = new int[graph.maxDegree()];

        seen[startId] = true;
        queue[tail++] = startId;

        while (head < tail) {
            stats.recordFrontier(tail - head);
            int current = queue[head++];
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
                if (!seen[next]) {
                    seen[next] = true;
                    parent[next] = current;
                    queue[tail++] = next;
                    stats.incVisited();
                }
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }
}
