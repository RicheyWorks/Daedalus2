// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.PriorityQueue;
import java.util.SplittableRandom;

/**
 * Quench Pools (contest gap G221): rain falls on the forge yard, a row of slag heaps (or a grid of them), and water
 * pools between the heaps where the smiths quench blades fresh from {@link FurnaceWatch}. How much water does the yard
 * hold, and where is it deepest?
 *
 * <p>The tool is plain: {@link #trapped} is the O(n) two-pointer volume over an {@code int[]}, {@link #depths} the
 * water depth per column, and {@link #trapped2d} the priority-queue flood from the rim over an {@code int[][]}. Any
 * project can use it for terrain water or basin volume.
 */
public final class QuenchPools {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_quench_pools";

    /** How the player's pick of the deepest pool went. */
    public enum Grade { FULL, SHALLOW, DRY }

    private QuenchPools() {
    }

    /** A seeded row of {@code n} heaps of height 0..maxHeight. Same seed, same yard. */
    public static int[] heaps(long seed, int n, int maxHeight) {
        if (n < 0 || maxHeight < 0) {
            throw new IllegalArgumentException("need n >= 0 and maxHeight >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] h = new int[n];
        for (int i = 0; i < n; i++) {
            h[i] = r.nextInt(maxHeight + 1);
        }
        return h;
    }

    /** A seeded rows x cols yard of heights 0..maxHeight. */
    public static int[][] yard(long seed, int rows, int cols, int maxHeight) {
        int[][] g = new int[rows][];
        for (int i = 0; i < rows; i++) {
            g[i] = heaps(seed * 31L + i, cols, maxHeight);
        }
        return g;
    }

    /** Total water held by a row, two pointers. */
    public static long trapped(int[] h) {
        int l = 0;
        int r = h.length - 1;
        int lm = 0;
        int rm = 0;
        long w = 0;
        while (l < r) {
            if (h[l] <= h[r]) {
                lm = Math.max(lm, h[l]);
                w += lm - h[l];
                l++;
            } else {
                rm = Math.max(rm, h[r]);
                w += rm - h[r];
                r--;
            }
        }
        return w;
    }

    /** Water depth above each column of a row. */
    public static int[] depths(int[] h) {
        int n = h.length;
        int[] left = new int[n];
        int[] d = new int[n];
        int m = 0;
        for (int i = 0; i < n; i++) {
            m = Math.max(m, h[i]);
            left[i] = m;
        }
        m = 0;
        for (int i = n - 1; i >= 0; i--) {
            m = Math.max(m, h[i]);
            d[i] = Math.min(left[i], m) - h[i];
        }
        return d;
    }

    /** Total water held by a grid yard (water spills off any rim cell). */
    public static long trapped2d(int[][] g) {
        int rows = g.length;
        if (rows == 0) {
            return 0;
        }
        int cols = g[0].length;
        for (int[] row : g) {
            if (row.length != cols) {
                throw new IllegalArgumentException("yard must be rectangular");
            }
        }
        boolean[][] seen = new boolean[rows][cols];
        PriorityQueue<int[]> pq = new PriorityQueue<>((a, b) -> Integer.compare(a[0], b[0]));
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                if (i == 0 || j == 0 || i == rows - 1 || j == cols - 1) {
                    seen[i][j] = true;
                    pq.add(new int[] {g[i][j], i, j});
                }
            }
        }
        int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        long w = 0;
        while (!pq.isEmpty()) {
            int[] c = pq.poll();
            for (int[] d : dirs) {
                int ni = c[1] + d[0];
                int nj = c[2] + d[1];
                if (ni >= 0 && nj >= 0 && ni < rows && nj < cols && !seen[ni][nj]) {
                    seen[ni][nj] = true;
                    w += Math.max(0, c[0] - g[ni][nj]);
                    pq.add(new int[] {Math.max(c[0], g[ni][nj]), ni, nj});
                }
            }
        }
        return w;
    }

    /** FULL if the picked column is a deepest pool, SHALLOW if it holds some water, DRY if none. */
    public static Grade grade(int[] h, int column) {
        if (column < 0 || column >= h.length) {
            throw new IllegalArgumentException("column outside the yard");
        }
        int[] d = depths(h);
        int deepest = 0;
        for (int x : d) {
            deepest = Math.max(deepest, x);
        }
        if (d[column] == 0) {
            return Grade.DRY;
        }
        return d[column] == deepest ? Grade.FULL : Grade.SHALLOW;
    }

    /** The Forgemaster's line for a pick. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case FULL -> "Forgemaster: deepest pool in the yard. Plunge it to the tang.";
            case SHALLOW -> "Forgemaster: wet, but shallow. The edge will warp.";
            case DRY -> "Forgemaster: that is dry slag. You will set the yard alight.";
        };
    }
}
