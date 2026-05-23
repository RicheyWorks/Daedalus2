// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.List;
import java.util.Random;

/**
 * Aldous-Broder. Walk randomly across the grid; whenever you step into an unvisited cell,
 * carve the wall you came through. Stops when all cells are visited.
 *
 * <p>Like Wilson's, this produces a uniformly random spanning tree (unbiased), but with
 * a fast start and slow end — the dual character to Wilson's.
 */
public class AldousBroderGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "aldous-broder"; }
    @Override public String displayName() { return "Aldous-Broder"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "Expected O(n²) time, O(n) space",
                "Provably unbiased; same uniform distribution as Wilson's",
                "Random walk that carves on first-visit. Slow finish.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        Point cur = new Point(rng.nextInt(rows), rng.nextInt(cols));
        grid.cell(cur).markVisited();
        int unvisited = rows * cols - 1;
        stats.incVisited();

        while (unvisited > 0) {
            stats.recordFrontier(unvisited);
            List<Point> nbrs = grid.neighbors(cur);
            Point next = nbrs.get(rng.nextInt(nbrs.size()));
            if (!grid.cell(next).isVisited()) {
                grid.carve(cur, next);
                grid.cell(next).markVisited();
                unvisited--;
                stats.incVisited();
            }
            cur = next;
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }
}
