// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Triad Alloys: alloy n is a triad when it is the product of exactly three distinct prime ores (a sphenic number:
 * 30 = 2 x 3 x 5, 42, 66, 70, ...).
 *
 * <p>Reusable plain long API: {@link #ores} and {@link #isSphenic} for 1 &lt;= n &lt;= {@link #MAX_N},
 * {@link #countSphenic} by smallest-prime-factor sieve and {@link #firstRun} for limits up to {@link #MAX_SIEVE}.
 */
public final class TriadAlloys {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_triad_alloys";
    /** Largest supported alloy. */
    public static final long MAX_N = 1_000_000_000_000L;
    /** Largest supported sieve limit. */
    public static final int MAX_SIEVE = 10_000_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private TriadAlloys() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("alloy out of range: " + n);
        }
    }

    /** The ores {p, q, r} with p &lt; q &lt; r and pqr = n, or an empty array when n is no triad. */
    public static long[] ores(long n) {
        check(n);
        long[] f = new long[3];
        int k = 0;
        long m = n;
        for (long p = 2; p * p <= m; p++) {
            if (m % p == 0) {
                m /= p;
                if (m % p == 0 || k == 3) {
                    return new long[0];
                }
                f[k++] = p;
            }
        }
        if (m > 1) {
            if (k == 3) {
                return new long[0];
            }
            f[k++] = m;
        }
        return k == 3 ? f : new long[0];
    }

    /** True when n is the product of three distinct primes. */
    public static boolean isSphenic(long n) {
        return ores(n).length == 3;
    }

    private static boolean[] sieve(int limit) {
        if (limit < 0 || limit > MAX_SIEVE) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        int[] spf = new int[limit + 1];
        boolean[] tri = new boolean[limit + 1];
        int[] omega = new int[limit + 1];
        boolean[] sqf = new boolean[limit + 1];
        if (limit >= 1) {
            sqf[1] = true;
        }
        for (int i = 2; i <= limit; i++) {
            if (spf[i] == 0) {
                for (long j = i; j <= limit; j += i) {
                    if (spf[(int) j] == 0) {
                        spf[(int) j] = i;
                    }
                }
            }
            int p = spf[i];
            int q = i / p;
            sqf[i] = sqf[q] && q % p != 0;
            omega[i] = omega[q] + 1;
            tri[i] = sqf[i] && omega[i] == 3;
        }
        return tri;
    }

    /** Number of triads in 1..limit. */
    public static long countSphenic(int limit) {
        boolean[] t = sieve(limit);
        long c = 0;
        for (boolean b : t) {
            if (b) {
                c++;
            }
        }
        return c;
    }

    /** Smallest start of k consecutive triads ending at or below limit, or -1 if none. */
    public static long firstRun(int k, int limit) {
        if (k < 1) {
            throw new IllegalArgumentException("run length must be positive: " + k);
        }
        boolean[] t = sieve(limit);
        int run = 0;
        for (int i = 1; i <= limit; i++) {
            run = t[i] ? run + 1 : 0;
            if (run == k) {
                return i - k + 1L;
            }
        }
        return -1;
    }

    /** Grade a claim that alloy n is (or is not) a triad. */
    public static Grade grade(long n, boolean claimedTriad) {
        return isSphenic(n) == claimedTriad ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: three ores, each once, no more. You read the alloy true.";
            case SLIPPED -> "Forgemaster: the alloy slipped. Exactly three primes, and none of them twice.";
        };
    }
}
