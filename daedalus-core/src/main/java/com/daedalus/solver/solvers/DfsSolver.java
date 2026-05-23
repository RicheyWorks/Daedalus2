// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;

import java.util.*;

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
        Map<Point, Point> parent = new HashMap<>();
        Deque<Point> stack = new ArrayDeque<>();
        Set<Point> seen = new HashSet<>();

        stack.push(start);
        seen.add(start);
        parent.put(start, null);

        while (!stack.isEmpty()) {
            stats.recordFrontier(stack.size());
            Point cur = stack.pop();
            stats.incExplored();
            if (cur.equals(goal)) {
                List<Point> path = reconstruct(parent, start, goal);
                stats.setPathLength(path.size());
                stats.finish(true);
                return path;
            }
            for (Point n : grid.openNeighbors(cur)) {
                if (seen.add(n)) {
                    parent.put(n, cur);
                    stack.push(n);
                    stats.incVisited();
                }
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }
}
