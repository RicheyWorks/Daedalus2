package com.daedalus.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeSolvedEvent;
import com.daedalus.routing.adapters.RoutingMazeSolver;
import com.daedalus.solver.MazeSolver;
import com.daedalus.solver.solvers.SolverRegistry;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

/**
 * Enhanced solver service that can use both legacy solvers and the new routing framework.
 */
@Service
public class EnhancedMazeSolverService {

    private final SolverRegistry legacySolvers;
    private final ApplicationEventPublisher events;
    private final MeterRegistry meters;
    private final RoutingMazeSolver routingSolver = new RoutingMazeSolver();

    public EnhancedMazeSolverService(SolverRegistry legacySolvers,
                                     ApplicationEventPublisher events,
                                     MeterRegistry meters) {
        this.legacySolvers = legacySolvers;
        this.events = events;
        this.meters = meters;
    }

    public record Result(List<Point> path, MazeStats stats, String solverId, boolean usedRouting) {}

    public Result solve(String solverId, MazeGrid grid, UUID mazeId) {
        return solve(solverId, grid, grid.start(), grid.goal(), mazeId);
    }

    public Result solve(String solverId, MazeGrid grid, Point start, Point goal, UUID mazeId) {
        boolean useRouting = solverId.startsWith("routing-") || solverId.equals("a-star") || solverId.equals("dijkstra");

        Timer timer = meters.timer("daedalus.solve", "algo", solverId, "routing", String.valueOf(useRouting));
        MazeStats stats = new MazeStats();

        List<Point> path = timer.record(() -> {
            if (useRouting) {
                return routingSolver.solve(grid, start, goal, stats);
            } else {
                MazeSolver solver = legacySolvers.require(solverId);
                return solver.solve(grid, start, goal, stats);
            }
        });

        events.publishEvent(new MazeSolvedEvent(this, mazeId, solverId, path, stats));
        return new Result(path, stats, solverId, useRouting);
    }
}