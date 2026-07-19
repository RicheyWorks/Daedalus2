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
        MazeGraph graph = new MazeGraph(grid);
        GridIndex index = new GridIndex(grid);
        int nodes = index.size();
        int startId = index.idOf(start);
        int goalId = index.idOf(goal);

        boolean[] filled = new boolean[nodes];
        // Nested neighbour iteration needs two buffers — the inner loop would otherwise
        // clobber the outer one's contents mid-scan.
        int[] outer = new int[graph.maxDegree()];
        int[] inner = new int[graph.maxDegree()];

        // Cascade queue. The old version could enqueue the same cell several times and threw
        // the duplicates away at poll time; enqueueing each cell at most once is equivalent —
        // a cell is filled the first time it is polled and never unfilled — and it makes V an
        // exact capacity bound instead of a guess.
        int[] deadEnds = new int[nodes];
        boolean[] queued = new boolean[nodes];
        int head = 0;
        int tail = 0;

        // Initial sweep: every cell with degree <= 1 (and not start/goal) is a dead-end.
        for (int id = 0; id < nodes; id++) {
            if (id == startId || id == goalId) {
                continue;
            }
            if (graph.neighbors(id, outer) <= 1) {
                deadEnds[tail++] = id;
                queued[id] = true;
            }
        }

        while (head < tail) {
            int d = deadEnds[head++];
            if (filled[d]) {
                continue;
            }
            filled[d] = true;
            stats.incVisited();
            // Filling d may cascade: if d's surviving neighbour now has only one unfilled
            // exit and isn't start/goal, it becomes a new dead-end.
            int degree = graph.neighbors(d, outer);
            for (int i = 0; i < degree; i++) {
                int n = outer[i];
                if (filled[n] || queued[n] || n == startId || n == goalId) {
                    continue;
                }
                // A plain count, not a Stream. This sits in the cascade's inner loop and runs
                // once per neighbour of every filled cell — on a maze that is mostly dead ends
                // that is the hottest line in the solver, and building a stream pipeline there
                // costs far more than the counting does.
                int survivingExits = 0;
                int innerDegree = graph.neighbors(n, inner);
                for (int j = 0; j < innerDegree; j++) {
                    if (!filled[inner[j]]) {
                        survivingExits++;
                    }
                }
                if (survivingExits <= 1) {
                    deadEnds[tail++] = n;
                    queued[n] = true;
                }
            }
        }

        // Phase 2: BFS through surviving (unfilled) cells.
        int[] parent = new int[nodes];
        Arrays.fill(parent, -1);
        boolean[] seen = new boolean[nodes];
        int[] queue = new int[nodes];
        int qHead = 0;
        int qTail = 0;

        queue[qTail++] = startId;
        seen[startId] = true;

        while (qHead < qTail) {
            stats.recordFrontier(qTail - qHead);
            int cur = queue[qHead++];
            stats.incExplored();
            if (cur == goalId) {
                List<Point> path = reconstruct(parent, startId, goalId, index);
                stats.setPathLength(path.size());
                stats.finish(true);
                return path;
            }
            int degree = graph.neighbors(cur, outer);
            for (int i = 0; i < degree; i++) {
                int n = outer[i];
                if (filled[n] || seen[n]) {
                    continue;
                }
                seen[n] = true;
                parent[n] = cur;
                queue[qTail++] = n;
            }
        }
        stats.finish(false);
        return Collections.emptyList();
    }
}
