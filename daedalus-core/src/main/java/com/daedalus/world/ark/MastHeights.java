// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G372 The Mast Heights: the harbour is an n x n grid of masts of heights 1..n, each height once per
 * row and column. A clue on an edge says how many masts a lookout there can see, since a taller mast
 * hides every shorter one behind it (a skyscraper puzzle). The solver fills cells in order and checks
 * a row's side clues when the row is done and the column clues on the last row.
 */
public final class MastHeights {

    public static final String QUEST_ID = "q_mast_heights";

    private MastHeights() { }

    /** Masts visible from the start of the line. */
    public static int visible(int[] line) {
        int seen = 0;
        int tallest = 0;
        for (int h : line) {
            if (h > tallest) {
                tallest = h;
                seen++;
            }
        }
        return seen;
    }

    private static int[] reversed(int[] a) {
        int[] r = new int[a.length];
        for (int i = 0; i < a.length; i++) {
            r[i] = a[a.length - 1 - i];
        }
        return r;
    }

    private static int[] column(int[][] g, int c) {
        int[] out = new int[g.length];
        for (int r = 0; r < g.length; r++) {
            out[r] = g[r][c];
        }
        return out;
    }

    /** Clues {top, bottom, left, right}, each of length n, for a filled grid. */
    public static int[][] clues(int[][] g) {
        int n = g.length;
        int[][] out = new int[4][n];
        for (int i = 0; i < n; i++) {
            int[] col = column(g, i);
            out[0][i] = visible(col);
            out[1][i] = visible(reversed(col));
            out[2][i] = visible(g[i]);
            out[3][i] = visible(reversed(g[i]));
        }
        return out;
    }

    private static boolean fits(int want, int got) {
        return want == 0 || want == got;
    }

    /** Number of harbours matching the clues (0 means no clue), stopping at limit; n up to 5. */
    public static int count(int[][] clues, int limit) {
        return run(clues, limit, new int[0][]);
    }

    /** One harbour matching the clues, or an empty array. */
    public static int[][] solve(int[][] clues) {
        int n = clues.length == 4 ? clues[0].length : 0;
        int[][] out = new int[n][n];
        return run(clues, 1, out) > 0 ? out : new int[0][];
    }

    private static int run(int[][] clues, int limit, int[][] out) {
        if (clues.length != 4 || limit < 1) {
            throw new IllegalArgumentException("four clue edges and limit >= 1");
        }
        int n = clues[0].length;
        if (n < 1 || n > 5) {
            throw new IllegalArgumentException("n 1..5");
        }
        for (int[] edge : clues) {
            if (edge.length != n) {
                throw new IllegalArgumentException("each edge has n clues");
            }
        }
        int[] found = new int[1];
        fill(0, new int[n][n], new int[n], new int[n], clues, limit, found, out);
        return found[0];
    }

    private static void fill(int cell, int[][] g, int[] rowUsed, int[] colUsed, int[][] clues, int limit,
            int[] found, int[][] out) {
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
        for (int h = 1; h <= n; h++) {
            int bit = 1 << h;
            if ((rowUsed[r] & bit) != 0 || (colUsed[c] & bit) != 0) {
                continue;
            }
            g[r][c] = h;
            boolean ok = true;
            if (c == n - 1) {
                ok = fits(clues[2][r], visible(g[r])) && fits(clues[3][r], visible(reversed(g[r])));
            }
            if (ok && r == n - 1) {
                int[] col = column(g, c);
                ok = fits(clues[0][c], visible(col)) && fits(clues[1][c], visible(reversed(col)));
            }
            if (ok) {
                rowUsed[r] |= bit;
                colUsed[c] |= bit;
                fill(cell + 1, g, rowUsed, colUsed, clues, limit, found, out);
                rowUsed[r] &= ~bit;
                colUsed[c] &= ~bit;
            }
        }
        g[r][c] = 0;
    }

    /** Quest q_mast_heights: hand in a harbour that matches every given clue. */
    public static boolean quest(int[][] clues, int[][] answer) {
        int n = answer.length;
        if (clues.length != 4 || n == 0 || clues[0].length != n || !WatchGrid.isFair(minusOne(answer))) {
            return false;
        }
        int[][] got = clues(answer);
        for (int e = 0; e < 4; e++) {
            for (int i = 0; i < n; i++) {
                if (!fits(clues[e][i], got[e][i])) {
                    return false;
                }
            }
        }
        return true;
    }

    private static int[][] minusOne(int[][] g) {
        int[][] out = new int[g.length][];
        for (int r = 0; r < g.length; r++) {
            out[r] = new int[g[r].length];
            for (int c = 0; c < g[r].length; c++) {
                out[r][c] = g[r][c] - 1;
            }
        }
        return out;
    }
}