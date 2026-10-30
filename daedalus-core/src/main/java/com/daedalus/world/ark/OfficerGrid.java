// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G365 The Officer Grid: n ranks and n ships are posted on an n x n deck grid so each rank and
 * each ship appears once per row and column, and every (rank, ship) pair appears exactly once
 * (a Graeco-Latin square, two orthogonal Latin squares). Odd n uses (i + j, i + 2j) mod n, order 4
 * comes from the field of four elements, and products combine them.
 */
public final class OfficerGrid {

    public static final String QUEST_ID = "q_officer_grid";

    private static final int[][] GF4_A = {{0, 1, 2, 3}, {1, 0, 3, 2}, {2, 3, 0, 1}, {3, 2, 1, 0}};
    private static final int[][] GF4_B = {{0, 2, 3, 1}, {1, 3, 2, 0}, {2, 0, 1, 3}, {3, 1, 0, 2}};

    private OfficerGrid() { }

    private static boolean isLatin(int[][] a, int n) {
        if (a.length != n) {
            return false;
        }
        for (int i = 0; i < n; i++) {
            if (a[i].length != n) {
                return false;
            }
            boolean[] row = new boolean[n];
            boolean[] col = new boolean[n];
            for (int j = 0; j < n; j++) {
                int r = a[i][j];
                if (r < 0 || r >= n || row[r]) {
                    return false;
                }
                row[r] = true;
                int c = a[j][i];
                if (c < 0 || c >= n || col[c]) {
                    return false;
                }
                col[c] = true;
            }
        }
        return true;
    }

    /** True when ranks and ships are Latin squares and every pair occurs exactly once. */
    public static boolean isGraecoLatin(int[][] ranks, int[][] ships) {
        int n = ranks.length;
        if (n == 0 || !isLatin(ranks, n) || !isLatin(ships, n)) {
            return false;
        }
        boolean[] pair = new boolean[n * n];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                int p = ranks[i][j] * n + ships[i][j];
                if (pair[p]) {
                    return false;
                }
                pair[p] = true;
            }
        }
        return true;
    }

    /**
     * Builds {ranks, ships} for n = 4^a times an odd number (n up to 200); returns an empty array
     * for other n (2 and 6 have none; other even orders are not built here).
     */
    public static int[][][] build(int n) {
        if (n < 1 || n > 200) {
            throw new IllegalArgumentException("n 1..200");
        }
        int odd = n;
        int fours = 0;
        while (odd % 4 == 0) {
            odd /= 4;
            fours++;
        }
        if (odd % 2 == 0) {
            return new int[0][][];
        }
        int[][] a = new int[odd][odd];
        int[][] b = new int[odd][odd];
        for (int i = 0; i < odd; i++) {
            for (int j = 0; j < odd; j++) {
                a[i][j] = (i + j) % odd;
                b[i][j] = (i + 2 * j) % odd;
            }
        }
        for (int f = 0; f < fours; f++) {
            a = product(a, GF4_A);
            b = product(b, GF4_B);
        }
        return new int[][][] {a, b};
    }

    private static int[][] product(int[][] x, int[][] y) {
        int m = x.length;
        int k = y.length;
        int[][] out = new int[m * k][m * k];
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < m; j++) {
                for (int p = 0; p < k; p++) {
                    for (int q = 0; q < k; q++) {
                        out[i * k + p][j * k + q] = x[i][j] * k + y[p][q];
                    }
                }
            }
        }
        return out;
    }

    /** Quest q_officer_grid: post n ranks and n ships as a valid officer grid. */
    public static boolean quest(int n, int[][] ranks, int[][] ships) {
        return ranks.length == n && isGraecoLatin(ranks, ships);
    }
}