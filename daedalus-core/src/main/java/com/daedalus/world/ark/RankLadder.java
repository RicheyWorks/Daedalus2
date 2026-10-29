// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G375 The Rank Ladder: n officers of ranks 1..n stand in an n x n grid, each rank once per row and
 * column, with some ranks already posted and greater-than signs between some neighbouring cells
 * (Futoshiki). The solver fills cells in order and checks every sign whose two cells are filled.
 */
public final class RankLadder {

    public static final String QUEST_ID = "q_rank_ladder";

    private RankLadder() { }

    private static void checkPuzzle(int[][] given, int[][] signs) {
        int n = given.length;
        if (n < 1 || n > 5) {
            throw new IllegalArgumentException("n 1..5");
        }
        for (int[] row : given) {
            if (row.length != n) {
                throw new IllegalArgumentException("square grid");
            }
            for (int v : row) {
                if (v < 0 || v > n) {
                    throw new IllegalArgumentException("given 0..n");
                }
            }
        }
        for (int[] s : signs) {
            if (s.length != 4 || Math.abs(s[0] - s[2]) + Math.abs(s[1] - s[3]) != 1) {
                throw new IllegalArgumentException("sign joins neighbouring cells {r1, c1, r2, c2}");
            }
            for (int v : s) {
                if (v < 0 || v >= n) {
                    throw new IllegalArgumentException("sign out of grid");
                }
            }
        }
    }

    /** Number of fillings (stopping at limit). Signs are {r1, c1, r2, c2}: cell 1 greater. */
    public static int count(int[][] given, int[][] signs, int limit) {
        checkPuzzle(given, signs);
        int[] found = new int[1];
        int n = given.length;
        fill(0, new int[n][n], given, signs, limit, found, new int[0][]);
        return found[0];
    }

    /** One filling, or an empty array. */
    public static int[][] solve(int[][] given, int[][] signs) {
        checkPuzzle(given, signs);
        int n = given.length;
        int[][] out = new int[n][n];
        int[] found = new int[1];
        fill(0, new int[n][n], given, signs, 1, found, out);
        return found[0] > 0 ? out : new int[0][];
    }

    private static void fill(int cell, int[][] g, int[][] given, int[][] signs, int limit, int[] found,
            int[][] out) {
        int n = g.length;
        if (found[0] >= limit) {
            return;
        }
        if (cell == n * n) {
            found[0]++;
            if (found[0] == 1 && out.length == n) {
                for (int r = 0; r < n; r++) {
                    out[r] = g[r].clone();
                }
            }
            return;
        }
        int r = cell / n;
        int c = cell % n;
        for (int v = 1; v <= n; v++) {
            if (given[r][c] != 0 && given[r][c] != v) {
                continue;
            }
            boolean ok = true;
            for (int k = 0; k < c && ok; k++) {
                ok = g[r][k] != v;
            }
            for (int k = 0; k < r && ok; k++) {
                ok = g[k][c] != v;
            }
            g[r][c] = v;
            for (int i = 0; i < signs.length && ok; i++) {
                int[] s = signs[i];
                int a = g[s[0]][s[1]];
                int b = g[s[2]][s[3]];
                ok = a == 0 || b == 0 || a > b;
            }
            if (ok) {
                fill(cell + 1, g, given, signs, limit, found, out);
            }
            g[r][c] = 0;
        }
    }

    /** True when the grid is Latin in 1..n, keeps the givens, and obeys every sign. */
    public static boolean isSolution(int[][] given, int[][] signs, int[][] grid) {
        checkPuzzle(given, signs);
        int n = given.length;
        if (grid.length != n) {
            return false;
        }
        int[][] zeroBased = new int[n][];
        for (int r = 0; r < n; r++) {
            if (grid[r].length != n) {
                return false;
            }
            zeroBased[r] = new int[n];
            for (int c = 0; c < n; c++) {
                if (given[r][c] != 0 && given[r][c] != grid[r][c]) {
                    return false;
                }
                zeroBased[r][c] = grid[r][c] - 1;
            }
        }
        if (!WatchGrid.isFair(zeroBased)) {
            return false;
        }
        for (int[] s : signs) {
            if (grid[s[0]][s[1]] <= grid[s[2]][s[3]]) {
                return false;
            }
        }
        return true;
    }

    /** Quest q_rank_ladder: post every officer so the ladder's signs hold. */
    public static boolean quest(int[][] given, int[][] signs, int[][] answer) {
        return isSolution(given, signs, answer);
    }
}