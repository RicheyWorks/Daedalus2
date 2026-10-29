// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G337 The Watch Grid: n sailors stand n watches over n days, and the roster is fair when every
 * sailor appears once in each day's row and once in each watch's column (a Latin square). The
 * mate builds the cyclic roster, checks a roster, and counts every fair roster for small crews.
 */
public final class WatchGrid {

    public static final String QUEST_ID = "q_watch_grid";

    private WatchGrid() { }

    /** Cyclic roster: day d, watch w gets sailor (d + w) mod n. */
    public static int[][] cyclic(int n) {
        if (n < 1 || n > 1000) {
            throw new IllegalArgumentException("n " + n);
        }
        int[][] g = new int[n][n];
        for (int d = 0; d < n; d++) {
            for (int w = 0; w < n; w++) {
                g[d][w] = (d + w) % n;
            }
        }
        return g;
    }

    /** True when the grid is square and each of 0..n-1 is once per row and once per column. */
    public static boolean isFair(int[][] g) {
        int n = g.length;
        if (n == 0) {
            return false;
        }
        for (int[] row : g) {
            if (row.length != n) {
                return false;
            }
        }
        for (int i = 0; i < n; i++) {
            boolean[] inRow = new boolean[n];
            boolean[] inCol = new boolean[n];
            for (int j = 0; j < n; j++) {
                int a = g[i][j];
                int b = g[j][i];
                if (a < 0 || a >= n || b < 0 || b >= n || inRow[a] || inCol[b]) {
                    return false;
                }
                inRow[a] = true;
                inCol[b] = true;
            }
        }
        return true;
    }

    /** Number of fair rosters for n sailors (1 &lt;= n &lt;= 5). */
    public static long count(int n) {
        if (n < 1 || n > 5) {
            throw new IllegalArgumentException("count supports n 1..5: " + n);
        }
        return fill(n, 0, new int[n], new int[n]);
    }

    private static long fill(int n, int cell, int[] rowUsed, int[] colUsed) {
        if (cell == n * n) {
            return 1;
        }
        int r = cell / n;
        int c = cell % n;
        long total = 0;
        for (int v = 0; v < n; v++) {
            int bit = 1 << v;
            if ((rowUsed[r] & bit) == 0 && (colUsed[c] & bit) == 0) {
                rowUsed[r] |= bit;
                colUsed[c] |= bit;
                total += fill(n, cell + 1, rowUsed, colUsed);
                rowUsed[r] &= ~bit;
                colUsed[c] &= ~bit;
            }
        }
        return total;
    }

    /** Quest q_watch_grid: hand in a fair roster for n sailors. */
    public static boolean quest(int n, int[][] answer) {
        return answer.length == n && isFair(answer);
    }
}