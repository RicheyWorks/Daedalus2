// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;

import java.util.*;

/**
 * Dead-end filling.
 *
 * <p>Iteratively "fills in" every cell with only one open passage that isn't the start
 * or goal. Each fill removes that cell from the search graph; doing so may turn its
 * single neighbor into a new dead-end, which then gets filled too. Cascade until no
 * dead-ends remain, then BFS over what survives — a corridor (possibly with branches
 * to other passable junctions) connecting start to goal.
 *
 * <p>Visually the maze "sublimates" inward from every dead branch until only the
 * skeleton between start and goal is left. On a perfect maze this skeleton IS the
 * shortest path; on imperfect mazes it's the union of all simple paths between
 * start and goal.
 *
 * <p>Two-phase: O(V) fill pass + O(V + E) BFS pass.
 */
public class DeadEndFillingSolver extends AbstractMazeSolver {

    @Override public String id() { return "dead-end-filling"; }
    @Override public String displayName() { return "Dead-End Filling"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "solver",
                "O(V + E) time, O(V) space",
                "Optimal on perfect mazes; full corridor on imperfect ones",
                "Fills every dead-end branch then BFS through the surviving cells.");
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats) {
        Set<Point> filled = new HashSet<>();

        // Initial sweep: every cell with degree ≤ 1 (and not start/goal) is a dead-end.
        Deque<Point> deadEnds = new ArrayDeque<>();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                if (p.equals(start) || p.equals(goal)) continue;
                if (grid.openNeighbors(p).size() <= 1) {
                    deadEnds.add(p);
                }
            }
        }

        while (!deadEnds.isEmpty()) {
            Point d = deadEnds.poll();
            if (!filled.add(d)) continue;
            stats.incVisited();
            // Filling d may cascade: if d's surviving neighbor now has only one
            // unfilled exit and isn't start/goal, it becomes a new dead-end.
            for (Point n : grid.openNeighbors(d)) {
                if (filled.contains(n) || n.equals(start) || n.equals(goal)) continue;
                // A plain count, not a Stream. This sits in the cascade's inner loop and runs
                // once per neighbour of every filled cell — on a maze that is mostly dead ends
                // that is the hottest line in the solver, and building a stream pipeline there
                // costs far more than the counting does.
                int survivingExits = 0;
                for (Point exit : grid.openNeighbors(n)) {
                    if (!filled.contains(exit)) {
                        survivingExits++;
                    }
                }
                if (survivingExits <= 1) deadEnds.add(n);
            }
        }

        // Phase 2: BFS through surviving (unfilled) cells.
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
                if (filled.contains(n)) continue;
                if (seen.add(n)) {
                    parent.put(n, cur);
                    queue.add(n);
                }
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }
}
