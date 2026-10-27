// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G359 The Hull Signs: the shipwright marks an n x n grid of hull plates +1 or -1 so that any two
 * rows agree on exactly half their plates (a Hadamard matrix, H times H-transpose equals n I).
 * Sylvester doubling gives every power of two, the Paley construction gives p + 1 for primes
 * p = 3 mod 4, and doubling a Paley grid covers more orders.
 */
public final class HullSigns {

    public static final String QUEST_ID = "q_hull_signs";

    private HullSigns() { }

    /** True when every entry is +1 or -1 and distinct rows are orthogonal. */
    public static boolean isHadamard(int[][] h) {
        int n = h.length;
        if (n == 0) {
            return false;
        }
        for (int[] row : h) {
            if (row.length != n) {
                return false;
            }
            for (int v : row) {
                if (v != 1 && v != -1) {
                    return false;
                }
            }
        }
        for (int a = 0; a < n; a++) {
            for (int b = a + 1; b < n; b++) {
                int dot = 0;
                for (int j = 0; j < n; j++) {
                    dot += h[a][j] * h[b][j];
                }
                if (dot != 0) {
                    return false;
                }
            }
        }
        return true;
    }

    private static int[][] doubled(int[][] h) {
        int n = h.length;
        int[][] out = new int[2 * n][2 * n];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                out[i][j] = h[i][j];
                out[i][j + n] = h[i][j];
                out[i + n][j] = h[i][j];
                out[i + n][j + n] = -h[i][j];
            }
        }
        return out;
    }

    private static boolean isPrime(int p) {
        if (p < 2) {
            return false;
        }
        for (int d = 2; d * d <= p; d++) {
            if (p % d == 0) {
                return false;
            }
        }
        return true;
    }

    /** Paley grid of order p + 1 for a prime p = 3 mod 4. */
    public static int[][] paley(int p) {
        if (p > 1000 || !isPrime(p) || p % 4 != 3) {
            throw new IllegalArgumentException("p must be a prime 3 mod 4 up to 1000: " + p);
        }
        int[] chi = new int[p];
        for (int x = 1; x < p; x++) {
            chi[(int) ((long) x * x % p)] = 1;
        }
        int n = p + 1;
        int[][] h = new int[n][n];
        for (int j = 0; j < n; j++) {
            h[0][j] = 1;
        }
        for (int i = 1; i < n; i++) {
            h[i][0] = -1;
            for (int j = 1; j < n; j++) {
                int diff = ((j - i) % p + p) % p;
                int q = diff == 0 ? 0 : (chi[diff] == 1 ? 1 : -1);
                h[i][j] = q + (i == j ? 1 : 0);
            }
        }
        return h;
    }

    /** A Hadamard grid of order n (up to 512) from Sylvester and Paley, or an empty array. */
    public static int[][] build(int n) {
        if (n < 1 || n > 512) {
            throw new IllegalArgumentException("n 1..512");
        }
        int m = n;
        int doublings = 0;
        int[][] base = new int[0][];
        while (true) {
            if (m == 1) {
                base = new int[][] {{1}};
                break;
            }
            if (m % 4 == 0 && m - 1 <= 1000 && isPrime(m - 1)) {
                base = paley(m - 1);
                break;
            }
            if (m % 2 != 0) {
                break;
            }
            m /= 2;
            doublings++;
        }
        if (base.length == 0) {
            return base;
        }
        int[][] h = base;
        for (int i = 0; i < doublings; i++) {
            h = doubled(h);
        }
        return h;
    }

    /** Quest q_hull_signs: hand in a valid hull-sign grid of order n. */
    public static boolean quest(int n, int[][] answer) {
        return answer.length == n && isHadamard(answer);
    }
}