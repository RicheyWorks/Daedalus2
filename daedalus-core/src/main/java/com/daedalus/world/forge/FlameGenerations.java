// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Flame Generations (contest gap G341): each generation of forge flame is a weighted mix of the last k generations.
 * Name generation n, for n up to 10^18, modulo a prime.
 *
 * <p>The tool is plain: {@link #nthTerm} raises the k-by-k companion matrix to a power by squaring (O(k^3 log n)) for
 * the recurrence {@code a[n] = c[0] a[n-1] + ... + c[k-1] a[n-k] (mod m)}. The modulus must be below
 * {@link #MAX_MOD} so products fit in a {@code long}. Any project can use it for fast linear recurrences.
 */
public final class FlameGenerations {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_flame_generations";

    /** Largest modulus accepted (exclusive). */
    public static final long MAX_MOD = 1L << 31;

    /** Default prime modulus. */
    public static final long PRIME = 1_000_000_007L;

    /** How a prophecy went. */
    public enum Grade { FORETOLD, GUESSED }

    private FlameGenerations() {
    }

    /** {@code k} seeded values in [0, m). */
    public static long[] seeded(long seed, int k, long m) {
        if (k < 1 || m < 2 || m >= MAX_MOD) {
            throw new IllegalArgumentException("need k >= 1 and 2 <= m < 2^31");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[] v = new long[k];
        for (int i = 0; i < k; i++) {
            v[i] = r.nextLong(m);
        }
        return v;
    }

    /** Matrix product mod m. */
    public static long[][] matMul(long[][] a, long[][] b, long m) {
        int n = a.length;
        int p = b[0].length;
        int q = b.length;
        long[][] c = new long[n][p];
        for (int i = 0; i < n; i++) {
            for (int t = 0; t < q; t++) {
                long x = a[i][t];
                if (x == 0) {
                    continue;
                }
                for (int j = 0; j < p; j++) {
                    c[i][j] = (c[i][j] + x * b[t][j]) % m;
                }
            }
        }
        return c;
    }

    /** Square matrix to the power e mod m. */
    public static long[][] matPow(long[][] a, long e, long m) {
        if (e < 0) {
            throw new IllegalArgumentException("exponent must be non-negative");
        }
        int n = a.length;
        long[][] r = new long[n][n];
        for (int i = 0; i < n; i++) {
            r[i][i] = 1 % m;
        }
        long[][] b = a;
        long left = e;
        while (left > 0) {
            if ((left & 1) == 1) {
                r = matMul(r, b, m);
            }
            b = matMul(b, b, m);
            left >>= 1;
        }
        return r;
    }

    /** a[n] for coefficients c and first terms init (both length k), mod m. */
    public static long nthTerm(long[] c, long[] init, long n, long m) {
        int k = c.length;
        if (k < 1 || init.length != k || n < 0 || m < 2 || m >= MAX_MOD) {
            throw new IllegalArgumentException("need matching non-empty c/init, n >= 0, 2 <= m < 2^31");
        }
        if (n < k) {
            return Math.floorMod(init[(int) n], m);
        }
        long[][] t = new long[k][k];
        for (int j = 0; j < k; j++) {
            t[0][j] = Math.floorMod(c[j], m);
        }
        for (int i = 1; i < k; i++) {
            t[i][i - 1] = 1;
        }
        long[][] p = matPow(t, n - k + 1, m);
        long s = 0;
        for (int j = 0; j < k; j++) {
            s = (s + p[0][j] * Math.floorMod(init[k - 1 - j], m)) % m;
        }
        return s;
    }

    /** FORETOLD only if the claimed term is right. */
    public static Grade grade(long[] c, long[] init, long n, long m, long claimed) {
        return nthTerm(c, init, n, m) == claimed ? Grade.FORETOLD : Grade.GUESSED;
    }

    /** The Forgemaster's line for a prophecy. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case FORETOLD -> "Forgemaster: you saw a flame not yet lit, a billion generations hence. Uncanny.";
            case GUESSED -> "Forgemaster: that flame never burns. Count the generations properly.";
        };
    }
}
