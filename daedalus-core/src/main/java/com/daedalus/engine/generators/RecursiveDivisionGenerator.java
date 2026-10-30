// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.Random;

/**
 * Recursive Division. The "wall-adder" approach — start with a fully open chamber
 * and recursively partition it with a wall containing a single passage.
 *
 * <p>Bias: rooms-and-corridors aesthetic, very straight passages, low branching.
 * Distinctly different visual character from carve-based algorithms.
 */
public class RecursiveDivisionGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "recursive-division"; }
    @Override public String displayName() { return "Recursive Division"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(log n) recursion",
                "Rooms-and-corridors look; long straight passages",
                "Wall-adder: opens a chamber then recursively bisects.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        // Step 1: open every wall (start with a fully connected chamber).
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Point p = new Point(r, c);
                for (Direction d : Direction.values()) {
                    Point n = p.step(d);
                    if (grid.inBounds(n)) grid.cell(p).open(d);
                }
            }
        }

        // Step 2: recursively divide.
        divide(grid, 0, 0, cols, rows, chooseOrientation(cols, rows, rng), rng, stats);
        stats.finish(true);
        return grid;
    }

    private enum Orient { HORIZONTAL, VERTICAL }

    private Orient chooseOrientation(int width, int height, Random rng) {
        if (width < height) return Orient.HORIZONTAL;
        if (height < width) return Orient.VERTICAL;
        return rng.nextBoolean() ? Orient.HORIZONTAL : Orient.VERTICAL;
    }

    private void divide(MazeGrid grid, int x, int y, int width, int height,
                        Orient orient, Random rng, MazeStats stats) {
        if (width < 2 || height < 2) return;

        boolean horizontal = orient == Orient.HORIZONTAL;
        int wallX = x + (horizontal ? 0 : rng.nextInt(width  - 1));
        int wallY = y + (horizontal ? rng.nextInt(height - 1) : 0);
        int passageX = wallX + (horizontal ? rng.nextInt(width)  : 0);
        int passageY = wallY + (horizontal ? 0 : rng.nextInt(height));
        int dx = horizontal ? 1 : 0;
        int dy = horizontal ? 0 : 1;
        int length = horizontal ? width : height;
        Direction dir = horizontal ? Direction.SOUTH : Direction.EAST;

        for (int i = 0; i < length; i++) {
            int wx = wallX + dx * i;
            int wy = wallY + dy * i;
            if (wx == passageX && wy == passageY) continue;
            Point p = new Point(wy, wx);
            if (!grid.inBounds(p)) continue;
            grid.cell(p).close(dir);
            Point neighbor = p.step(dir);
            if (grid.inBounds(neighbor)) grid.cell(neighbor).close(dir.opposite());
            stats.incVisited();
        }

        int nx = x;
        int ny = y;
        int w = horizontal ? width : wallX - x + 1;
        int h = horizontal ? wallY - y + 1 : height;
        divide(grid, nx, ny, w, h, chooseOrientation(w, h, rng), rng, stats);

        nx = horizontal ? x : wallX + 1;
        ny = horizontal ? wallY + 1 : y;
        w = horizontal ? width : x + width - wallX - 1;
        h = horizontal ? y + height - wallY - 1 : height;
        divide(grid, nx, ny, w, h, chooseOrientation(w, h, rng), rng, stats);
    }
}
