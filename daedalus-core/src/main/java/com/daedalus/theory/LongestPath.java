// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.graph.MazeGraph;
import com.daedalus.model.Point;
import com.daedalus.solver.GridIndex;


import java.util.ArrayList;


import java.util.List;


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
     *
     * <p><b>The search starts from a known route, not from nothing.</b> The incumbent is seeded
     * with the BFS shortest path, so whenever the two cells are connected the answer is a real
     * route — at worst the shortest one — and the DFS spends its budget improving on that rather
     * than hunting for a first success. Without the seed, a big braided maze spends two million
     * visits wandering a cycle-rich graph and never once arrives at the goal: measured on a
     * 41×41 at braid 0.5 and a 61×61 at braid 1.0, the old code returned {@code length = -1} and
     * an empty path even though a route obviously existed. A "hardest route" that answers
     * "there isn't one" on a solvable maze is worse than a conservative answer.
     *
     * <p>{@code exact} is unaffected: it still reports whether the search finished inside the
     * budget, so a seeded-but-unimproved result is correctly labelled a lower bound.
     */
    public static LongPath longestSimplePath(MazeGrid grid, Point start, Point goal, long budget) {
        Search search = new Search(grid, goal, budget);
        List<Point> known = MazeMetrics.shortestPath(grid, start, goal);
        if (!known.isEmpty()) {
            search.bestPath = known;
            search.bestLength = known.size() - 1;
        }
        search.run(start);
        List<Point> best = search.bestPath == null ? List.of() : search.bestPath;
        int length = best.isEmpty() ? -1 : best.size() - 1;
        return new LongPath(start, goal, length, best, !search.budgetExhausted);
    }

    /**
     * Mutable backtracking search — kept off the public surface.
     *
     * <p>Runs on the {@link MazeGraph} seam with dense node ids: the path is an {@code int[]}
     * stack and membership a {@code boolean[]}, rather than an {@code ArrayDeque<Point>} and a
     * {@code HashSet<Point>}. This is the hottest hashed structure that remained in the engine
     * — the {@code onPath} set was probed and mutated once per neighbour of every visited node,
     * up to {@link #DEFAULT_BUDGET} (two million) times per call — so the usual rule applies:
     * the seam pays exactly where hashing survived.
     *
     * <p>Depth is bounded by the number of cells, since a <em>simple</em> path cannot revisit
     * one, so {@code V} is an exact stack bound rather than a guess.
     *
     * <h4>Why the stack is explicit and not the JVM's</h4>
     *
     * <p>This search used to recurse, and that made "depth is bounded by the number of cells"
     * a liability rather than a reassurance: the REST surface accepts mazes up to 512×512, and
     * a perfect maze of that size is a tree whose unique start→goal path runs tens of thousands
     * of cells deep. Measured, the recursive version threw {@link StackOverflowError} on every
     * perfect maze from 200×200 up — an {@code Error}, not an exception, escaping a public
     * core API on input the server itself considers valid. Braided mazes hid it, because the
     * visit budget ran out at shallow depth before the stack did, which is exactly how a bug
     * like this survives a test suite that only exercises small or braided grids.
     *
     * <p>So the frames live in arrays sized from the grid: {@code path} holds the route,
     * {@code cursor} remembers how far each frame got through its neighbours, and depth is
     * capped by cell count with no JVM stack involved. Traversal order — and therefore the
     * result — is identical to the recursion it replaces.
     */
    private static final class Search {
        private final MazeGraph graph;
        private final GridIndex index;
        private final int goalId;
        private final int[] path;
        private final boolean[] onPath;
        private final int[][] adjacency;
        private final int[] degree;
        private final int[] cursor;
        private int depth;
        private long budget;
        private boolean budgetExhausted;
        private List<Point> bestPath;
        private int bestLength = -1;

        Search(MazeGrid grid, Point goal, long budget) {
            this.graph = new MazeGraph(grid);
            this.index = new GridIndex(grid);
            this.goalId = index.idOf(goal);
            this.budget = budget;
            int nodes = index.size();
            this.path = new int[nodes];
            this.onPath = new boolean[nodes];
            // One adjacency buffer per frame: every frame holds a live iteration over its own
            // neighbours, so a single shared buffer would be clobbered by the frame below it.
            this.adjacency = new int[nodes + 1][graph.maxDegree()];
            this.degree = new int[nodes + 1];
            this.cursor = new int[nodes + 1];
        }

        void run(Point start) {
            push(index.idOf(start));
            while (depth > 0) {
                if (budget <= 0) {
                    budgetExhausted = true;
                    return;
                }
                int frame = depth - 1;
                if (path[frame] == goalId) {
                    pop(); // a simple path must END at the goal — don't extend past it
                } else if (cursor[frame] < degree[frame]) {
                    int next = adjacency[frame][cursor[frame]++];
                    if (!onPath[next]) {
                        push(next);
                    }
                } else {
                    pop();
                }
            }
        }

        /** Enter a cell: charge the budget, record the frame, and score it if it is the goal. */
        private void push(int node) {
            budget--;
            path[depth] = node;
            onPath[node] = true;
            degree[depth] = graph.neighbors(node, adjacency[depth]);
            cursor[depth] = 0;
            depth++;
            if (node == goalId && depth - 1 > bestLength) {
                bestLength = depth - 1;
                bestPath = snapshot();
            }
        }

        private void pop() {
            depth--;
            onPath[path[depth]] = false;
        }

        /** Materialise the current stack as Points — only when a new best is found. */
        private List<Point> snapshot() {
            List<Point> out = new ArrayList<>(depth);
            for (int i = 0; i < depth; i++) {
                out.add(index.pointOf(path[i]));
            }
            return out;
        }
    }
}
