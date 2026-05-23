// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeSolvedEvent;
import com.daedalus.solver.MazeSolver;
import com.daedalus.solver.solvers.SolverRegistry;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

/** Runs solvers, records timing, fires events. */
@Service
public class MazeSolverService {

    private final SolverRegistry solvers;
    private final ApplicationEventPublisher events;
    private final MeterRegistry meters;

    public MazeSolverService(SolverRegistry solvers,
                             ApplicationEventPublisher events,
                             MeterRegistry meters) {
        this.solvers = solvers;
        this.events = events;
        this.meters = meters;
    }

    public record Result(List<Point> path, MazeStats stats, String solverId) {}

    public Result solve(String solverId, MazeGrid grid, UUID mazeId) {
        return solve(solverId, grid, grid.start(), grid.goal(), mazeId);
    }

    public Result solve(String solverId, MazeGrid grid, Point start, Point goal, UUID mazeId) {
        MazeSolver solver = solvers.require(solverId);
        Timer timer = meters.timer("daedalus.solve", "algo", solverId);
        MazeStats stats = new MazeStats();
        List<Point> path = timer.record(() -> solver.solve(grid, start, goal, stats));
        events.publishEvent(new MazeSolvedEvent(this, mazeId, solverId, path, stats));
        return new Result(path, stats, solverId);
    }
}
