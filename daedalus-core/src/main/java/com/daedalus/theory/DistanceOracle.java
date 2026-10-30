// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

import java.util.Arrays;

/**
 * All-pairs shortest distances for one stored maze, precomputed once so any later query is O(1)
 * (CLRS Ch. 25 — the all-pairs problem, solved here by the unweighted special case: a BFS from
 * every cell).
 *
 * <p>Useful when the same maze is queried many times — scoring a leaderboard against the optimal
 * route, answering "how far is the goal from here" for arbitrary start/goal pairs, or ranking cells
 * by eccentricity — where re-running a search per query would be wasteful.
 *
 * <h3>The catch is memory, not time</h3>
 *
 * <p>Preprocessing is O(V·E), which is fine. Storage is the problem: the table is V² entries and
 * grows quadratically in the <em>cell count</em>, which itself is quadratic in the maze's edge
 * length. Distances are held as {@code short} (a maze of V cells has no distance above V, well
 * inside {@code short} range at these sizes), so:
 *
 * <table border="1">
 *   <caption>Table size by maze dimensions</caption>
 *   <tr><th>maze</th><th>cells</th><th>table</th></tr>
 *   <tr><td>32 x 32</td><td>1,024</td><td>2 MB</td></tr>
 *   <tr><td>64 x 64</td><td>4,096</td><td>32 MB</td></tr>
 *   <tr><td>128 x 128</td><td>16,384</td><td>512 MB</td></tr>
 * </table>
 *
 * <p>128² is already unreasonable, so {@link #MAX_CELLS} caps this at 4,096 cells and
 * {@link #precompute} refuses anything larger rather than quietly exhausting the heap. Use
 * {@link MazeMetrics#distancesFrom} for a single source on a big maze — it's one BFS and one row of
 * this table.
 */
public final class DistanceOracle {

    /** Largest cell count worth tabulating — 4,096 cells (e.g. 64x64) is a 32 MB table. */
    public static final int MAX_CELLS = 4096;

    /** Returned for pairs with no route between them. */
    public static final int UNREACHABLE = -1;

    private final int cols;
    private final int cells;
    private final short[] table;

    private DistanceOracle(int cols, int cells, short[] table) {
        this.cols = cols;
        this.cells = cells;
        this.table = table;
    }

    /**
     * Run a BFS from every cell and tabulate the results.
     *
     * @throws IllegalArgumentException if the maze has more than {@link #MAX_CELLS} cells
     */
    public static DistanceOracle precompute(MazeGrid grid) {
        int cols = grid.cols();
        int cells = grid.rows() * cols;
        if (cells > MAX_CELLS) {
            throw new IllegalArgumentException(
                    "DistanceOracle stores V^2 distances; " + cells + " cells would need "
                            + memoryBytesFor(cells) / (1024 * 1024) + " MB. Cap is " + MAX_CELLS
                            + " cells — use MazeMetrics.distancesFrom for a single source instead.");
        }

        short[] table = new short[cells * cells];
        Arrays.fill(table, (short) UNREACHABLE);
        for (int id = 0; id < cells; id++) {
            int[][] field = MazeMetrics.distancesFrom(grid, new Point(id / cols, id % cols));
            int base = id * cells;
            for (int r = 0; r < grid.rows(); r++) {
                for (int c = 0; c < cols; c++) {
                    table[base + r * cols + c] = (short) field[r][c];
                }
            }
        }
        return new DistanceOracle(cols, cells, table);
    }

    /** Bytes the distance table alone would occupy for {@code cells} cells. */
    public static long memoryBytesFor(int cells) {
        return (long) cells * cells * Short.BYTES;
    }

    /** Number of cells covered. */
    public int cells() {
        return cells;
    }

    /** Steps between two cells, or {@link #UNREACHABLE}. O(1). */
    public int distance(Point from, Point to) {
        return table[(from.row() * cols + from.col()) * cells + to.row() * cols + to.col()];
    }

    /**
     * Greatest distance from {@code from} to any cell it can reach — its eccentricity.
     * {@code 0} for an isolated cell.
     */
    public int eccentricity(Point from) {
        int base = (from.row() * cols + from.col()) * cells;
        int worst = 0;
        for (int i = 0; i < cells; i++) {
            int d = table[base + i];
            if (d > worst) {
                worst = d;
            }
        }
        return worst;
    }

    /**
     * The maze's diameter — the largest distance between any two connected cells. Matches
     * {@link MazeMetrics#diameter} on a connected maze, computed here by exhaustive scan rather
     * than double-BFS.
     */
    public int diameter() {
        int worst = 0;
        for (int i = 0; i < table.length; i++) {
            if (table[i] > worst) {
                worst = table[i];
            }
        }
        return worst;
    }
}
