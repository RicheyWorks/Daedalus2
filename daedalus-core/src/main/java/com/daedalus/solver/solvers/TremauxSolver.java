// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;

import java.util.*;

/**
 * Trémaux's algorithm — one of the oldest known maze-solving methods, predating
 * computers (Charles Pierre Trémaux, 19th century).
 *
 * <p>The method tracks <i>edge marks</i> on every passage: 0 (untouched), 1 (traversed
 * once), 2 (traversed both ways). Rules:
 * <ol>
 *   <li>Never enter a passage already marked twice.</li>
 *   <li>Among available passages, prefer unmarked over once-marked.</li>
 *   <li>Each step, increment the mark on the passage you traverse.</li>
 * </ol>
 *
 * <p>Works on any connected maze including imperfect ones with loops. Bounded by 2|E|
 * steps because each edge is marked at most twice.
 */
public class TremauxSolver extends AbstractMazeSolver {

    @Override public String id() { return "tremaux"; }
    @Override public String displayName() { return "Trémaux"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "solver",
                "O(V + E) time, O(E) space (edge marks)",
                "Returns the traversal sequence; may include backtracking",
                "Mark passages as you walk. Prefer unmarked, never re-enter twice-marked.");
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats) {
        Map<Edge, Integer> marks = new HashMap<>();
        List<Point> path = new ArrayList<>();
        Set<Point> visited = new HashSet<>();

        Point pos = start;
        Point prev = null;
        path.add(pos);
        visited.add(pos);
        stats.incVisited();

        int maxSteps = 4 * grid.rows() * grid.cols(); // each edge ≤ 2 marks, safety bound
        for (int step = 0; step < maxSteps; step++) {
            stats.incExplored();
            stats.recordFrontier(path.size());

            if (pos.equals(goal)) {
                stats.setPathLength(path.size());
                stats.finish(true);
                return path;
            }

            // Candidate neighbors: open passages not already marked twice.
            List<Point> open = grid.openNeighbors(pos);
            List<Point> usable = new ArrayList<>(open.size());
            for (Point n : open) {
                if (markOf(marks, pos, n) < 2) usable.add(n);
            }
            if (usable.isEmpty()) {
                // Dead end with all exits twice-marked — impossible on connected maze.
                stats.finish(false);
                return Collections.emptyList();
            }

            // Sort: prefer unmarked (0), then once-marked (1). Stable order keeps it deterministic.
            final Point posF = pos;
            usable.sort(Comparator.comparingInt(n -> markOf(marks, posF, n)));
            Point next = usable.get(0);

            // Mark traversal of the edge we're about to use.
            marks.merge(Edge.of(pos, next), 1, Integer::sum);

            prev = pos;
            pos = next;
            path.add(pos);
            if (visited.add(pos)) stats.incVisited();
        }

        stats.finish(false);
        return Collections.emptyList();
    }

    private static int markOf(Map<Edge, Integer> marks, Point a, Point b) {
        return marks.getOrDefault(Edge.of(a, b), 0);
    }

    /** Canonical undirected edge — sorts endpoints so {a,b} and {b,a} hash equally. */
    private record Edge(Point lo, Point hi) {
        static Edge of(Point a, Point b) {
            int cmp = Integer.compare(a.row() * 100_000 + a.col(),
                                      b.row() * 100_000 + b.col());
            return cmp <= 0 ? new Edge(a, b) : new Edge(b, a);
        }
    }
}
