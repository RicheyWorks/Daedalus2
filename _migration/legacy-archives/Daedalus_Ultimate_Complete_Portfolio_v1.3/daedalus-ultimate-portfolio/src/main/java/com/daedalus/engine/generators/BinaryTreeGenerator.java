package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.Random;

/**
 * Binary Tree. For each cell, randomly carve North or East. Almost trivial to implement,
 * runs in O(n) with O(1) auxiliary memory.
 *
 * <p>Bias: severe — diagonal "staircase" feel. The top row and right column are always
 * fully open corridors. Useful as a baseline for bias analysis.
 */
public class BinaryTreeGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "binary-tree"; }
    @Override public String displayName() { return "Binary Tree"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(1) auxiliary",
                "Severe NE bias; top row + right column always open",
                "Trivial cell-local carving. Great for benchmarking bias.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Point p = new Point(r, c);
                boolean canN = r > 0;
                boolean canE = c < cols - 1;
                Direction choice;
                if (canN && canE) choice = rng.nextBoolean() ? Direction.NORTH : Direction.EAST;
                else if (canN)    choice = Direction.NORTH;
                else if (canE)    choice = Direction.EAST;
                else continue;
                grid.carve(grid.cell(p), choice);
                stats.incVisited();
            }
        }
        stats.finish(true);
        return grid;
    }
}
