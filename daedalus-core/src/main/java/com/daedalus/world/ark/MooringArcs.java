// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;

/**
 * G340 The Mooring Arcs: n posts stand in a row on the quay and mooring lines arc between pairs of
 * posts above the water; no two lines may cross and each post holds at most one line. Motzkin
 * numbers count the layouts when posts may stay free; Narayana numbers split the full layouts of
 * 2n posts by how many lines join neighbouring posts.
 */
public final class MooringArcs {

    public static final String QUEST_ID = "q_mooring_arcs";

    private MooringArcs() { }

    /** Motzkin number: non-crossing layouts on n posts, free posts allowed (n up to 2000). */
    public static BigInteger motzkin(int n) {
        if (n < 0 || n > 2000) {
            throw new IllegalArgumentException("n " + n);
        }
        BigInteger[] m = new BigInteger[n + 1];
        m[0] = BigInteger.ONE;
        for (int i = 1; i <= n; i++) {
            BigInteger v = m[i - 1];
            for (int k = 0; k <= i - 2; k++) {
                v = v.add(m[k].multiply(m[i - 2 - k]));
            }
            m[i] = v;
        }
        return m[n];
    }

    private static BigInteger binom(int n, int k) {
        BigInteger r = BigInteger.ONE;
        for (int i = 0; i < k; i++) {
            r = r.multiply(BigInteger.valueOf(n - i)).divide(BigInteger.valueOf(i + 1));
        }
        return r;
    }

    /** Narayana number: full layouts of 2n posts with exactly k lines between neighbouring posts. */
    public static BigInteger narayana(int n, int k) {
        if (n < 1 || n > 2000) {
            throw new IllegalArgumentException("n " + n);
        }
        if (k < 1 || k > n) {
            return BigInteger.ZERO;
        }
        return binom(n, k).multiply(binom(n, k - 1)).divide(BigInteger.valueOf(n));
    }

    /**
     * True when partner[i] is -1 (free) or the post line i is tied to, partners agree, and no two
     * lines cross.
     */
    public static boolean isLayout(int[] partner) {
        int n = partner.length;
        for (int i = 0; i < n; i++) {
            int p = partner[i];
            if (p == -1) {
                continue;
            }
            if (p < 0 || p >= n || p == i || partner[p] != i) {
                return false;
            }
        }
        for (int a = 0; a < n; a++) {
            int b = partner[a];
            if (b <= a) {
                continue;
            }
            for (int c = a + 1; c < b; c++) {
                int d = partner[c];
                if (d != -1 && (d < a || d > b)) {
                    return false;
                }
            }
        }
        return true;
    }

    /** Quest q_mooring_arcs: count the layouts on n posts with free posts allowed. */
    public static boolean quest(int n, BigInteger answer) {
        return motzkin(n).equals(answer);
    }
}