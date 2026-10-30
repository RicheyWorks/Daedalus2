// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;

/**
 * Primorial Pyres: the pyre of n burns n#, the product of all primes up to n. Its Euclid flame n# + 1 and Kummer
 * flame n# - 1 may themselves be prime (2# + 1 = 3, 30 + 1 = 31, but 13# + 1 = 30031 = 59 x 509).
 *
 * <p>Reusable plain long API: {@link #primorial} for 0 &lt;= n &lt;= {@link #MAX_N}, {@link #isPrime} for any
 * long (deterministic Miller-Rabin over the first twelve prime bases), {@link #euclidFlames} and
 * {@link #kummerFlames}.
 */
public final class PrimorialPyres {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_primorial_pyres";
    /** Largest supported pyre (52# is below 1e18). */
    public static final int MAX_N = 52;

    private static final long[] BASES = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private PrimorialPyres() {
    }

    private static long mulMod(long a, long b, long m) {
        return BigInteger.valueOf(a).multiply(BigInteger.valueOf(b)).mod(BigInteger.valueOf(m)).longValue();
    }

    private static long powMod(long b, long e, long m) {
        long r = 1;
        long x = b % m;
        long k = e;
        while (k > 0) {
            if ((k & 1L) != 0) {
                r = mulMod(r, x, m);
            }
            x = mulMod(x, x, m);
            k >>= 1;
        }
        return r;
    }

    /** Deterministic primality for any long (false below 2). */
    public static boolean isPrime(long n) {
        if (n < 2) {
            return false;
        }
        for (long p : BASES) {
            if (n % p == 0) {
                return n == p;
            }
        }
        long d = n - 1;
        int s = 0;
        while ((d & 1L) == 0) {
            d >>= 1;
            s++;
        }
        for (long a : BASES) {
            long x = powMod(a, d, n);
            if (x == 1 || x == n - 1) {
                continue;
            }
            boolean witness = true;
            for (int i = 1; i < s; i++) {
                x = mulMod(x, x, n);
                if (x == n - 1) {
                    witness = false;
                    break;
                }
            }
            if (witness) {
                return false;
            }
        }
        return true;
    }

    /** n#, the product of all primes &lt;= n (1 for n &lt; 2). */
    public static long primorial(int n) {
        if (n < 0 || n > MAX_N) {
            throw new IllegalArgumentException("pyre out of range: " + n);
        }
        long p = 1;
        for (int k = 2; k <= n; k++) {
            if (isPrime(k)) {
                p *= k;
            }
        }
        return p;
    }

    private static List<Integer> flames(int limit, int sign) {
        if (limit < 0 || limit > MAX_N) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        List<Integer> out = new ArrayList<>();
        for (int p = 2; p <= limit; p++) {
            if (isPrime(p) && isPrime(primorial(p) + sign)) {
                out.add(p);
            }
        }
        return out;
    }

    /** Primes p &lt;= limit with p# + 1 prime. */
    public static List<Integer> euclidFlames(int limit) {
        return flames(limit, 1);
    }

    /** Primes p &lt;= limit with p# - 1 prime. */
    public static List<Integer> kummerFlames(int limit) {
        return flames(limit, -1);
    }

    /** Grade a claim that the Euclid flame n# + 1 is (or is not) prime. */
    public static Grade grade(int n, boolean claimedPrime) {
        return isPrime(primorial(n) + 1) == claimedPrime ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: you read the flame true. Not every pyre plus one burns prime.";
            case SLIPPED -> "Forgemaster: the flame slipped. The product plus one escapes those primes, not all.";
        };
    }
}
