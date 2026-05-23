package com.daedalus.routing.adapters;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.routing.Graph;
import com.daedalus.routing.PathfindingAlgorithm;
import com.daedalus.routing.algorithms.AStar;
import com.daedalus.solver.AbstractMazeSolver;
import com.daedalus.solver.MazeSolver;

import java.util.List;

/**
 * Bridge between the new general routing framework and the existing MazeSolver SPI.
 * Allows all existing code (MazeSolverService, plugins, etc.) to use A*/Dijkstra transparently.
 */
public class RoutingMazeSolver extends AbstractMazeSolver implements MazeSolver {

    private final PathfindingAlgorithm<Point> algorithm;

    public RoutingMazeSolver() {
        this.algorithm = new AStar<>();
    }

    public RoutingMazeSolver(PathfindingAlgorithm<Point> algorithm) {
        this.algorithm = algorithm;
    }

    @Override
    public String id() {
        return "routing-" + algorithm.getClass().getSimpleName().toLowerCase();
    }

    @Override
    public String displayName() {
        return "Routing " + algorithm.getClass().getSimpleName();
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, com.daedalus.model.MazeStats stats) {
        Graph<Point> graph = new MazeGraphAdapter(grid);
        List<Point> path = algorithm.findPath(graph, start, goal);

        if (stats != null && !path.isEmpty()) {
            stats.setPathLength(path.size());
            stats.finish(true);
        }
        return path;
    }
}