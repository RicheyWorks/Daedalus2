package com.daedalus.routing.adapters;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.routing.Graph;

import java.util.List;

public class MazeGraphAdapter implements Graph<Point> {
    private final MazeGrid grid;
    public MazeGraphAdapter(MazeGrid grid) { this.grid = grid; }

    @Override public List<Point> neighbors(Point n) { return grid.openNeighbors(n); }
    @Override public double cost(Point a, Point b) { return 1.0; }
    @Override public double estimate(Point a, Point b) {
        return Math.abs(a.row() - b.row()) + Math.abs(a.col() - b.col());
    }
}