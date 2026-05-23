package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Randomized Prim's. Maintain a frontier of walls between visited and unvisited cells;
 * repeatedly pick a random frontier wall and carve through if it borders exactly one
 * visited cell.
 *
 * <p>Bias: many short branches, "bushy" texture, lots of dead ends. Opposite character
 * to Recursive Backtracker.
 *
 * <p>Complexity: O(n log n) time, O(n) memory.
 */
public class PrimsGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "prims"; }
    @Override public String displayName() { return "Prim's (randomized)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n log n) time, O(n) space",
                "Bushy texture; many short branches and dead ends",
                "Randomized Prim's MST. Frontier-driven, opposite bias to recursive backtracker.");
    }

    private record FrontierWall(Point inside, Point outside) {}

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        Point startP = new Point(rng.nextInt(rows), rng.nextInt(cols));
        grid.cell(startP).markVisited();
        stats.incVisited();

        List<FrontierWall> frontier = new ArrayList<>();
        addFrontier(grid, startP, frontier);

        while (!frontier.isEmpty()) {
            stats.recordFrontier(frontier.size());
            int idx = rng.nextInt(frontier.size());
            FrontierWall w = frontier.remove(idx);
            if (grid.cell(w.outside).isVisited()) continue;

            Direction d = MazeGrid.directionBetween(w.inside, w.outside);
            grid.carve(grid.cell(w.inside), d);
            grid.cell(w.outside).markVisited();
            stats.incVisited();
            addFrontier(grid, w.outside, frontier);
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }

    private void addFrontier(MazeGrid grid, Point inside, List<FrontierWall> frontier) {
        for (Direction d : Direction.values()) {
            Point n = inside.step(d);
            if (grid.inBounds(n) && !grid.cell(n).isVisited()) {
                frontier.add(new FrontierWall(inside, n));
            }
        }
    }
}
