// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.BitSet;
import java.util.Optional;
import java.util.SplittableRandom;

/**
 * Vent Levers (contest gap G294): a grid of furnace vents, some open. Pulling a lever flips its vent and the four
 * beside it. Find the fewest pulls that shut every vent, or show it cannot be done.
 *
 * <p>The tool is plain: Gaussian elimination over GF(2) on the r*c toggle system with {@link BitSet} rows, then a walk
 * over the free-variable null space (up to {@link #MAX_FREE} free variables) for the fewest pulls. Any project can use
 * it for Lights Out style puzzles or small XOR linear systems.
 */
public final class VentLevers {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_vent_levers";

    /** Most free variables the minimum search will enumerate. */
    public static final int MAX_FREE = 20;

    /** How a sealing went. */
    public enum Grade { SEALED, DRAFTY }

    private VentLevers() {
    }

    /** A seeded rows x cols grid where each vent is open with chance pct/100. Same seed, same furnace. */
    public static boolean[][] vents(long seed, int rows, int cols, int pct) {
        if (rows < 1 || cols < 1 || pct < 0 || pct > 100) {
            throw new IllegalArgumentException("need rows, cols >= 1 and 0 <= pct <= 100");
        }
        SplittableRandom r = new SplittableRandom(seed);
        boolean[][] g = new boolean[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                g[i][j] = r.nextInt(100) < pct;
            }
        }
        return g;
    }

    /** The grid after applying the pulls. */
    public static boolean[][] apply(boolean[][] open, boolean[][] pulls) {
        int rows = open.length;
        int cols = open[0].length;
        boolean[][] g = new boolean[rows][];
        for (int i = 0; i < rows; i++) {
            g[i] = open[i].clone();
        }
        int[][] d = {{0, 0}, {1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                if (pulls[i][j]) {
                    for (int[] x : d) {
                        int a = i + x[0];
                        int b = j + x[1];
                        if (a >= 0 && a < rows && b >= 0 && b < cols) {
                            g[a][b] = !g[a][b];
                        }
                    }
                }
            }
        }
        return g;
    }

    /** Fewest pulls that shut every vent, or empty if no set of pulls can. */
    public static Optional<boolean[][]> fewestPulls(boolean[][] open) {
        int rows = open.length;
        int cols = rows == 0 ? 0 : open[0].length;
        if (rows == 0 || cols == 0) {
            throw new IllegalArgumentException("need a non-empty grid");
        }
        int n = rows * cols;
        BitSet[] eq = new BitSet[n];
        for (int i = 0; i < rows; i++) {
            if (open[i].length != cols) {
                throw new IllegalArgumentException("grid must be rectangular");
            }
            for (int j = 0; j < cols; j++) {
                BitSet b = new BitSet(n + 1);
                int v = i * cols + j;
                b.set(v);
                if (i > 0) {
                    b.set(v - cols);
                }
                if (i + 1 < rows) {
                    b.set(v + cols);
                }
                if (j > 0) {
                    b.set(v - 1);
                }
                if (j + 1 < cols) {
                    b.set(v + 1);
                }
                if (open[i][j]) {
                    b.set(n);
                }
                eq[v] = b;
            }
        }
        int[] pivotCol = new int[n];
        boolean[] isPivot = new boolean[n];
        int rank = 0;
        for (int col = 0; col < n && rank < n; col++) {
            int sel = -1;
            for (int r = rank; r < n; r++) {
                if (eq[r].get(col)) {
                    sel = r;
                    break;
                }
            }
            if (sel < 0) {
                continue;
            }
            BitSet t = eq[sel];
            eq[sel] = eq[rank];
            eq[rank] = t;
            for (int r = 0; r < n; r++) {
                if (r != rank && eq[r].get(col)) {
                    eq[r].xor(eq[rank]);
                }
            }
            pivotCol[rank] = col;
            isPivot[col] = true;
            rank++;
        }
        for (int r = rank; r < n; r++) {
            if (eq[r].get(n)) {
                return Optional.empty();
            }
        }
        int[] free = new int[n - rank];
        int nf = 0;
        for (int c = 0; c < n; c++) {
            if (!isPivot[c]) {
                free[nf++] = c;
            }
        }
        if (nf > MAX_FREE) {
            throw new IllegalStateException("too many free levers to search: " + nf);
        }
        boolean[] best = new boolean[n];
        int bestCount = Integer.MAX_VALUE;
        for (long mask = 0; mask < (1L << nf); mask++) {
            boolean[] x = new boolean[n];
            for (int k = 0; k < nf; k++) {
                x[free[k]] = ((mask >> k) & 1L) == 1L;
            }
            for (int r = 0; r < rank; r++) {
                boolean v = eq[r].get(n);
                for (int k = 0; k < nf; k++) {
                    if (x[free[k]] && eq[r].get(free[k])) {
                        v = !v;
                    }
                }
                x[pivotCol[r]] = v;
            }
            int count = 0;
            for (boolean b : x) {
                count += b ? 1 : 0;
            }
            if (count < bestCount) {
                bestCount = count;
                best = x;
            }
        }
        boolean[][] out = new boolean[rows][cols];
        for (int v = 0; v < n; v++) {
            out[v / cols][v % cols] = best[v];
        }
        return Optional.of(out);
    }

    /** Number of pulls in a pull grid. */
    public static int count(boolean[][] pulls) {
        int c = 0;
        for (boolean[] row : pulls) {
            for (boolean b : row) {
                c += b ? 1 : 0;
            }
        }
        return c;
    }

    /** SEALED only if the pulls shut every vent with as few pulls as possible. */
    public static Grade grade(boolean[][] open, boolean[][] pulls) {
        for (boolean[] row : apply(open, pulls)) {
            for (boolean b : row) {
                if (b) {
                    return Grade.DRAFTY;
                }
            }
        }
        Optional<boolean[][]> best = fewestPulls(open);
        return best.isPresent() && count(pulls) == count(best.get()) ? Grade.SEALED : Grade.DRAFTY;
    }

    /** The Forgemaster's line for a sealing. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case SEALED -> "Forgemaster: every vent shut, not one lever wasted. The furnace holds its breath.";
            case DRAFTY -> "Forgemaster: cold air still whistles through, or you pulled more than needed. Again.";
        };
    }
}
