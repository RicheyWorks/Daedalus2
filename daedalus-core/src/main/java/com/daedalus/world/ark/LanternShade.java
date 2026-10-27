// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;

/**
 * G377 The Lantern Shade: lanterns marked with numbers hang in an n x n grid. The lamplighter
 * shades some so that no number repeats among lit lanterns in any row or column, no two shaded
 * lanterns touch edge to edge, and all lit lanterns stay connected (Hitori). The solver decides
 * cells in order, never lighting a repeat or shading next to a shaded cell, and checks
 * connectivity at the end.
 */
public final class LanternShade {

    public static final String QUEST_ID = "q_lantern_shade";

    private LanternShade() { }

    private static void checkGrid(int[][] grid) {
        int n = grid.length;
        if (n < 1 || n > 6) {
            throw new IllegalArgumentException("n 1..6");
        }
        for (int[] row : grid) {
            if (row.length != n) {
                throw new IllegalArgumentException("square grid");
            }
        }
    }

    /** True when shaded (true = shaded) obeys all three rules for the grid. */
    public static boolean isValid(int[][] grid, boolean[][] shaded) {
        checkGrid(grid);
        int n = grid.length;
        if (shaded.length != n) {
            return false;
        }
        int lit = 0;
        int startR = -1;
        int startC = -1;
        for (int r = 0; r < n; r++) {
            if (shaded[r].length != n) {
                return false;
            }
            for (int c = 0; c < n; c++) {
                if (shaded[r][c]) {
                    if ((r > 0 && shaded[r - 1][c]) || (c > 0 && shaded[r][c - 1])) {
                        return false;
                    }
                    continue;
                }
                lit++;
                startR = r;
                startC = c;
                for (int k = 0; k < c; k++) {
                    if (!shaded[r][k] && grid[r][k] == grid[r][c]) {
                        return false;
                    }
                }
                for (int k = 0; k < r; k++) {
                    if (!shaded[k][c] && grid[k][c] == grid[r][c]) {
                        return false;
                    }
                }
            }
        }
        return lit > 0 && reach(shaded, startR, startC) == lit;
    }

    private static int reach(boolean[][] shaded, int r0, int c0) {
        int n = shaded.length;
        boolean[][] seen = new boolean[n][n];
        ArrayDeque<int[]> q = new ArrayDeque<>();
        q.add(new int[] {r0, c0});
        seen[r0][c0] = true;
        int count = 0;
        int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        while (!q.isEmpty()) {
            int[] p = q.poll();
            count++;
            for (int[] d : dirs) {
                int r = p[0] + d[0];
                int c = p[1] + d[1];
                if (r >= 0 && c >= 0 && r < n && c < n && !shaded[r][c] && !seen[r][c]) {
                    seen[r][c] = true;
                    q.add(new int[] {r, c});
                }
            }
        }
        return count;
    }

    /** Number of valid shadings, stopping at limit. */
    public static int count(int[][] grid, int limit) {
        checkGrid(grid);
        int n = grid.length;
        int[] found = new int[1];
        decide(0, grid, new boolean[n][n], limit, found, new boolean[0][]);
        return found[0];
    }

    /** One valid shading, or an empty array. */
    public static boolean[][] solve(int[][] grid) {
        checkGrid(grid);
        int n = grid.length;
        boolean[][] out = new boolean[n][n];
        int[] found = new int[1];
        decide(0, grid, new boolean[n][n], 1, found, out);
        return found[0] > 0 ? out : new boolean[0][];
    }

    private static void decide(int cell, int[][] grid, boolean[][] sh, int limit, int[] found, boolean[][] out) {
        int n = grid.length;
        if (found[0] >= limit) {
            return;
        }
        if (cell == n * n) {
            if (isValid(grid, sh)) {
                found[0]++;
                if (found[0] == 1 && out.length == n) {
                    for (int r = 0; r < n; r++) {
                        out[r] = sh[r].clone();
                    }
                }
            }
            return;
        }
        int r = cell / n;
        int c = cell % n;
        boolean repeat = false;
        for (int k = 0; k < c && !repeat; k++) {
            repeat = !sh[r][k] && grid[r][k] == grid[r][c];
        }
        for (int k = 0; k < r && !repeat; k++) {
            repeat = !sh[k][c] && grid[k][c] == grid[r][c];
        }
        if (!repeat) {
            sh[r][c] = false;
            decide(cell + 1, grid, sh, limit, found, out);
        }
        boolean touches = (r > 0 && sh[r - 1][c]) || (c > 0 && sh[r][c - 1]);
        if (!touches) {
            sh[r][c] = true;
            decide(cell + 1, grid, sh, limit, found, out);
            sh[r][c] = false;
        }
    }

    /** Quest q_lantern_shade: shade the grid by all three rules. */
    public static boolean quest(int[][] grid, boolean[][] answer) {
        return isValid(grid, answer);
    }
}