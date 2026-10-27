// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;

/**
 * Hammer Cadence: two smiths share hammer blows fairly by the Thue-Morse sequence, where blow n goes to
 * smith t(n) = parity of the set bits of n. Splitting 0..2^k-1 by t gives two crews whose power sums agree
 * up to degree k-1 (Prouhet).
 *
 * <p>Reusable plain long API: {@link #striker}, {@link #countOnes}, {@link #prefix}, {@link #prouhet},
 * {@link #powerSumsAgree}.
 */
public final class HammerCadence {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_hammer_cadence";

    /** Largest prefix length listed. */
    public static final int MAX_PREFIX = 1 << 24;

    /** Largest Prouhet order. */
    public static final int MAX_K = 20;

    /** Grade band. */
    public enum Grade { FAIR, LOPSIDED }

    private HammerCadence() {
    }

    /** Smith (0 or 1) who strikes blow n. */
    public static int striker(long n) {
        if (n < 0) {
            throw new IllegalArgumentException("n must be non-negative");
        }
        return Long.bitCount(n) & 1;
    }

    /** Number of blows in [0, n) struck by smith 1. */
    public static long countOnes(long n) {
        if (n < 0) {
            throw new IllegalArgumentException("n must be non-negative");
        }
        if ((n & 1L) == 0L) {
            return n / 2;
        }
        return (n - 1) / 2 + striker(n - 1);
    }

    /** First len terms by the doubling construction (t, then t complemented). */
    public static int[] prefix(int len) {
        if (len < 0 || len > MAX_PREFIX) {
            throw new IllegalArgumentException("len out of range: " + len);
        }
        int[] t = new int[len];
        for (int size = 1; size < len; size *= 2) {
            for (int i = size; i < Math.min(2 * size, len); i++) {
                t[i] = 1 - t[i - size];
            }
        }
        return t;
    }

    /** Crews {t=0 members, t=1 members} of 0..2^k-1. */
    public static long[][] prouhet(int k) {
        if (k < 1 || k > MAX_K) {
            throw new IllegalArgumentException("k out of range: " + k);
        }
        int half = 1 << (k - 1);
        long[] a = new long[half];
        long[] b = new long[half];
        int ia = 0;
        int ib = 0;
        for (long n = 0; n < (1L << k); n++) {
            if (striker(n) == 0) {
                a[ia++] = n;
            } else {
                b[ib++] = n;
            }
        }
        return new long[][] {a, b};
    }

    /** True when sum of x^d over a equals that over b for every d in 0..deg. */
    public static boolean powerSumsAgree(long[] a, long[] b, int deg) {
        for (int d = 0; d <= deg; d++) {
            if (!powerSum(a, d).equals(powerSum(b, d))) {
                return false;
            }
        }
        return true;
    }

    /** FAIR when the crews' power sums agree up to degree deg. */
    public static Grade grade(long[] a, long[] b, int deg) {
        return powerSumsAgree(a, b, deg) ? Grade.FAIR : Grade.LOPSIDED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case FAIR -> "Forgemaster: blow for blow, power for power, neither crew carries the other. Fair work.";
            case LOPSIDED -> "Forgemaster: lopsided. One crew is swinging heavier; split the blows again.";
        };
    }

    private static BigInteger powerSum(long[] xs, int d) {
        BigInteger s = BigInteger.ZERO;
        for (long x : xs) {
            s = s.add(BigInteger.valueOf(x).pow(d));
        }
        return s;
    }
}
