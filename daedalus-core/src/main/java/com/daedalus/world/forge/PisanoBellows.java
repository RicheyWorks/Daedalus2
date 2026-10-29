// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Pisano Bellows: the bellows pump in a Fibonacci rhythm modulo m. The smith names the beat F(n) mod m
 * for huge n and the Pisano period pi(m), after which the rhythm repeats.
 *
 * <p>Reusable plain long API: {@link #fibMod}, {@link #period}.
 */
public final class PisanoBellows {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_pisano_bellows";

    /** Largest supported modulus (keeps products inside a long). */
    public static final long MAX_M = Integer.MAX_VALUE;

    /** Grade band. */
    public enum Grade { TRUE, OFFBEAT }

    private PisanoBellows() {
    }

    /** Seeded modulus in [2, 10^9]. */
    public static long bellows(long seed) {
        return 2 + new SplittableRandom(seed).nextLong(999_999_999L);
    }

    /** F(n) mod m by fast doubling. */
    public static long fibMod(long n, long m) {
        return pair(n, m)[0];
    }

    /** Pisano period of m (pi(1) = 1). */
    public static long period(long m) {
        check(m);
        if (m == 1) {
            return 1;
        }
        long[] pf = factor(m);
        long cand = 1;
        long x = m;
        for (long p : pf) {
            long pk = 1;
            while (x % p == 0) {
                x /= p;
                pk *= p;
            }
            long base;
            if (p == 2) {
                base = 3;
            } else if (p == 5) {
                base = 20;
            } else if (p % 5 == 1 || p % 5 == 4) {
                base = p - 1;
            } else {
                base = 2 * (p + 1);
            }
            long t = base * (pk / p);
            cand = cand / gcd(cand, t) * t;
        }
        for (long r : factor(cand)) {
            while (cand % r == 0 && isPeriod(cand / r, m)) {
                cand /= r;
            }
        }
        return cand;
    }

    /** True when t is a period of the Fibonacci sequence mod m. */
    public static boolean isPeriod(long t, long m) {
        long[] q = pair(t, m);
        return q[0] == 0 && q[1] == 1 % m;
    }

    /** TRUE when the claimed period is exact. */
    public static Grade grade(long m, long claimed) {
        return claimed == period(m) ? Grade.TRUE : Grade.OFFBEAT;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TRUE -> "Forgemaster: you called the turn of the rhythm to the very beat. The bellows sing.";
            case OFFBEAT -> "Forgemaster: offbeat. Listen for zero then one again before you call it.";
        };
    }

    private static long[] pair(long n, long m) {
        check(m);
        if (n < 0) {
            throw new IllegalArgumentException("n must be non-negative");
        }
        long a = 0;
        long b = 1 % m;
        for (int bit = 63 - Long.numberOfLeadingZeros(n); bit >= 0; bit--) {
            long c = a * Math.floorMod(2 * b - a, m) % m;
            long d = (a * a % m + b * b % m) % m;
            if (((n >>> bit) & 1L) == 1L) {
                a = d;
                b = (c + d) % m;
            } else {
                a = c;
                b = d;
            }
        }
        return new long[] {a, b};
    }

    private static long[] factor(long n) {
        long[] buf = new long[64];
        int k = 0;
        long x = n;
        for (long p = 2; p * p <= x; p++) {
            if (x % p == 0) {
                buf[k++] = p;
                while (x % p == 0) {
                    x /= p;
                }
            }
        }
        if (x > 1) {
            buf[k++] = x;
        }
        long[] out = new long[k];
        System.arraycopy(buf, 0, out, 0, k);
        return out;
    }

    private static long gcd(long x, long y) {
        long p = x;
        long q = y;
        while (q != 0) {
            long t = p % q;
            p = q;
            q = t;
        }
        return p;
    }

    private static void check(long m) {
        if (m < 1 || m > MAX_M) {
            throw new IllegalArgumentException("m out of range: " + m);
        }
    }
}
