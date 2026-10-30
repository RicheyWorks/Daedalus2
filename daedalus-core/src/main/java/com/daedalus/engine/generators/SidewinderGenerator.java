// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Sidewinder. Variant of Binary Tree that processes a row at a time and randomly closes
 * "runs" by carving North from one cell of the run.
 *
 * <p>Bias: pronounced horizontal bias, but only the top row is a fully open corridor.
 * Less extreme than Binary Tree.
 */
public class SidewinderGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "sidewinder"; }
    @Override public String displayName() { return "Sidewinder"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(width) auxiliary",
                "Strong horizontal bias; top row always a single corridor",
                "Row-wise runs of east passages broken by random north risers.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        for (int r = 0; r < rows; r++) {
            List<Point> run = new ArrayList<>();
            for (int c = 0; c < cols; c++) {
                Point p = new Point(r, c);
                run.add(p);
                boolean atEastEdge = (c == cols - 1);
                boolean atTopEdge  = (r == 0);
                boolean closeOut = atEastEdge || (!atTopEdge && rng.nextInt(2) == 0);

                if (closeOut) {
                    Point member = run.get(rng.nextInt(run.size()));
                    if (!atTopEdge) grid.carve(grid.cell(member), Direction.NORTH);
                    run.clear();
                } else {
                    grid.carve(grid.cell(p), Direction.EAST);
                }
                stats.incVisited();
            }
        }
        stats.finish(true);
        return grid;
    }
}
