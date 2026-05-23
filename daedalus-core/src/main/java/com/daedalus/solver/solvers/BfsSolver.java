// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;

import java.util.*;

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
        Map<Point, Point> parent = new HashMap<>();
        Queue<Point> queue = new ArrayDeque<>();
        Set<Point> seen = new HashSet<>();

        queue.add(start);
        seen.add(start);
        parent.put(start, null);

        while (!queue.isEmpty()) {
            stats.recordFrontier(queue.size());
            Point cur = queue.poll();
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
                    queue.add(n);
                    stats.incVisited();
                }
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }
}
