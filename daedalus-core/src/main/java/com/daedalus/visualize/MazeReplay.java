// SPDX-License-Identifier: MIT

package com.daedalus.visualize;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.GridIndex;
import com.daedalus.solver.MazeSolver;
import com.daedalus.solver.SearchRecorder;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Replay a solve step by step (audit §2.2, deferred in ADR-004 "until something wants to
 * animate solves" — the web UI now does).
 *
 * <p>Runs the solver normally while a {@link SearchRecorder} recording is active, then
 * translates the recorded expansion order back into cell coordinates. The solver executes its
 * real implementation — this is observation, not simulation, so what animates is what actually
 * ran: BFS floods layer by layer, A* beelines, Trémaux wanders and backtracks.
 *
 * <p>Solvers that never touch the graph seam ({@code IDAStarSolver}, {@code WallFollowerSolver}
 * — deliberately left off it, see ADR-001 item 3) return an empty expansion list: the path is
 * still real, there is just no recorded search to replay. Callers should treat "no expansions"
 * as "replay unsupported", not as "the solver did no work".
 */
public final class MazeReplay {

    /** A solve plus the expansion order that produced it. */
    public record Replay(List<Point> path, List<Point> expansions) {
        public Replay {
            path = List.copyOf(path);
            expansions = List.copyOf(expansions);
        }
    }

    private MazeReplay() {
    }

    /** Record {@code solver} solving {@code grid} from {@code start} to {@code goal}. */
    public static Replay record(MazeSolver solver, MazeGrid grid,
                                Point start, Point goal, MazeStats stats) {
        List<Integer> order = new ArrayList<>();
        List<Point> path;
        SearchRecorder.begin(order::add);
        try {
            path = solver.solve(grid, start, goal, stats);
        } finally {
            SearchRecorder.end();
        }
        if (order.isEmpty()) {
            return new Replay(path, Collections.emptyList());
        }
        GridIndex index = new GridIndex(grid);
        List<Point> expansions = new ArrayList<>(order.size());
        for (int id : order) {
            expansions.add(index.pointOf(id));
        }
        return new Replay(path, expansions);
    }
}
