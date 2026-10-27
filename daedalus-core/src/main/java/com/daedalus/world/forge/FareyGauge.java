// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Farey Gauge: the gaugewright lists every reduced ratio p/q in [0, 1] with q at most n, in order
 * (the Farey sequence F_n), counts it, ranks a ratio inside it and checks neighbours.
 *
 * <p>Reusable plain int/long API: {@link #sequence}, {@link #count}, {@link #rank}, {@link #neighbours}.
 */
public final class FareyGauge {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_farey_gauge";

    /** Largest order for which the full sequence is listed. */
    public static final int MAX_SEQ_N = 2000;

    /** Largest order for counting and ranking. */
    public static final int MAX_N = 10_000_000;

    /** Grade band. */
    public enum Grade { TRUE, BENT }

    private FareyGauge() {
    }

    /** Seeded gauge order in [1, 60]. */
    public static int gauge(long seed) {
        return 1 + new SplittableRandom(seed).nextInt(60);
    }

    /** F_n as rows {p, q} in increasing order, from 0/1 to 1/1. */
    public static int[][] sequence(int n) {
        if (n < 1 || n > MAX_SEQ_N) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        int[][] out = new int[(int) count(n)][];
        int a = 0;
        int b = 1;
        int c = 1;
        int d = n;
        int i = 0;
        out[i++] = new int[] {a, b};
        while (c <= n) {
            out[i++] = new int[] {c, d};
            int k = (n + b) / d;
            int e = k * c - a;
            int f = k * d - b;
            a = c;
            b = d;
            c = e;
            d = f;
            if (a == 1 && b == 1) {
                break;
            }
        }
        return out;
    }

    /** |F_n| = 1 + sum of Euler phi(1..n). */
    public static long count(int n) {
        check(n);
        int[] phi = new int[n + 1];
        for (int i = 0; i <= n; i++) {
            phi[i] = i;
        }
        long total = 1;
        for (int i = 1; i <= n; i++) {
            if (i > 1 && phi[i] == i) {
                for (int j = i; j <= n; j += i) {
                    phi[j] -= phi[j] / i;
                }
            }
            total += phi[i];
        }
        return total;
    }

    /** Number of terms of F_n that are at most a/b (so 0/1 has rank 1); requires 0 &lt;= a &lt;= b. */
    public static long rank(long a, long b, int n) {
        check(n);
        if (b < 1 || a < 0 || a > b) {
            throw new IllegalArgumentException("ratio out of range");
        }
        long[] f = new long[n + 1];
        long total = 1;
        for (int q = 1; q <= n; q++) {
            f[q] += a * q / b;
            total += f[q];
            for (int m = 2 * q; m <= n; m += q) {
                f[m] -= f[q];
            }
        }
        return total;
    }

    /** True when a/b and c/d are Farey neighbours (b*c - a*d == 1). */
    public static boolean neighbours(long a, long b, long c, long d) {
        return b * c - a * d == 1;
    }

    /** TRUE when the claimed size of F_n is exact. */
    public static Grade grade(int n, long claimed) {
        return claimed == count(n) ? Grade.TRUE : Grade.BENT;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TRUE -> "Forgemaster: every ratio in its notch, none missing, none doubled. A true gauge.";
            case BENT -> "Forgemaster: that gauge is bent. Count the notches again, smallest step first.";
        };
    }

    private static void check(int n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
    }
}
