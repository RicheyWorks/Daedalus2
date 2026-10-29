// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Pernicious Pins: pin n is pernicious when the number of set bits in its binary form is prime (3 = 11b, 5, 6, 7, 9,
 * ...).
 *
 * <p>Reusable plain long API for 0 &lt;= n &lt;= {@link #MAX_N}: {@link #isPernicious}, {@link #countPernicious}
 * (binomial count bit by bit) and {@link #nthPernicious} (binary search on the count).
 */
public final class PerniciousPins {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_pernicious_pins";
    /** Largest supported pin. */
    public static final long MAX_N = 1_000_000_000_000_000_000L;

    private static final long[][] BINOM = new long[64][64];

    static {
        for (int i = 0; i < 64; i++) {
            BINOM[i][0] = 1;
            for (int j = 1; j <= i; j++) {
                BINOM[i][j] = BINOM[i - 1][j - 1] + (j <= i - 1 ? BINOM[i - 1][j] : 0);
            }
        }
    }

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private PerniciousPins() {
    }

    private static void check(long n) {
        if (n < 0 || n > MAX_N) {
            throw new IllegalArgumentException("pin out of range: " + n);
        }
    }

    private static boolean smallPrime(int k) {
        if (k < 2) {
            return false;
        }
        for (int d = 2; d * d <= k; d++) {
            if (k % d == 0) {
                return false;
            }
        }
        return true;
    }

    /** True when the popcount of n is prime. */
    public static boolean isPernicious(long n) {
        check(n);
        return smallPrime(Long.bitCount(n));
    }

    /** Number of pernicious pins in 0..N. */
    public static long countPernicious(long bigN) {
        check(bigN);
        long c = 0;
        int ones = 0;
        for (int i = 62; i >= 0; i--) {
            if ((bigN & (1L << i)) != 0) {
                for (int k = ones; k <= ones + i; k++) {
                    if (smallPrime(k)) {
                        c += BINOM[i][k - ones];
                    }
                }
                ones++;
            }
        }
        return smallPrime(ones) ? c + 1 : c;
    }

    /** The k-th pernicious pin, k &gt;= 1 (the first is 3). */
    public static long nthPernicious(long k) {
        if (k < 1 || k > countPernicious(MAX_N)) {
            throw new IllegalArgumentException("rank out of range: " + k);
        }
        long lo = 0;
        long hi = MAX_N;
        while (lo < hi) {
            long mid = lo + (hi - lo) / 2;
            if (countPernicious(mid) >= k) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        return lo;
    }

    /** Grade a claim that pin n is (or is not) pernicious. */
    public static Grade grade(long n, boolean claimedPernicious) {
        return isPernicious(n) == claimedPernicious ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: you counted the lit bits and named their prime. True work.";
            case SLIPPED -> "Forgemaster: the pin slipped. Count the ones in its binary, then test that count.";
        };
    }
}
