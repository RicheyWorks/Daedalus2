// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.Arrays;

/**
 * G512 The Rigging Count: the bosun can rig the ark's n spars with any n-1 of the available lines that hold every
 * spar together without a loop, a spanning tree of the line graph. Kirchhoff's matrix-tree theorem counts the
 * riggings exactly: the determinant of the Laplacian with one spar's row and column struck out. The determinant is
 * taken by fraction-free Bareiss elimination over {@link BigInteger}, so huge counts stay exact. Parallel lines count
 * as different riggings; a line from a spar to itself never helps.
 *
 * <p>Daedalus hook: the bosun's locker shows how many riggings the deck allows; quest {@link #QUEST_ID} asks the
 * player for the count.
 */
public final class RiggingCount {

    public static final String QUEST_ID = "q_rigging_count";
    /** Most spars the bosun counts for. */
    public static final int MAX_SPARS = 200;

    private RiggingCount() { }

    /**
     * Number of spanning trees.
     *
     * @param n spars 1..{@link #MAX_SPARS}, numbered 0..n-1
     * @param lines lines {a, b}; repeats are parallel lines
     */
    public static BigInteger count(int n, int[][] lines) {
        if (n < 1 || n > MAX_SPARS) {
            throw new IllegalArgumentException("spars 1.." + MAX_SPARS + ": " + n);
        }
        long[][] lap = new long[n][n];
        for (int[] l : lines) {
            if (l.length != 2 || l[0] < 0 || l[0] >= n || l[1] < 0 || l[1] >= n) {
                throw new IllegalArgumentException("bad line " + Arrays.toString(l));
            }
            if (l[0] != l[1]) {
                lap[l[0]][l[0]]++;
                lap[l[1]][l[1]]++;
                lap[l[0]][l[1]]--;
                lap[l[1]][l[0]]--;
            }
        }
        int m = n - 1;
        BigInteger[][] a = new BigInteger[m][m];
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < m; j++) {
                a[i][j] = BigInteger.valueOf(lap[i + 1][j + 1]);
            }
        }
        return determinant(a);
    }

    /** Bareiss fraction-free determinant; the matrix is overwritten. An empty matrix has determinant 1. */
    static BigInteger determinant(BigInteger[][] a) {
        int m = a.length;
        if (m == 0) {
            return BigInteger.ONE;
        }
        int sign = 1;
        BigInteger prev = BigInteger.ONE;
        for (int k = 0; k < m - 1; k++) {
            if (a[k][k].signum() == 0) {
                int swap = -1;
                for (int i = k + 1; i < m && swap < 0; i++) {
                    if (a[i][k].signum() != 0) {
                        swap = i;
                    }
                }
                if (swap < 0) {
                    return BigInteger.ZERO;
                }
                BigInteger[] t = a[k];
                a[k] = a[swap];
                a[swap] = t;
                sign = -sign;
            }
            for (int i = k + 1; i < m; i++) {
                for (int j = k + 1; j < m; j++) {
                    a[i][j] = a[i][j].multiply(a[k][k]).subtract(a[i][k].multiply(a[k][j])).divide(prev);
                }
            }
            prev = a[k][k];
        }
        BigInteger d = a[m - 1][m - 1];
        return sign < 0 ? d.negate() : d;
    }

    /** Count for the complete deck where every pair of spars has one line: Cayley's n^(n-2). */
    public static BigInteger complete(int n) {
        if (n < 1 || n > MAX_SPARS) {
            throw new IllegalArgumentException("spars 1.." + MAX_SPARS + ": " + n);
        }
        return n <= 2 ? BigInteger.ONE : BigInteger.valueOf(n).pow(n - 2);
    }

    /** Bosun's locker sign text. */
    public static String locker(int n, int[][] lines) {
        BigInteger c = count(n, lines);
        if (c.signum() == 0) {
            return "The Rigging Count: " + n + " spars cannot all be rigged together.";
        }
        return "The Rigging Count: " + n + " spars, " + lines.length + " lines, " + c + " riggings.";
    }

    /** Quest q_rigging_count: the player names the number of riggings. */
    public static boolean quest(int n, int[][] lines, BigInteger answer) {
        return answer != null && count(n, lines).equals(answer);
    }
}