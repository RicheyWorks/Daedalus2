// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G240 The Ballast Grid: stow ballast blocks weighing {@code 1..n^2} in the ark's {@code n x n}
 * hold so every row, column and both diagonals weigh the magic weight {@code n(n^2+1)/2}.
 * {@link #build} uses the Siamese method for odd holds, the complement pattern for doubly-even
 * holds and Strachey's quadrant method for singly-even holds; no such grid exists for n = 2.
 */
public final class BallastGrid {

    public static final String QUEST_ID = "q_ballast_grid";
    public static final int MAX_HOLD = 1000;

    private BallastGrid() { }

    public static long magicWeight(int n) {
        if (n < 1) {
            throw new IllegalArgumentException("n < 1");
        }
        return (long) n * ((long) n * n + 1) / 2;
    }

    /** Ballast grid for an n x n hold; {@code grid[row][col]}. */
    public static int[][] build(int n) {
        if (n < 1 || n > MAX_HOLD || n == 2) {
            throw new IllegalArgumentException("no ballast grid for n = " + n);
        }
        if (n % 2 != 0) {
            return odd(n);
        }
        return n % 4 == 0 ? doublyEven(n) : singlyEven(n);
    }

    private static int[][] odd(int n) {
        int[][] g = new int[n][n];
        int i = 0;
        int j = n / 2;
        for (int v = 1; v <= n * n; v++) {
            g[i][j] = v;
            int ni = (i - 1 + n) % n;
            int nj = (j + 1) % n;
            if (g[ni][nj] != 0) {
                ni = (i + 1) % n;
                nj = j;
            }
            i = ni;
            j = nj;
        }
        return g;
    }

    private static int[][] doublyEven(int n) {
        int[][] g = new int[n][n];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                int v = i * n + j + 1;
                boolean flip = (i % 4 == j % 4) || ((i % 4) + (j % 4) == 3);
                g[i][j] = flip ? n * n + 1 - v : v;
            }
        }
        return g;
    }

    private static int[][] singlyEven(int n) {
        int u = n / 2;
        int[][] a = odd(u);
        int uu = u * u;
        int[][] g = new int[n][n];
        for (int i = 0; i < u; i++) {
            for (int j = 0; j < u; j++) {
                g[i][j] = a[i][j];
                g[i + u][j + u] = a[i][j] + uu;
                g[i][j + u] = a[i][j] + 2 * uu;
                g[i + u][j] = a[i][j] + 3 * uu;
            }
        }
        int k = (n - 2) / 4;
        for (int i = 0; i < u; i++) {
            for (int c = 0; c < k; c++) {
                int j = i == u / 2 ? c + 1 : c;
                swap(g, i, j, i + u, j);
            }
            for (int c = 0; c < k - 1; c++) {
                int j = n - 1 - c;
                swap(g, i, j, i + u, j);
            }
        }
        return g;
    }

    private static void swap(int[][] g, int r1, int c1, int r2, int c2) {
        int t = g[r1][c1];
        g[r1][c1] = g[r2][c2];
        g[r2][c2] = t;
    }

    /** True when {@code g} holds 1..n^2 once each with every line at the magic weight. */
    public static boolean valid(int[][] g) {
        int n = g.length;
        if (n == 0) {
            return false;
        }
        for (int[] row : g) {
            if (row == null || row.length != n) {
                return false;
            }
        }
        long target = magicWeight(n);
        boolean[] seen = new boolean[n * n + 1];
        long d1 = 0;
        long d2 = 0;
        for (int i = 0; i < n; i++) {
            long row = 0;
            long col = 0;
            for (int j = 0; j < n; j++) {
                int v = g[i][j];
                if (v < 1 || v > n * n || seen[v]) {
                    return false;
                }
                seen[v] = true;
                row += v;
                col += g[j][i];
            }
            if (row != target || col != target) {
                return false;
            }
            d1 += g[i][i];
            d2 += g[i][n - 1 - i];
        }
        return d1 == target && d2 == target;
    }

    /** Quest q_ballast_grid: the bosun's stowage plan must balance the n x n hold. */
    public static boolean quest(int n, int[][] plan) {
        return plan.length == n && valid(plan);
    }
}
