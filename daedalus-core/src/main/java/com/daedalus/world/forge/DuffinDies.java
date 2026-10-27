// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Duffin Dies: die n is a Duffin die when it is composite yet shares no factor with sigma(n), the sum of all its
 * divisors (a Duffinian number: 4, 8, 9, 16, 21, 25, ...).
 *
 * <p>Reusable plain long API: {@link #sigma} and {@link #isDuffinian} for 1 &lt;= n &lt;= {@link #MAX_N},
 * {@link #countDuffinian} and {@link #firstRun} by divisor-sum sieve for limits up to {@link #MAX_SIEVE}.
 */
public final class DuffinDies {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_duffin_dies";
    /** Largest supported die. */
    public static final long MAX_N = 1_000_000_000_000L;
    /** Largest supported sieve limit. */
    public static final int MAX_SIEVE = 10_000_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private DuffinDies() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("die out of range: " + n);
        }
    }

    private static long gcd(long a, long b) {
        long x = a;
        long y = b;
        while (y != 0) {
            long t = x % y;
            x = y;
            y = t;
        }
        return x;
    }

    /** Sum of all divisors of n. */
    public static long sigma(long n) {
        check(n);
        long m = n;
        long s = 1;
        for (long p = 2; p * p <= m; p++) {
            if (m % p == 0) {
                long term = 1;
                long pk = 1;
                while (m % p == 0) {
                    m /= p;
                    pk *= p;
                    term += pk;
                }
                s *= term;
            }
        }
        return m > 1 ? s * (m + 1) : s;
    }

    /** True when n is composite and gcd(n, sigma(n)) = 1. */
    public static boolean isDuffinian(long n) {
        long s = sigma(n);
        return n > 1 && s != n + 1 && gcd(n, s) == 1;
    }

    private static boolean[] sieve(int limit) {
        if (limit < 0 || limit > MAX_SIEVE) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        long[] sig = new long[limit + 1];
        for (int d = 1; d <= limit; d++) {
            for (int k = d; k <= limit; k += d) {
                sig[k] += d;
            }
        }
        boolean[] duf = new boolean[limit + 1];
        for (int n = 2; n <= limit; n++) {
            duf[n] = sig[n] != n + 1L && gcd(n, sig[n]) == 1;
        }
        return duf;
    }

    /** Number of Duffin dies in 1..limit. */
    public static long countDuffinian(int limit) {
        long c = 0;
        for (boolean b : sieve(limit)) {
            if (b) {
                c++;
            }
        }
        return c;
    }

    /** Smallest start of k consecutive Duffin dies ending at or below limit, or -1 if none. */
    public static long firstRun(int k, int limit) {
        if (k < 1) {
            throw new IllegalArgumentException("run length must be positive: " + k);
        }
        boolean[] d = sieve(limit);
        int run = 0;
        for (int i = 1; i <= limit; i++) {
            run = d[i] ? run + 1 : 0;
            if (run == k) {
                return i - k + 1L;
            }
        }
        return -1;
    }

    /** Grade a claim that die n is (or is not) a Duffin die. */
    public static Grade grade(long n, boolean claimedDuffin) {
        return isDuffinian(n) == claimedDuffin ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: a composite die that shares nothing with its divisor sum. Read true.";
            case SLIPPED -> "Forgemaster: the die slipped. Primes are no Duffin dies; check gcd with the sum.";
        };
    }
}
