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
 * components. {@link #repairConnectivity} joins them back up with the fewest openings it can,
 * which is the honest answer to ADR-006's "stitched offspring need connectivity repair"
 * concern: every <em>habitable</em> cell of the child is reachable from every other, proven by
 * test, whatever the parents looked like.
 *
 * <p><b>Rock survives breeding.</b> A cell with no open side is uncarved rock rather than a
 * room, and a sparse generator's rock is the whole point of it — a {@code DungeonGenerator}
 * maze is about half rock. Repair therefore works on the habitable subgraph and tunnels
 * through rock only where leaving it would orphan a room. See {@link #repairConnectivity} for
 * what the earlier, rock-blind version measured out at.
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
                for (Direction d : FORWARD) {
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

        // Habitability comes from the patch's donor, NOT from the child's own walls after
        // inheritance. The difference is not academic: a cell's four edges are each decided
        // separately, so the lottery can seal a cell that both parents had carved. Reading
        // habitability off the stitched grid classified those accidents as rock and stranded
        // them — measured as spanning-tree parents (which contain no rock at all) producing
        // children with sealed cells. Asking the donor instead means a room stays a room and
        // only genuine rock — rock in the parent that patch came from — survives as rock.
        boolean[] habitable = new boolean[rows * cols];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                MazeGrid donor = fromA[r / BLOCK][c / BLOCK] ? a : b;
                habitable[r * cols + c] = !donor.openNeighbors(new Point(r, c)).isEmpty();
            }
        }

        repairConnectivity(child, habitable, rng);
        return child;
    }

    /** The two edge directions that cover every undirected edge exactly once. */
    private static final Direction[] FORWARD = {Direction.SOUTH, Direction.EAST};
    /** Deterministic neighbour order for the corridor search. */
    private static final Direction[] ALL =
        {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};

    /**
     * Make every <em>habitable</em> cell reachable, while leaving rock as rock.
     *
     * <p>A cell that its donor parent left uncarved is rock, not a room — half of a
     * {@code DungeonGenerator} maze is rock, and that is the trait the whole generator exists
     * to produce. The first version of this repair ran Kruskal over every closed wall in the
     * grid, which connects rock too: measured, breeding two 21×21 dungeons that were 49% and
     * 50% rock produced children that were <b>0% rock</b> on every seed. The offspring were
     * technically connected and had lost the one thing both parents were recognisable by.
     *
     * @param habitable which cells are rooms rather than rock, decided by patch donor in
     *                  {@link #breed} — see the note there on why the stitched grid cannot be
     *                  asked directly
     *
     * <p>So connectivity is required of the habitable subgraph only, in three phases:
     *
     * <ol>
     *   <li>union cells already joined by inherited openings;</li>
     *   <li>Kruskal over walls whose <em>both</em> sides are habitable — merges rooms and
     *       corridors without ever breaking into rock;</li>
     *   <li>only if habitable components still remain separated, tunnel a shortest corridor
     *       between them through rock, promoting just the cells that corridor occupies.</li>
     * </ol>
     *
     * <p>Phase 3 is what keeps the guarantee honest: rock is preserved wherever preserving it
     * does not orphan a room, and where it must yield it yields a corridor rather than the
     * whole field. Every phase is deterministic — fixed direction order, seeded shuffle — so
     * {@code (parentA, parentB, seed)} still reproduces one exact child.
     */
    private static void repairConnectivity(MazeGrid child, boolean[] habitable, Random rng) {
        int rows = child.rows();
        int cols = child.cols();
        int[] parent = new int[rows * cols];
        for (int i = 0; i < parent.length; i++) {
            parent[i] = i;
        }

        // Phase 1: union existing open edges.
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                for (Direction d : FORWARD) {
                    int nr = r + d.dr();
                    int nc = c + d.dc();
                    if (child.inBounds(nr, nc) && child.cell(r, c).isOpen(d)) {
                        union(parent, r * cols + c, nr * cols + nc);
                    }
                }
            }
        }

        // Phase 2: Kruskal, habitable-to-habitable walls only.
        List<Point> walls = new ArrayList<>(); // encoded: (cellIndex, dirOrdinal)
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                for (Direction d : FORWARD) {
                    int nr = r + d.dr();
                    int nc = c + d.dc();
                    if (child.inBounds(nr, nc) && !child.cell(r, c).isOpen(d)
                            && habitable[r * cols + c] && habitable[nr * cols + nc]) {
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

        // Phase 3: tunnel between whatever habitable components survive.
        tunnelBetweenComponents(child, parent, habitable, rows, cols);
    }

    /**
     * Join separated habitable components with shortest corridors through rock. Each pass
     * BFSes out from one component (breadth-first, so the corridor is minimal) until it
     * reaches a habitable cell of another, then carves the whole path.
     */
    private static void tunnelBetweenComponents(MazeGrid child, int[] parent, boolean[] habitable,
                                                int rows, int cols) {
        while (true) {
            int anchor = -1;
            for (int i = 0; i < habitable.length && anchor < 0; i++) {
                if (habitable[i]) {
                    anchor = find(parent, i);
                }
            }
            if (anchor < 0) {
                return; // no habitable cells at all — nothing to connect
            }
            // Any habitable cell in a different component means we are not done.
            boolean split = false;
            for (int i = 0; i < habitable.length && !split; i++) {
                split = habitable[i] && find(parent, i) != anchor;
            }
            if (!split) {
                return;
            }

            int[] prev = new int[rows * cols];
            java.util.Arrays.fill(prev, -1);
            boolean[] seen = new boolean[rows * cols];
            java.util.ArrayDeque<Integer> queue = new java.util.ArrayDeque<>();
            for (int i = 0; i < habitable.length; i++) {
                if (habitable[i] && find(parent, i) == anchor) {
                    seen[i] = true;
                    queue.add(i);
                }
            }
            int target = -1;
            while (!queue.isEmpty() && target < 0) {
                int cur = queue.poll();
                int r = cur / cols;
                int c = cur % cols;
                for (Direction d : ALL) {
                    int nr = r + d.dr();
                    int nc = c + d.dc();
                    if (!child.inBounds(nr, nc)) {
                        continue;
                    }
                    int next = nr * cols + nc;
                    if (seen[next]) {
                        continue;
                    }
                    seen[next] = true;
                    prev[next] = cur;
                    if (habitable[next] && find(parent, next) != anchor) {
                        target = next;   // reached another component: carve back along prev
                        break;
                    }
                    queue.add(next);
                }
            }
            if (target < 0) {
                return; // unreachable in a 4-connected grid; nothing further we can do
            }
            for (int at = target; prev[at] >= 0; at = prev[at]) {
                int from = prev[at];
                Direction step = directionBetween(from / cols, from % cols, at / cols, at % cols);
                if (!child.cell(from / cols, from % cols).isOpen(step)) {
                    child.carve(child.cell(from / cols, from % cols), step);
                }
                habitable[at] = true;
                habitable[from] = true;
                union(parent, from, at);
            }
        }
    }

    private static Direction directionBetween(int fromRow, int fromCol, int toRow, int toCol) {
        for (Direction d : ALL) {
            if (fromRow + d.dr() == toRow && fromCol + d.dc() == toCol) {
                return d;
            }
        }
        throw new IllegalStateException("cells are not adjacent");
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
