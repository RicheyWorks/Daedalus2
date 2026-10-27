// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;

/**
 * G329 The Berth Tableau: crew numbered 1..n bunk in a stepped berth block (row lengths never
 * grow going down). A berthing is standard when numbers rise along every row and down every
 * column. The hook length formula counts the berthings: n! over the product of every cell's
 * hook (cells to its right, below it, and itself).
 */
public final class BerthTableau {

    public static final String QUEST_ID = "q_berth_tableau";

    private BerthTableau() { }

    private static int checkShape(int[] shape) {
        int n = 0;
        for (int r = 0; r < shape.length; r++) {
            if (shape[r] < 1 || (r > 0 && shape[r] > shape[r - 1])) {
                throw new IllegalArgumentException("rows must be positive and non-increasing");
            }
            n += shape[r];
        }
        if (n > 400) {
            throw new IllegalArgumentException("berth block too large: " + n);
        }
        return n;
    }

    /** Number of standard berthings of the shape (hook length formula). */
    public static BigInteger count(int[] shape) {
        int n = checkShape(shape);
        BigInteger num = BigInteger.ONE;
        for (int i = 2; i <= n; i++) {
            num = num.multiply(BigInteger.valueOf(i));
        }
        BigInteger den = BigInteger.ONE;
        for (int r = 0; r < shape.length; r++) {
            for (int c = 0; c < shape[r]; c++) {
                int below = 0;
                for (int rr = r + 1; rr < shape.length && shape[rr] > c; rr++) {
                    below++;
                }
                den = den.multiply(BigInteger.valueOf(shape[r] - c + below));
            }
        }
        return num.divide(den);
    }

    /** True when the filling uses 1..n once each and rises along rows and down columns. */
    public static boolean isStandard(int[][] berth) {
        int[] shape = new int[berth.length];
        for (int r = 0; r < berth.length; r++) {
            shape[r] = berth[r].length;
        }
        int n = checkShape(shape);
        boolean[] seen = new boolean[n + 1];
        for (int r = 0; r < berth.length; r++) {
            for (int c = 0; c < berth[r].length; c++) {
                int v = berth[r][c];
                if (v < 1 || v > n || seen[v]) {
                    return false;
                }
                seen[v] = true;
                if (c > 0 && berth[r][c - 1] >= v) {
                    return false;
                }
                if (r > 0 && berth[r - 1][c] >= v) {
                    return false;
                }
            }
        }
        return true;
    }

    /** Quest q_berth_tableau: say how many standard berthings the block has. */
    public static boolean quest(int[] shape, long answer) {
        return count(shape).equals(BigInteger.valueOf(answer));
    }
}