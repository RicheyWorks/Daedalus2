// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;

/**
 * Root Quench: quench tanks cycle modulo a prime p; the smith finds t with t*t = a (mod p) or shows none exists.
 * The Jacobi symbol (a/n) screens candidates for any odd n without factoring.
 *
 * <p>Reusable plain long API: {@link #jacobi}, {@link #isResidue}, {@link #sqrtMod}.
 */
public final class RootQuench {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_root_quench";

    /** Grade band. */
    public enum Grade { QUENCHED, CRACKED }

    private RootQuench() {
    }

    /** Jacobi symbol (a/n) for odd n &gt;= 1: -1, 0 or 1. */
    public static int jacobi(long a, long n) {
        if (n < 1 || (n & 1L) == 0L) {
            throw new IllegalArgumentException("n must be odd and positive");
        }
        long x = Math.floorMod(a, n);
        long m = n;
        int result = 1;
        while (x != 0) {
            while ((x & 1L) == 0L) {
                x >>= 1;
                long r = m & 7L;
                if (r == 3 || r == 5) {
                    result = -result;
                }
            }
            long t = x;
            x = m;
            m = t;
            if ((x & 3L) == 3L && (m & 3L) == 3L) {
                result = -result;
            }
            x %= m;
        }
        return m == 1 ? result : 0;
    }

    /** True when a is a square modulo the prime p (0 counts as a square). */
    public static boolean isResidue(long a, long p) {
        return sqrtMod(a, p) >= 0;
    }

    /** Smallest t in [0, p) with t*t = a (mod p) for prime p, or -1 when none exists. */
    public static long sqrtMod(long a, long p) {
        if (p < 2) {
            throw new IllegalArgumentException("p must be prime");
        }
        long x = Math.floorMod(a, p);
        if (x == 0 || p == 2) {
            return x;
        }
        if (jacobi(x, p) != 1) {
            return -1;
        }
        long q = p - 1;
        int s = 0;
        while ((q & 1L) == 0L) {
            q >>= 1;
            s++;
        }
        long z = 2;
        while (jacobi(z, p) != -1) {
            z++;
        }
        int m = s;
        long c = pow(z, q, p);
        long t = pow(x, q, p);
        long r = pow(x, (q + 1) / 2, p);
        while (t != 1) {
            int i = 0;
            long tt = t;
            while (tt != 1) {
                tt = mul(tt, tt, p);
                i++;
                if (i >= m) {
                    throw new IllegalArgumentException("p is not prime");
                }
            }
            long b = c;
            for (int k = 0; k < m - i - 1; k++) {
                b = mul(b, b, p);
            }
            m = i;
            c = mul(b, b, p);
            t = mul(t, c, p);
            r = mul(r, b, p);
        }
        if (mul(r, r, p) != x) {
            throw new IllegalArgumentException("p is not prime");
        }
        return Math.min(r, p - r);
    }

    /** QUENCHED when claimed squares to a mod p (or claimed is -1 and no root exists). */
    public static Grade grade(long a, long p, long claimed) {
        long want = sqrtMod(a, p);
        boolean ok = want < 0 ? claimed == -1
            : claimed >= 0 && claimed < p && mul(claimed, claimed, p) == Math.floorMod(a, p);
        return ok ? Grade.QUENCHED : Grade.CRACKED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case QUENCHED -> "Forgemaster: the root rings true in the tank; square it and the cycle closes.";
            case CRACKED -> "Forgemaster: cracked. Check the symbol first; some tanks have no root at all.";
        };
    }

    private static long mul(long a, long b, long m) {
        if (m <= Integer.MAX_VALUE) {
            return a * b % m;
        }
        return BigInteger.valueOf(a).multiply(BigInteger.valueOf(b)).mod(BigInteger.valueOf(m)).longValue();
    }

    private static long pow(long base, long e, long m) {
        long r = 1 % m;
        long b = Math.floorMod(base, m);
        long x = e;
        while (x > 0) {
            if ((x & 1L) == 1L) {
                r = mul(r, b, m);
            }
            b = mul(b, b, m);
            x >>= 1;
        }
        return r;
    }
}
