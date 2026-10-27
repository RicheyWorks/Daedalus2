// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.HashMap;
import java.util.Map;

/**
 * G416 The Hammock Rows: two watches sling hammocks into a rack of w columns and h rows; each
 * hammock drops to the lowest free row of its column, and the first watch with k in a line
 * (across, up or diagonal) wins, a Connect Four style gravity game. Cells are column-major with
 * row 0 at the bottom, index col * h + row, 0 = empty, 1 or 2 = watch. Gives drops, the winner
 * and an exact memoised minimax value for racks of at most {@link #MAX_SOLVE} cells.
 */
public final class HammockRows {

    public static final String QUEST_ID = "q_hammock_rows";
    public static final int MAX_SIDE = 10;
    public static final int MAX_SOLVE = 16;
    private static final int[][] DIRS = {{1, 0}, {0, 1}, {1, 1}, {1, -1}};

    private final int w;
    private final int h;
    private final int k;
    private final Map<Long, Integer> memo = new HashMap<>();

    /** A rack of w x h (each 1 to 10) with line length k (3 to 6). */
    public HammockRows(int w, int h, int k) {
        if (w < 1 || h < 1 || w > MAX_SIDE || h > MAX_SIDE || k < 3 || k > 6) {
            throw new IllegalArgumentException("rack or line length out of range");
        }
        this.w = w;
        this.h = h;
        this.k = k;
    }

    private void check(int[] cells) {
        if (cells == null || cells.length != w * h) {
            throw new IllegalArgumentException("rack must have w * h cells");
        }
        for (int c = 0; c < w; c++) {
            boolean gap = false;
            for (int r = 0; r < h; r++) {
                int v = cells[c * h + r];
                if (v < 0 || v > 2 || (gap && v != 0)) {
                    throw new IllegalArgumentException("cells must be 0-2 and stacked from the bottom");
                }
                gap |= v == 0;
            }
        }
    }

    /** Lowest free row in the column, or -1 when it is full. */
    public int height(int[] cells, int col) {
        check(cells);
        for (int r = 0; r < h; r++) {
            if (cells[col * h + r] == 0) {
                return r;
            }
        }
        return -1;
    }

    /** New rack after the watch drops a hammock in the column. */
    public int[] drop(int[] cells, int col, int who) {
        if (col < 0 || col >= w || (who != 1 && who != 2)) {
            throw new IllegalArgumentException("bad drop");
        }
        int r = height(cells, col);
        if (r < 0) {
            throw new IllegalArgumentException("column full: " + col);
        }
        int[] out = cells.clone();
        out[col * h + r] = who;
        return out;
    }

    /** The watch with k in a line, or 0 when neither has one. */
    public int winner(int[] cells) {
        check(cells);
        return line(cells);
    }

    private int line(int[] b) {
        for (int c = 0; c < w; c++) {
            for (int r = 0; r < h; r++) {
                int v = b[c * h + r];
                if (v == 0) {
                    continue;
                }
                for (int[] d : DIRS) {
                    int n = 1;
                    int cc = c + d[0];
                    int rr = r + d[1];
                    while (n < k && cc < w && rr >= 0 && rr < h && b[cc * h + rr] == v) {
                        n++;
                        cc += d[0];
                        rr += d[1];
                    }
                    if (n == k) {
                        return v;
                    }
                }
            }
        }
        return 0;
    }

    /** +1 when the watch to move wins with perfect play, 0 for a draw, -1 for a loss. */
    public int value(int[] cells, int toMove) {
        check(cells);
        if (cells.length > MAX_SOLVE) {
            throw new IllegalArgumentException("solver limited to " + MAX_SOLVE + " cells");
        }
        if (toMove != 1 && toMove != 2) {
            throw new IllegalArgumentException("watch must be 1 or 2");
        }
        int win = line(cells);
        if (win != 0) {
            return win == toMove ? 1 : -1;
        }
        return solve(cells.clone(), toMove);
    }

    private int solve(int[] b, int who) {
        long key = who;
        for (int v : b) {
            key = key * 3 + v;
        }
        Integer c = memo.get(key);
        if (c != null) {
            return c;
        }
        int best = -2;
        for (int col = 0; col < w && best < 1; col++) {
            int r = free(b, col);
            if (r < 0) {
                continue;
            }
            b[col * h + r] = who;
            int v = line(b) == who ? 1 : -solve(b, 3 - who);
            b[col * h + r] = 0;
            best = Math.max(best, v);
        }
        int out = best == -2 ? 0 : best;
        memo.put(key, out);
        return out;
    }

    private int free(int[] b, int col) {
        for (int r = 0; r < h; r++) {
            if (b[col * h + r] == 0) {
                return r;
            }
        }
        return -1;
    }

    /** Lowest column whose drop keeps the best value, or -1 when the game is over. */
    public int bestColumn(int[] cells, int toMove) {
        int want = value(cells, toMove);
        if (line(cells) != 0) {
            return -1;
        }
        for (int col = 0; col < w; col++) {
            if (free(cells, col) >= 0) {
                int[] b = drop(cells, col, toMove);
                int v = line(b) == toMove ? 1 : -value(b, 3 - toMove);
                if (v == want) {
                    return col;
                }
            }
        }
        return -1;
    }

    /** Quest q_hammock_rows: the bosun names the perfect-play result on an empty 4 x 4 rack, k = 3. */
    public static boolean quest(int answer) {
        return new HammockRows(4, 4, 3).value(new int[16], 1) == answer;
    }
}