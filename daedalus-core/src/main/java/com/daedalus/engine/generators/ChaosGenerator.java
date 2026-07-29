// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.List;
import java.util.Random;

/**
 * Chaos Mode (audit recommendation §2.1.3): one maze, several generators.
 *
 * <p>Splits the grid into 2–3 bands along its longer dimension, hands each band to a randomly
 * chosen delegate from a fixed pool, then stitches adjacent bands together with a single door.
 * The seed drives every choice — band count, delegate per band, door positions, sub-seeds — so
 * the result is exactly as deterministic as any other generator.
 *
 * <h3>Why the spanning-tree contract survives</h3>
 *
 * <p>Each delegate produces a perfect maze over its band (a tree on the band's cells), and
 * adjacent bands are connected by exactly one carved door. Joining trees with single edges
 * yields a tree: {@code sum(Vi - 1) + (bands - 1) = V - 1} edges, connected by construction.
 * So Chaos Mode belongs on the spanning-tree roster and inherits the full connectivity and
 * awkward-shape sweeps like everyone else — no special pleading.
 *
 * <p>The point, per the audit, is stress variety for load-balancer work: texture changes
 * mid-maze (a Sidewinder band's horizontal drift colliding with Prim's uniform sprawl), and
 * the band doors are guaranteed chokepoints — exactly the features a routing policy should be
 * exercised against. Grids too small to band ({@code < 6} along the longer edge) delegate
 * whole-grid to one pool member; chaos degrades to "a random generator", not to a special case.
 */
public class ChaosGenerator extends AbstractMazeGenerator {

    /** Fast, shape-tolerant delegates with visibly different textures. */
    private static final List<MazeGenerator> POOL = List.of(
            new RecursiveBacktrackerGenerator(),
            new PrimsGenerator(),
            new KruskalsGenerator(),
            new SidewinderGenerator());

    @Override
    public String id() {
        return "chaos";
    }

    @Override
    public String displayName() {
        return "Chaos Mode";
    }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time — delegates dominate",
                "Deliberately inconsistent: each band carries its delegate's bias, and band "
                        + "doors are guaranteed chokepoints",
                "Splits the grid into bands, generates each with a randomly chosen algorithm "
                        + "(backtracker, Prim's, Kruskal's, Sidewinder), and joins bands with "
                        + "single doors. Still a perfect maze.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        boolean splitCols = cols >= rows;
        int extent = splitCols ? cols : rows;
        int bands = extent >= 9 ? 2 + rng.nextInt(2) : extent >= 6 ? 2 : 1;

        int offset = 0;
        for (int band = 0; band < bands; band++) {
            int size = (extent - offset) / (bands - band); // remaining split evenly
            MazeGenerator delegate = POOL.get(rng.nextInt(POOL.size()));
            MazeGrid sub = delegate.generate(
                    splitCols ? rows : size,
                    splitCols ? size : cols,
                    rng.nextLong(), stats);
            copyInto(sub, grid, splitCols ? 0 : offset, splitCols ? offset : 0);
            if (band > 0) {
                // One door between this band and the previous — the single edge that keeps
                // the union a tree.
                if (splitCols) {
                    int r = rng.nextInt(rows);
                    grid.carve(new Point(r, offset - 1), new Point(r, offset));
                } else {
                    int c = rng.nextInt(cols);
                    grid.carve(new Point(offset - 1, c), new Point(offset, c));
                }
            }
            offset += size;
        }
        stats.finish(true);
        return grid;
    }

    /** Replays {@code sub}'s carved passages into {@code target} at the given offset. */
    private static void copyInto(MazeGrid sub, MazeGrid target, int rowOffset, int colOffset) {
        for (int r = 0; r < sub.rows(); r++) {
            for (int c = 0; c < sub.cols(); c++) {
                Point here = new Point(r, c);
                for (Point n : sub.openNeighbors(here)) {
                    if (n.row() > r || n.col() > c) { // each edge once: east + south
                        target.carve(new Point(r + rowOffset, c + colOffset),
                                new Point(n.row() + rowOffset, n.col() + colOffset));
                    }
                }
            }
        }
    }
}
