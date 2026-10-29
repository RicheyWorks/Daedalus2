// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;

/**
 * Totient Tempers: tempering blade n runs the totient chain n -&gt; phi(n) -&gt; ... -&gt; 1. The blade is perfectly
 * tempered when the chain after n sums back to n: the perfect totient numbers 3, 9, 15, 27, 39, 81, ...
 *
 * <p>Reusable plain long API for 1 &lt;= n &lt;= {@link #MAX_N}: {@link #phi}, {@link #chain}, {@link #chainSum},
 * {@link #isPerfectTemper} and the sieve {@link #tempersUpTo} for x up to {@link #SIEVE_MAX}.
 */
public final class TotientTempers {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_totient_tempers";
    /** Largest supported blade. */
    public static final long MAX_N = 1_000_000_000_000L;
    /** Largest sieve bound. */
    public static final int SIEVE_MAX = 2_000_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private TotientTempers() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("blade out of range: " + n);
        }
    }

    /** Euler's totient by trial factoring. */
    public static long phi(long n) {
        check(n);
        long m = n;
        long r = n;
        for (long p = 2; p * p <= m; p++) {
            if (m % p == 0) {
                while (m % p == 0) {
                    m /= p;
                }
                r -= r / p;
            }
        }
        if (m > 1) {
            r -= r / m;
        }
        return r;
    }

    /** phi(n), phi(phi(n)), ..., 1 (empty for n = 1). */
    public static List<Long> chain(long n) {
        check(n);
        List<Long> out = new ArrayList<>();
        long v = n;
        while (v > 1) {
            v = phi(v);
            out.add(v);
        }
        return out;
    }

    /** Sum of {@link #chain}. */
    public static long chainSum(long n) {
        long s = 0;
        for (long v : chain(n)) {
            s += v;
        }
        return s;
    }

    /** True when the chain after n sums to n. */
    public static boolean isPerfectTemper(long n) {
        return chainSum(n) == n;
    }

    /** Perfect tempers in 1..x, by totient sieve. */
    public static List<Long> tempersUpTo(int x) {
        if (x < 0 || x > SIEVE_MAX) {
            throw new IllegalArgumentException("bound out of range: " + x);
        }
        int[] ph = new int[x + 1];
        for (int i = 0; i <= x; i++) {
            ph[i] = i;
        }
        for (int p = 2; p <= x; p++) {
            if (ph[p] == p) {
                for (int j = p; j <= x; j += p) {
                    ph[j] -= ph[j] / p;
                }
            }
        }
        long[] sum = new long[x + 1];
        List<Long> out = new ArrayList<>();
        for (int n = 2; n <= x; n++) {
            sum[n] = ph[n] + sum[ph[n]];
            if (sum[n] == n) {
                out.add((long) n);
            }
        }
        return out;
    }

    /** Grade a claim that n is (or is not) perfectly tempered. */
    public static Grade grade(long n, boolean claimedPerfect) {
        return isPerfectTemper(n) == claimedPerfect ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the temper reads true. Every quench sums back to the blade.";
            case SLIPPED -> "Forgemaster: the temper slipped. Follow phi all the way down to one.";
        };
    }
}
