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

public class DfsSolver extends AbstractMazeSolver {

    @Override public String id() { return "dfs"; }
    @Override public String displayName() { return "Depth-First Search"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "solver",
                "O(V + E) time, O(V) space",
                "NOT optimal — finds a path, not the shortest",
                "Stack-based depth-first exploration.");
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats) {
        MazeGraph graph = new MazeGraph(grid);
        GridIndex index = new GridIndex(grid);
        int nodes = index.size();
        int startId = index.idOf(start);
        int goalId = index.idOf(goal);

        // -1 is "no parent", which is also what terminates the reconstruct walk at the start.
        int[] parent = new int[nodes];
        Arrays.fill(parent, -1);
        boolean[] seen = new boolean[nodes];

        // A node is pushed at most once (the `seen` guard), so V slots is an exact bound.
        int[] stack = new int[nodes];
        int top = 0;
        int[] adjacency = new int[graph.maxDegree()];

        stack[top++] = startId;
        seen[startId] = true;

        while (top > 0) {
            stats.recordFrontier(top);
            int cur = stack[--top];
            stats.incExplored();
            if (cur == goalId) {
                List<Point> path = reconstruct(parent, startId, goalId, index);
                stats.setPathLength(path.size());
                stats.finish(true);
                return path;
            }
            // Neighbours are pushed in Direction order, so the last one is popped first —
            // identical to what ArrayDeque.push/pop did, and the traversal order depends on it.
            int degree = graph.neighbors(cur, adjacency);
            for (int i = 0; i < degree; i++) {
                int next = adjacency[i];
                if (!seen[next]) {
                    seen[next] = true;
                    parent[next] = cur;
                    stack[top++] = next;
                    stats.incVisited();
                }
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }
}
