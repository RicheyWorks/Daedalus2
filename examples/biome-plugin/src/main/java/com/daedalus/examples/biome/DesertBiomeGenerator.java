// SPDX-License-Identifier: MIT

package com.daedalus.examples.biome;

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
 * Desert-biome generator — Sidewinder variant with widened runs.
 *
 * <p>Companion to {@link ForestBiomeGenerator}. Where forest favours vertical
 * trunks, desert favours long horizontal "dunes" that occasionally rise.
 *
 * <p><b>Texture.</b> Same row-walk skeleton as Sidewinder, but the close-out
 * probability is {@code 1/3} instead of {@code 1/2}, so runs are noticeably
 * longer on average. When a run closes, we carve a riser north (top row
 * excepted) just like Sidewinder, preserving the perfect-maze invariant.
 *
 * <p><b>Seed contract.</b> Given the same {@code (rows, cols, seed)} the output
 * is bit-for-bit deterministic. Not seed-compatible with the built-in
 * Sidewinder — the close-out probability changes the Random consumption
 * pattern.
 *
 * @since 1.0
 */
public final class DesertBiomeGenerator extends AbstractMazeGenerator {

    /** Run-close probability. 1/3 → average run length ≈ 3, vs Sidewinder's ≈ 2. */
    private static final int RUN_CLOSE_DENOMINATOR = 3;

    @Override public String id()          { return "desert-biome"; }
    @Override public String displayName() { return "Desert Biome"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(width) space",
                "Strong horizontal bias with widened runs — long dune-like corridors",
                "Sidewinder variant with a 1/3 run-close probability (vs. 1/2). " +
                "Worked example shipped with the biome-plugin reference module.");
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
                boolean closeRun = atEastEdge
                        || (!atTopEdge && rng.nextInt(RUN_CLOSE_DENOMINATOR) == 0);

                if (closeRun) {
                    Point riser = run.get(rng.nextInt(run.size()));
                    if (!atTopEdge) grid.carve(grid.cell(riser), Direction.NORTH);
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
