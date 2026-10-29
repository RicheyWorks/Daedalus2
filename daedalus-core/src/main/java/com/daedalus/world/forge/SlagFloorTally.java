// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Slag Floor Tally (contest gap G270): slag piles up in a grid across the forge floor. The sweeper must give the slag
 * in any rectangle at a glance and pick the k-by-k plot with the most slag to clear first.
 *
 * <p>The tool is plain: a 2D summed-area table over a {@code long[][]} with O(1) {@link #sum} for any rectangle and
 * {@link #bestPlot} for the heaviest k-by-k square. Any project can use it for fast area sums on a grid.
 */
public final class SlagFloorTally {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_slag_floor_tally";

    /** How a sweep went. */
    public enum Grade { SWEPT, DUSTY }

    /** A k-by-k plot with its top-left corner and total slag. */
    public record Plot(int row, int col, long slag) {
    }

    private final long[][] pre;
    private final int rows;
    private final int cols;

    /** Builds the tally over a rectangular grid. */
    public SlagFloorTally(long[][] grid) {
        rows = grid.length;
        cols = rows == 0 ? 0 : grid[0].length;
        pre = new long[rows + 1][cols + 1];
        for (int r = 0; r < rows; r++) {
            if (grid[r].length != cols) {
                throw new IllegalArgumentException("grid must be rectangular");
            }
            for (int c = 0; c < cols; c++) {
                pre[r + 1][c + 1] = grid[r][c] + pre[r][c + 1] + pre[r + 1][c] - pre[r][c];
            }
        }
    }

    /** A seeded rows x cols floor with 0..maxSlag per cell. Same seed, same floor. */
    public static long[][] floor(long seed, int rows, int cols, int maxSlag) {
        if (rows < 0 || cols < 0 || maxSlag < 0) {
            throw new IllegalArgumentException("need rows, cols, maxSlag >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[][] g = new long[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                g[i][j] = r.nextInt(maxSlag + 1);
            }
        }
        return g;
    }

    /** Slag in rows r1..r2 and columns c1..c2, all inclusive. */
    public long sum(int r1, int c1, int r2, int c2) {
        if (r1 < 0 || c1 < 0 || r2 >= rows || c2 >= cols || r1 > r2 || c1 > c2) {
            throw new IllegalArgumentException("bad rectangle");
        }
        return pre[r2 + 1][c2 + 1] - pre[r1][c2 + 1] - pre[r2 + 1][c1] + pre[r1][c1];
    }

    /** Heaviest k-by-k plot (top-most, then left-most on ties). */
    public Plot bestPlot(int k) {
        if (k < 1 || k > rows || k > cols) {
            throw new IllegalArgumentException("plot does not fit the floor");
        }
        Plot best = null;
        for (int r = 0; r + k <= rows; r++) {
            for (int c = 0; c + k <= cols; c++) {
                long s = sum(r, c, r + k - 1, c + k - 1);
                if (best == null || s > best.slag()) {
                    best = new Plot(r, c, s);
                }
            }
        }
        return best;
    }

    /** SWEPT only if the chosen plot carries as much slag as the heaviest one. */
    public Grade grade(int k, int row, int col) {
        if (row < 0 || col < 0 || row + k > rows || col + k > cols) {
            return Grade.DUSTY;
        }
        return sum(row, col, row + k - 1, col + k - 1) == bestPlot(k).slag() ? Grade.SWEPT : Grade.DUSTY;
    }

    /** The Forgemaster's line for a sweep. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case SWEPT -> "Forgemaster: you found the worst of it first. The floor is safe to walk again.";
            case DUSTY -> "Forgemaster: heavier slag still waits elsewhere. Look over the floor again.";
        };
    }
}
