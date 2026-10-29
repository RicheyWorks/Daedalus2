// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.HashMap;
import java.util.Map;

/**
 * G421 The Chalk Grid: two watches chalk marks on an m x n deck grid (the m,n,k game). In the
 * normal game the first to make k in a line (across, down or diagonal) wins; in the misere game
 * that player loses. Cells are row-major, 0 = empty, 1 or 2 = watch. Gives the line check and an
 * exact memoised minimax value (+1 / 0 / -1 for the watch to move) with a best square for grids
 * of at most {@link #MAX_SOLVE} cells.
 */
public final class ChalkGrid {

    public static final String QUEST_ID = "q_chalk_grid";
    public static final int MAX_SIDE = 8;
    public static final int MAX_SOLVE = 12;
    private static final int[][] DIRS = {{0, 1}, {1, 0}, {1, 1}, {1, -1}};

    private final int m;
    private final int n;
    private final int k;
    private final boolean misere;
    private final Map<Long, Integer> memo = new HashMap<>();

    /** A grid of rows x cols (1 to 8), line length k (3 to 5), normal or misere. */
    public ChalkGrid(int rows, int cols, int k, boolean misere) {
        if (rows < 1 || cols < 1 || rows > MAX_SIDE || cols > MAX_SIDE || k < 3 || k > 5) {
            throw new IllegalArgumentException("grid or line length out of range");
        }
        this.m = rows;
        this.n = cols;
        this.k = k;
        this.misere = misere;
    }

    private void check(int[] cells) {
        if (cells == null || cells.length != m * n) {
            throw new IllegalArgumentException("grid must have rows * cols cells");
        }
        for (int v : cells) {
            if (v < 0 || v > 2) {
                throw new IllegalArgumentException("cells are 0, 1 or 2");
            }
        }
    }

    /** The watch with k in a line, or 0 when neither has one. */
    public int lineOwner(int[] cells) {
        check(cells);
        return line(cells);
    }

    private int line(int[] b) {
        for (int r = 0; r < m; r++) {
            for (int c = 0; c < n; c++) {
                int v = b[r * n + c];
                if (v == 0) {
                    continue;
                }
                for (int[] d : DIRS) {
                    int len = 1;
                    int rr = r + d[0];
                    int cc = c + d[1];
                    while (len < k && rr < m && cc >= 0 && cc < n && b[rr * n + cc] == v) {
                        len++;
                        rr += d[0];
                        cc += d[1];
                    }
                    if (len == k) {
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
        int owner = line(cells);
        if (owner != 0) {
            return (owner == toMove) != misere ? 1 : -1;
        }
        return solve(cells.clone(), toMove);
    }

    private int score(int[] b, int who) {
        int owner = line(b);
        if (owner == 0) {
            return 2;
        }
        return (owner == who) != misere ? 1 : -1;
    }

    private int solve(int[] b, int who) {
        long key = who;
        for (int v : b) {
            key = key * 3 + v;
        }
        Integer hit = memo.get(key);
        if (hit != null) {
            return hit;
        }
        int best = -2;
        for (int i = 0; i < b.length && best < 1; i++) {
            if (b[i] == 0) {
                b[i] = who;
                int s = score(b, who);
                int v = s != 2 ? s : -solve(b, 3 - who);
                b[i] = 0;
                best = Math.max(best, v);
            }
        }
        int out = best == -2 ? 0 : best;
        memo.put(key, out);
        return out;
    }

    /** Lowest square keeping the perfect-play value, or -1 when the game is over. */
    public int bestSquare(int[] cells, int toMove) {
        int want = value(cells, toMove);
        if (line(cells) != 0) {
            return -1;
        }
        int[] b = cells.clone();
        for (int i = 0; i < b.length; i++) {
            if (b[i] == 0) {
                b[i] = toMove;
                int s = score(b, toMove);
                int v = s != 2 ? s : -solve(b, 3 - toMove);
                b[i] = 0;
                if (v == want) {
                    return i;
                }
            }
        }
        return -1;
    }

    /** Quest q_chalk_grid: the bosun names the perfect-play result of misere 3 x 3 noughts and crosses. */
    public static boolean quest(int answer) {
        return new ChalkGrid(3, 3, 3, true).value(new int[9], 1) == answer;
    }
}