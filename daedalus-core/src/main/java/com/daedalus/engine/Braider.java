// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * Turns a perfect maze into a <em>braided</em> one by removing dead ends.
 *
 * <p>Every generator that ships here produces a perfect maze — a spanning tree, so exactly one
 * route between any two cells and no loops. Braiding is the classic post-process that opens one
 * extra wall at a dead end (a cell with a single passage), which necessarily creates a cycle. The
 * result is a maze with genuine route choice.
 *
 * <p>This matters beyond aesthetics: several structural metrics are degenerate on a tree and only
 * become meaningful once the maze is braided.
 * <ul>
 *   <li>{@code theory.MazeFlow} — start↔goal edge connectivity is always 1 on a perfect maze;
 *       braiding is what produces min-cuts greater than 1.</li>
 *   <li>{@code theory.LongestPath} — in a tree the simple path between two cells is unique, so
 *       "longest" equals "shortest"; braiding is what makes the NP-hard search non-trivial.</li>
 * </ul>
 *
 * <p>Deterministic: dead ends are collected in row-major order and shuffled with a seeded
 * {@link Random}, so the same {@code (maze, factor, seed)} always yields the same braid. Cells are
 * re-checked as the pass proceeds — carving into a neighbour can stop it from being a dead end,
 * and such cells are skipped rather than double-carved.
 */
public final class Braider {

    private Braider() {
    }

    /**
     * Outcome of a braid pass.
     *
     * @param deadEndsBefore dead ends present when the pass started
     * @param wallsOpened    walls actually carved (one per braided dead end)
     * @param deadEndsAfter  dead ends remaining afterwards
     */
    public record BraidResult(int deadEndsBefore, int wallsOpened, int deadEndsAfter) {
    }

    /**
     * Open one wall on {@code factor} of the maze's dead ends.
     *
     * @param grid   maze to braid, modified in place
     * @param factor fraction of dead ends to remove, clamped to {@code [0.0, 1.0]};
     *               {@code 0.0} is a no-op, {@code 1.0} removes every dead end it can
     * @param seed   seed for the deterministic shuffle
     */
    public static BraidResult braid(MazeGrid grid, double factor, long seed) {
        double clamped = Math.max(0.0, Math.min(1.0, factor));
        List<Point> deadEnds = deadEnds(grid);
        int before = deadEnds.size();

        Random rng = new Random(seed);
        Collections.shuffle(deadEnds, rng);
        int target = (int) Math.round(clamped * before);

        int opened = 0;
        for (Point cell : deadEnds) {
            if (opened >= target) {
                break;
            }
            // An earlier carve may have already given this cell a second passage.
            if (grid.openNeighbors(cell).size() != 1) {
                continue;
            }
            List<Point> closed = closedNeighbors(grid, cell);
            if (closed.isEmpty()) {
                continue; // 1x1 maze, or every neighbour already open
            }
            Collections.shuffle(closed, rng);
            grid.carve(cell, closed.get(0));
            opened++;
        }
        return new BraidResult(before, opened, deadEnds(grid).size());
    }

    /** Remove every dead end this pass can reach. */
    public static BraidResult braid(MazeGrid grid, long seed) {
        return braid(grid, 1.0, seed);
    }

    /** Cells with exactly one open passage, in row-major order. */
    public static List<Point> deadEnds(MazeGrid grid) {
        List<Point> out = new ArrayList<>();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                if (grid.openNeighbors(p).size() == 1) {
                    out.add(p);
                }
            }
        }
        return out;
    }

    /** In-bounds neighbours of {@code p} that are still walled off from it. */
    private static List<Point> closedNeighbors(MazeGrid grid, Point p) {
        List<Point> open = grid.openNeighbors(p);
        List<Point> out = new ArrayList<>(4);
        for (Point n : grid.neighbors(p)) {
            if (!open.contains(n)) {
                out.add(n);
            }
        }
        return out;
    }
}
