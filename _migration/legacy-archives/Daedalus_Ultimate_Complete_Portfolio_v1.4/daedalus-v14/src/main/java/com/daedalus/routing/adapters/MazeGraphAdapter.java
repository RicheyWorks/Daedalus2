package com.daedalus.routing.adapters;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.routing.Graph;

import java.util.List;

/**
 * Adapts MazeGrid to the generic Graph interface.
 * This allows all existing maze solvers to work with the new routing framework.
 */
public class MazeGraphAdapter implements Graph<Point> {

    private final MazeGrid grid;

    public MazeGraphAdapter(MazeGrid grid) {
        this.grid = grid;
    }

    @Override
    public List<Point> neighbors(Point node) {
        return grid.openNeighbors(node);
    }

    @Override
    public double cost(Point from, Point to) {
        // In a maze, all moves cost 1 (can be extended for weighted mazes)
        return 1.0;
    }

    @Override
    public double estimate(Point from, Point to) {
        // Manhattan distance (perfect for grid mazes)
        return Math.abs(from.row() - to.row()) + Math.abs(from.col() - to.col());
    }
}