// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;
import java.util.Arrays;

/**
 * Carmichael Cycle: a forge wheel with n notches, stepped multiplicatively, returns to start after lambda(n) turns
 * at most (the Carmichael function). The smith names lambda(n), the order of a step, and spots impostor wheels:
 * Carmichael numbers, which satisfy Fermat's test for every coprime base.
 *
 * <p>Reusable plain long API: {@link #lambda}, {@link #order}, {@link #isCarmichael}.
 */
public final class CarmichaelCycle {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_carmichael_cycle";

    /** Largest supported wheel. */
    public static final long MAX_N = 1_000_000_000_000L;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private CarmichaelCycle() {
    }

    /** Carmichael function lambda(n). */
    public static long lambda(long n) {
        check(n);
        long result = 1;
        long x = n;
        for (long p : factor(n)) {
            int k = 0;
            long pk = 1;
            while (x % p == 0) {
                x /= p;
                pk *= p;
                k++;
            }
            long l;
            if (p == 2) {
                l = k == 1 ? 1 : k == 2 ? 2 : pk / 4;
            } else {
                l = pk / p * (p - 1);
            }
            result = result / gcd(result, l) * l;
        }
        return result;
    }

    /** Multiplicative order of a modulo n (a coprime to n). */
    public static long order(long a, long n) {
        check(n);
        long b = Math.floorMod(a, n);
        if (gcd(b, n) != 1) {
            throw new IllegalArgumentException("a must be coprime to n");
        }
        long l = lambda(n);
        for (long r : factor(l)) {
            while (l % r == 0 && pow(b, l / r, n) == 1 % n) {
                l /= r;
            }
        }
        return l;
    }

    /** Korselt: n composite, squarefree, and p-1 divides n-1 for every prime p dividing n. */
    public static boolean isCarmichael(long n) {
        check(n);
        if (n < 3 || (n & 1L) == 0L) {
            return false;
        }
        long[] pf = factor(n);
        if (pf.length < 2) {
            return false;
        }
        for (long p : pf) {
            if ((n / p) % p == 0 || (n - 1) % (p - 1) != 0) {
                return false;
            }
        }
        return true;
    }

    /** TURNED when the claimed cycle length equals lambda(n). */
    public static Grade grade(long n, long claimed) {
        return lambda(n) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: every step comes home by that turn and no sooner for all of them. True cycle.";
            case SLIPPED -> "Forgemaster: the wheel slipped. Take the lcm over each prime power, not the product.";
        };
    }

    static long pow(long base, long e, long m) {
        if (m <= Integer.MAX_VALUE) {
            long r = 1 % m;
            long b = Math.floorMod(base, m);
            long x = e;
            while (x > 0) {
                if ((x & 1L) == 1L) {
                    r = r * b % m;
                }
                b = b * b % m;
                x >>= 1;
            }
            return r;
        }
        return BigInteger.valueOf(base).modPow(BigInteger.valueOf(e), BigInteger.valueOf(m)).longValue();
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
        return Arrays.copyOf(buf, k);
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

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
    }
}
