// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * The "hardest route" through a maze: the <em>longest simple path</em> from start to goal — and
 * an honest note on why that's hard.
 *
 * <h3>Why this is NP-hard (CLRS Ch. 34)</h3>
 *
 * <p>Unlike the shortest path (polynomial, via BFS/Dijkstra), the <b>longest simple path</b>
 * between two vertices is NP-hard. The Hamiltonian-path problem reduces to it directly: a graph
 * has a Hamiltonian path from {@code s} to {@code t} (one visiting every vertex exactly once) iff
 * the longest simple {@code s}→{@code t} path has length {@code |V| - 1}. So an efficient exact
 * longest-path routine would settle Hamiltonian path — and hence P = NP. There is no known
 * polynomial algorithm, and none is expected.
 *
 * <h3>What we actually do (CLRS Ch. 35 territory)</h3>
 *
 * <p>Exhaustive depth-first backtracking, bounded by a visit {@code budget}. Within the budget the
 * search is <b>exact</b> — it returns the true longest simple path — which is fine for the modest
 * mazes where "hardest route" is a meaningful game/level concept. If the budget is exhausted first
 * (large, highly-braided mazes, where the search tree explodes), it returns the longest path found
 * so far: a valid simple path and a lower bound on the true optimum, never a wrong or non-simple
 * one.
 *
 * <h3>Perfect mazes are the easy case</h3>
 *
 * <p>A perfect maze is a tree, and in a tree there is exactly <em>one</em> simple path between any
 * two cells. So on the generators that ship here the "longest" route is just that unique path
 * (which also happens to be the shortest). The problem only becomes hard once the maze is braided
 * — multiple routes to choose among. See {@link MazeFlow} for the complementary "how many routes
 * exist" metric.
 *
 * <p>Deterministic: neighbours are explored in {@link MazeGrid#openNeighbors(Point)} order and the
 * budget cutoff is deterministic, so a given maze always yields the same route.
 */
public final class LongestPath {

    /** Default DFS visit budget — ample for small mazes, a guard rail on large braided ones. */
    public static final long DEFAULT_BUDGET = 2_000_000L;

    private LongestPath() {
    }

    /**
     * The hardest route (longest simple path).
     *
     * @param from    start cell
     * @param to      goal cell
     * @param length  number of steps ({@code path.size() - 1}); {@code -1} if none found in budget
     * @param path    the cells from {@code from} to {@code to}, or empty if none found
     * @param exact   {@code true} if the search finished within budget (result is provably longest)
     */
    public record LongPath(Point from, Point to, int length, List<Point> path, boolean exact) {
        public LongPath {
            path = List.copyOf(path);
        }
    }

    /** Longest simple path between the grid's current start and goal. */
    public static LongPath hardestRoute(MazeGrid grid) {
        return longestSimplePath(grid, grid.start(), grid.goal(), DEFAULT_BUDGET);
    }

    /** Longest simple path from {@code start} to {@code goal} with the default budget. */
    public static LongPath longestSimplePath(MazeGrid grid, Point start, Point goal) {
        return longestSimplePath(grid, start, goal, DEFAULT_BUDGET);
    }

    /**
     * Longest simple path from {@code start} to {@code goal}, exploring at most {@code budget}
     * cells before giving up and returning the best route found so far.
     */
    public static LongPath longestSimplePath(MazeGrid grid, Point start, Point goal, long budget) {
        Search search = new Search(grid, goal, budget);
        search.run(start);
        List<Point> best = search.bestPath == null ? List.of() : search.bestPath;
        int length = best.isEmpty() ? -1 : best.size() - 1;
        return new LongPath(start, goal, length, best, !search.budgetExhausted);
    }

    /** Mutable backtracking search — kept off the public surface. */
    private static final class Search {
        private final MazeGrid grid;
        private final Point goal;
        private final Deque<Point> path = new ArrayDeque<>();
        private final Set<Point> onPath = new HashSet<>();
        private long budget;
        private boolean budgetExhausted;
        private List<Point> bestPath;
        private int bestLength = -1;

        Search(MazeGrid grid, Point goal, long budget) {
            this.grid = grid;
            this.goal = goal;
            this.budget = budget;
        }

        void run(Point start) {
            path.addLast(start);
            onPath.add(start);
            dfs(start);
        }

        private void dfs(Point current) {
            if (budget <= 0) {
                budgetExhausted = true;
                return;
            }
            budget--;

            if (current.equals(goal)) {
                int length = path.size() - 1;
                if (length > bestLength) {
                    bestLength = length;
                    bestPath = new ArrayList<>(path);
                }
                return; // a simple path must END at the goal — don't extend past it
            }

            for (Point next : grid.openNeighbors(current)) {
                if (!onPath.contains(next)) {
                    onPath.add(next);
                    path.addLast(next);
                    dfs(next);
                    path.removeLast();
                    onPath.remove(next);
                }
            }
        }
    }
}
