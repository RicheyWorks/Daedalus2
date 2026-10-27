// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G380 The Cage Sums: the quartermaster fills an n x n crate grid (n 1..5) with stamps 1..n so
 * every row and column holds each stamp once, and every cage of cells meets its rule (KenKen).
 * Cage ops: '+' sum, '*' product, '-' difference of two cells, '/' exact quotient of two cells,
 * '=' a single cell. Cells are numbered r*n+c; cageOf[cell] gives the cage index.
 */
public final class CageSums {

    public static final String QUEST_ID = "q_cage_sums";

    private CageSums() { }

    private static void check(int n, int[] cageOf, char[] ops, int[] targets) {
        if (n < 1 || n > 5) {
            throw new IllegalArgumentException("n 1..5");
        }
        if (cageOf.length != n * n || ops.length != targets.length) {
            throw new IllegalArgumentException("shape");
        }
        int[] size = new int[ops.length];
        for (int k : cageOf) {
            if (k < 0 || k >= ops.length) {
                throw new IllegalArgumentException("cage index");
            }
            size[k]++;
        }
        for (int k = 0; k < ops.length; k++) {
            char o = ops[k];
            boolean ok = (o == '+' || o == '*') && size[k] >= 1
                || (o == '-' || o == '/') && size[k] == 2
                || o == '=' && size[k] == 1;
            if (!ok) {
                throw new IllegalArgumentException("bad cage " + k);
            }
        }
    }

    private static boolean cageOk(int k, int[] vals, int[] cageOf, char op, int target) {
        long sum = 0;
        long prod = 1;
        int a = -1;
        int b = -1;
        for (int i = 0; i < cageOf.length; i++) {
            if (cageOf[i] != k) {
                continue;
            }
            int v = vals[i];
            sum += v;
            prod *= v;
            if (a < 0) {
                a = v;
            } else {
                b = v;
            }
        }
        switch (op) {
            case '+': return sum == target;
            case '*': return prod == target;
            case '=': return a == target;
            case '-': return Math.abs(a - b) == target;
            default:
                int hi = Math.max(a, b);
                int lo = Math.min(a, b);
                return hi == lo * target;
        }
    }

    /** True when the grid is a Latin square of 1..n meeting every cage. */
    public static boolean isValid(int[][] grid, int[] cageOf, char[] ops, int[] targets) {
        int n = grid.length;
        check(n, cageOf, ops, targets);
        int[] vals = new int[n * n];
        for (int r = 0; r < n; r++) {
            if (grid[r].length != n) {
                return false;
            }
            int rowSeen = 0;
            int colSeen = 0;
            for (int c = 0; c < n; c++) {
                int v = grid[r][c];
                int w = grid[c][r];
                if (v < 1 || v > n || w < 1 || w > n) {
                    return false;
                }
                rowSeen |= 1 << v;
                colSeen |= 1 << w;
                vals[r * n + c] = v;
            }
            if (rowSeen != colSeen || Integer.bitCount(rowSeen) != n) {
                return false;
            }
        }
        for (int k = 0; k < ops.length; k++) {
            if (!cageOk(k, vals, cageOf, ops[k], targets[k])) {
                return false;
            }
        }
        return true;
    }

    private static int[] lastCell(int[] cageOf, int cages) {
        int[] last = new int[cages];
        for (int i = 0; i < cageOf.length; i++) {
            last[cageOf[i]] = i;
        }
        return last;
    }

    private static final class Search {
        final int n;
        final int[] cageOf;
        final char[] ops;
        final int[] targets;
        final int[] last;
        final int[] vals;
        final int[] rowUsed;
        final int[] colUsed;
        final long limit;
        long count;
        int[] first = new int[0];

        Search(int n, int[] cageOf, char[] ops, int[] targets, long limit) {
            this.n = n;
            this.cageOf = cageOf.clone();
            this.ops = ops.clone();
            this.targets = targets.clone();
            this.last = lastCell(cageOf, ops.length);
            this.vals = new int[n * n];
            this.rowUsed = new int[n];
            this.colUsed = new int[n];
            this.limit = limit;
        }

        void run(int cell) {
            if (count >= limit) {
                return;
            }
            if (cell == n * n) {
                if (count == 0) {
                    first = vals.clone();
                }
                count++;
                return;
            }
            int r = cell / n;
            int c = cell % n;
            int k = cageOf[cell];
            for (int v = 1; v <= n; v++) {
                int bit = 1 << v;
                if ((rowUsed[r] & bit) != 0 || (colUsed[c] & bit) != 0) {
                    continue;
                }
                vals[cell] = v;
                if (last[k] == cell && !cageOkPartial(k)) {
                    continue;
                }
                rowUsed[r] |= bit;
                colUsed[c] |= bit;
                run(cell + 1);
                rowUsed[r] &= ~bit;
                colUsed[c] &= ~bit;
            }
            vals[cell] = 0;
        }

        boolean cageOkPartial(int k) {
            return cageOk(k, vals, cageOf, ops[k], targets[k]);
        }
    }

    /** Number of solutions, stopping at limit. */
    public static long count(int n, int[] cageOf, char[] ops, int[] targets, long limit) {
        check(n, cageOf, ops, targets);
        Search s = new Search(n, cageOf, ops, targets, limit);
        s.run(0);
        return s.count;
    }

    /** First solution in row-major order, or an empty array when none exists. */
    public static int[][] solve(int n, int[] cageOf, char[] ops, int[] targets) {
        check(n, cageOf, ops, targets);
        Search s = new Search(n, cageOf, ops, targets, 1);
        s.run(0);
        if (s.count == 0) {
            return new int[0][];
        }
        int[][] g = new int[n][n];
        for (int i = 0; i < n * n; i++) {
            g[i / n][i % n] = s.first[i];
        }
        return g;
    }

    /** Quest hook: the player's grid must satisfy the puzzle. */
    public static boolean quest(int[][] answer, int[] cageOf, char[] ops, int[] targets) {
        return answer.length >= 1 && answer.length <= 5 && isValid(answer, cageOf, ops, targets);
    }
}
