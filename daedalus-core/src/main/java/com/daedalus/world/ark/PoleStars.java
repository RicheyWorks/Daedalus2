// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G399 The Pole Stars: the navigator pins one star in every row, every column and every region of
 * an n x n chart, n 1..8 (one-star Star Battle). No two stars may touch, not even diagonally.
 * Regions are labels 0..n-1 per cell. Star boards use 1 for a star and 0 for none.
 */
public final class PoleStars {

    public static final String QUEST_ID = "q_pole_stars";

    private PoleStars() { }

    private static void checkRegions(int[][] regions) {
        int n = regions.length;
        if (n < 1 || n > 8) {
            throw new IllegalArgumentException("n 1..8");
        }
        for (int[] row : regions) {
            if (row.length != n) {
                throw new IllegalArgumentException("square");
            }
            for (int v : row) {
                if (v < 0 || v >= n) {
                    throw new IllegalArgumentException("region 0..n-1");
                }
            }
        }
    }

    /** True when the star board meets every rule on the chart. */
    public static boolean isValid(int[][] regions, int[][] stars) {
        checkRegions(regions);
        int n = regions.length;
        if (stars.length != n) {
            return false;
        }
        int[] rows = new int[n];
        int[] cols = new int[n];
        int[] regs = new int[n];
        for (int r = 0; r < n; r++) {
            if (stars[r].length != n) {
                return false;
            }
            for (int c = 0; c < n; c++) {
                int v = stars[r][c];
                if (v != 0 && v != 1) {
                    return false;
                }
                if (v == 1) {
                    rows[r]++;
                    cols[c]++;
                    regs[regions[r][c]]++;
                    for (int dr = -1; dr <= 1; dr++) {
                        for (int dc = -1; dc <= 1; dc++) {
                            int rr = r + dr;
                            int cc = c + dc;
                            if ((dr != 0 || dc != 0) && rr >= 0 && rr < n && cc >= 0 && cc < n
                                && stars[rr][cc] == 1) {
                                return false;
                            }
                        }
                    }
                }
            }
        }
        for (int i = 0; i < n; i++) {
            if (rows[i] != 1 || cols[i] != 1 || regs[i] != 1) {
                return false;
            }
        }
        return true;
    }

    private static final class Search {
        final int[][] regions;
        final int n;
        final int[] at;
        final boolean[] colUsed;
        final boolean[] regUsed;
        final long limit;
        long count;
        int[][] first = new int[0][];

        Search(int[][] regions, long limit) {
            this.regions = regions;
            this.n = regions.length;
            this.at = new int[n];
            this.colUsed = new boolean[n];
            this.regUsed = new boolean[n];
            this.limit = limit;
        }

        void run(int r) {
            if (count >= limit) {
                return;
            }
            if (r == n) {
                if (count == 0) {
                    first = new int[n][n];
                    for (int i = 0; i < n; i++) {
                        first[i][at[i]] = 1;
                    }
                }
                count++;
                return;
            }
            for (int c = 0; c < n; c++) {
                int g = regions[r][c];
                if (colUsed[c] || regUsed[g] || r > 0 && Math.abs(at[r - 1] - c) <= 1) {
                    continue;
                }
                colUsed[c] = true;
                regUsed[g] = true;
                at[r] = c;
                run(r + 1);
                colUsed[c] = false;
                regUsed[g] = false;
            }
        }
    }

    /** Number of valid star boards, stopping at limit. */
    public static long count(int[][] regions, long limit) {
        checkRegions(regions);
        Search s = new Search(regions, limit);
        s.run(0);
        return s.count;
    }

    /** First valid star board, or an empty array when none exists. */
    public static int[][] solve(int[][] regions) {
        checkRegions(regions);
        Search s = new Search(regions, 1);
        s.run(0);
        return s.first;
    }

    /** Quest hook: the player's star board must meet every rule. */
    public static boolean quest(int[][] regions, int[][] answer) {
        return isValid(regions, answer);
    }
}