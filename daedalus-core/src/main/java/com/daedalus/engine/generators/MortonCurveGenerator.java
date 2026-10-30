// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Random;

/**
 * Morton (Z-order) curve generator.
 *
 * <p>Visits cells in Morton order — i.e. interleave the bits of (row, col) and sort —
 * carving a passage from each newly-visited cell to a previously-visited orthogonal
 * neighbor. Random choice when multiple visited neighbors exist (seeded RNG).
 *
 * <p>Why this works: decreasing either {@code row} or {@code col} by 1 strictly decreases
 * the Morton index (row bits and col bits never collide in interleaved positions), so for
 * every cell except {@code (0,0)} at least one orthogonal neighbor has already been
 * visited. That guarantees a spanning tree — i.e. a perfect maze.
 *
 * <p>Bias: characteristic Z-quadrant locality. The maze tends to form 2×2, 4×4, 8×8 nested
 * blocks of densely-connected cells joined by sparse seams along quadrant boundaries.
 * Visually distinct from every other generator in the catalog — it's the only one whose
 * structural texture comes from a space-filling curve rather than randomized search.
 *
 * <p>Complexity: O(n log n) dominated by the Morton-order sort. Carving is O(n).
 */
public class MortonCurveGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "morton-curve"; }
    @Override public String displayName() { return "Morton Curve (Z-order)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n log n) — sort dominates",
                "Z-order quadrant locality; nested 2^k block structure",
                "Visits cells in Morton (Z-order) sequence, carving back to a visited neighbor. "
                        + "Produces a perfect maze with a recursive quadrant texture unlike any "
                        + "search-based generator.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        // Build cell list and sort by Morton index.
        List<Point> ordered = new ArrayList<>(rows * cols);
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                ordered.add(new Point(r, c));
            }
        }
        ordered.sort(Comparator.comparingLong(p -> mortonIndex(p.row(), p.col())));

        boolean[][] visited = new boolean[rows][cols];

        // First cell: just mark as visited, no carve needed.
        Point first = ordered.get(0);
        visited[first.row()][first.col()] = true;
        stats.incVisited();

        for (int i = 1; i < ordered.size(); i++) {
            Point p = ordered.get(i);
            stats.recordFrontier(ordered.size() - i);

            // Collect already-visited orthogonal neighbors.
            List<Direction> candidates = new ArrayList<>(4);
            for (Direction d : Direction.values()) {
                Point n = p.step(d);
                if (grid.inBounds(n) && visited[n.row()][n.col()]) {
                    candidates.add(d);
                }
            }

            // Invariant: candidates non-empty for every cell after the first
            // (Morton order guarantees a smaller-index orthogonal neighbor exists).
            Direction carveDir = candidates.get(rng.nextInt(candidates.size()));
            grid.carve(grid.cell(p), carveDir);
            visited[p.row()][p.col()] = true;
            stats.incVisited();
        }

        stats.finish(true);
        return grid;
    }

    /**
     * Interleave the low bits of {@code row} and {@code col} into a single Morton index.
     * Handles up to 32-bit coordinates which is far more than any sane maze size.
     */
    private static long mortonIndex(int row, int col) {
        return (spreadBits(row) << 1) | spreadBits(col);
    }

    /** Spread the low 32 bits of {@code x} into the even bit positions of a long. */
    private static long spreadBits(int x) {
        long v = x & 0xFFFFFFFFL;
        v = (v | (v << 16)) & 0x0000FFFF0000FFFFL;
        v = (v | (v << 8))  & 0x00FF00FF00FF00FFL;
        v = (v | (v << 4))  & 0x0F0F0F0F0F0F0F0FL;
        v = (v | (v << 2))  & 0x3333333333333333L;
        v = (v | (v << 1))  & 0x5555555555555555L;
        return v;
    }
}
