// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.model.Direction;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * Maze crossbreeding (ADR-006 idea #5): two parent mazes of equal dimensions produce a
 * child that inherits topology from both — in visible patches — and is then repaired back
 * to full connectivity.
 *
 * <p><b>Genome.</b> The grid is tiled into {@value #BLOCK}×{@value #BLOCK} blocks and each
 * block is assigned to one parent by a seeded coin flip; an edge whose two cells lie in
 * same-parent blocks copies that parent's wall state, and an edge crossing a patch
 * boundary copies a randomly chosen parent's state. Patches (rather than per-edge
 * coin flips) are what make offspring <em>look</em> bred: you can see a Hilbert curve's
 * discipline melt into a backtracker's rivers at the seams.
 *
 * <p><b>Repair.</b> Stitched patches rarely agree, so the child usually falls apart into
 * components. A seeded Kruskal pass over the closed walls carves exactly one opening per
 * component boundary until the maze is a single component again — the cheapest possible
 * repair, adding no cycles beyond what inheritance already produced. This is the honest
 * answer to ADR-006's "stitched offspring need connectivity repair" concern: every cell
 * of the child is reachable, proven by test, whatever the parents looked like. (A parent's
 * uncarved rock is therefore opened up — crossbreeding treats every cell as habitable, so
 * dungeon parents produce fully-carved offspring; recorded, not hidden.)
 *
 * <p>Deterministic: same parents + same seed → the identical child, the same contract
 * every generator honors.
 */
public final class MazeBreeder {

    /** Patch size of the inheritance genome. */
    public static final int BLOCK = 3;

    private MazeBreeder() {
    }

    /**
     * Breed two mazes.
     *
     * @param a    first parent (not modified)
     * @param b    second parent (not modified); must match {@code a}'s dimensions
     * @param seed genome + repair seed
     * @return a fully connected child inheriting patches of both parents
     * @throws IllegalArgumentException when parent dimensions differ
     */
    public static MazeGrid breed(MazeGrid a, MazeGrid b, long seed) {
        if (a.rows() != b.rows() || a.cols() != b.cols()) {
            throw new IllegalArgumentException("parents must share dimensions: "
                    + a.rows() + "x" + a.cols() + " vs " + b.rows() + "x" + b.cols());
        }
        int rows = a.rows();
        int cols = a.cols();
        Random rng = new Random(seed);

        // The genome: which parent owns each patch.
        int blockRows = (rows + BLOCK - 1) / BLOCK;
        int blockCols = (cols + BLOCK - 1) / BLOCK;
        boolean[][] fromA = new boolean[blockRows][blockCols];
        for (int r = 0; r < blockRows; r++) {
            for (int c = 0; c < blockCols; c++) {
                fromA[r][c] = rng.nextBoolean();
            }
        }

        // Inherit edges. Only SOUTH and EAST are visited so each undirected edge is
        // decided exactly once; carve() opens both sides.
        MazeGrid child = new MazeGrid(rows, cols);
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                for (Direction d : new Direction[] {Direction.SOUTH, Direction.EAST}) {
                    int nr = r + d.dr();
                    int nc = c + d.dc();
                    if (!child.inBounds(nr, nc)) {
                        continue;
                    }
                    boolean hereA = fromA[r / BLOCK][c / BLOCK];
                    boolean thereA = fromA[nr / BLOCK][nc / BLOCK];
                    MazeGrid donor = (hereA == thereA)
                            ? (hereA ? a : b)          // interior edge: the patch's parent
                            : (rng.nextBoolean() ? a : b); // seam edge: coin-flip donor
                    if (donor.cell(r, c).isOpen(d)) {
                        child.carve(child.cell(r, c), d);
                    }
                }
            }
        }

        repairConnectivity(child, rng);
        return child;
    }

    /**
     * Seeded Kruskal over the closed walls: one carve per component merge until the child
     * is a single component. Adds the minimum number of openings, in shuffled order so
     * repairs land in different places per seed.
     */
    private static void repairConnectivity(MazeGrid child, Random rng) {
        int rows = child.rows();
        int cols = child.cols();
        int[] parent = new int[rows * cols];
        for (int i = 0; i < parent.length; i++) {
            parent[i] = i;
        }
        // Union existing open edges first.
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                for (Direction d : new Direction[] {Direction.SOUTH, Direction.EAST}) {
                    int nr = r + d.dr();
                    int nc = c + d.dc();
                    if (child.inBounds(nr, nc) && child.cell(r, c).isOpen(d)) {
                        union(parent, r * cols + c, nr * cols + nc);
                    }
                }
            }
        }
        // Candidate walls, shuffled deterministically.
        List<Point> walls = new ArrayList<>(); // encoded: (cellIndex, dirOrdinal) pairs
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                for (Direction d : new Direction[] {Direction.SOUTH, Direction.EAST}) {
                    int nr = r + d.dr();
                    int nc = c + d.dc();
                    if (child.inBounds(nr, nc) && !child.cell(r, c).isOpen(d)) {
                        walls.add(new Point(r * cols + c, d.ordinal()));
                    }
                }
            }
        }
        Collections.shuffle(walls, rng);
        for (Point w : walls) {
            int cell = w.row();
            Direction d = Direction.values()[w.col()];
            int neighbor = (cell / cols + d.dr()) * cols + (cell % cols + d.dc());
            if (find(parent, cell) != find(parent, neighbor)) {
                child.carve(child.cell(cell / cols, cell % cols), d);
                union(parent, cell, neighbor);
            }
        }
    }

    private static int find(int[] parent, int i) {
        while (parent[i] != i) {
            parent[i] = parent[parent[i]];
            i = parent[i];
        }
        return i;
    }

    private static void union(int[] parent, int i, int j) {
        parent[find(parent, i)] = find(parent, j);
    }
}
