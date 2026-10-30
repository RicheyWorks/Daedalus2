// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Legendre Ladle: the ladle pours n! drops of molten metal. The smith names how many times a prime p divides the pour
 * (Legendre's formula), how many trailing zeros the pour shows when tallied in base b, and the p-free remainder of
 * n! modulo p (Wilson's theorem, digit by digit).
 *
 * <p>Reusable plain long API: {@link #valuation}, {@link #trailingZeros} and {@link #factorialUnitMod} for
 * 0 &lt;= n &lt;= {@link #MAX_N}, bases 2..{@link #MAX_BASE} and primes up to {@link #MAX_BASE}.
 */
public final class LegendreLadle {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_legendre_ladle";
    /** Largest supported n. */
    public static final long MAX_N = 1_000_000_000_000_000_000L;
    /** Largest supported base or prime. */
    public static final int MAX_BASE = 1_000_003;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private LegendreLadle() {
    }

    static boolean isPrime(long n) {
        if (n < 2) {
            return false;
        }
        for (long f = 2; f * f <= n; f++) {
            if (n % f == 0) {
                return false;
            }
        }
        return true;
    }

    private static void checkN(long n) {
        if (n < 0 || n > MAX_N) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
    }

    private static void checkPrime(long p) {
        if (p > MAX_BASE || !isPrime(p)) {
            throw new IllegalArgumentException("not a supported prime: " + p);
        }
    }

    /** Exponent of prime p in n! (Legendre's formula). */
    public static long valuation(long n, long p) {
        checkN(n);
        checkPrime(p);
        long v = 0;
        long m = n;
        while (m > 0) {
            m /= p;
            v += m;
        }
        return v;
    }

    /** Number of trailing zeros of n! written in base b. */
    public static long trailingZeros(long n, long b) {
        checkN(n);
        if (b < 2 || b > MAX_BASE) {
            throw new IllegalArgumentException("base out of range: " + b);
        }
        long best = Long.MAX_VALUE;
        long rest = b;
        for (long p = 2; p * p <= rest; p++) {
            int e = 0;
            while (rest % p == 0) {
                rest /= p;
                e++;
            }
            if (e > 0) {
                best = Math.min(best, valuation(n, p) / e);
            }
        }
        if (rest > 1) {
            best = Math.min(best, valuation(n, rest));
        }
        return best;
    }

    /** (n! / p^valuation(n, p)) mod p, using Wilson's theorem (p-1)! = -1 mod p. */
    public static long factorialUnitMod(long n, long p) {
        checkN(n);
        checkPrime(p);
        long[] fact = new long[(int) p];
        fact[0] = 1;
        for (int i = 1; i < p; i++) {
            fact[i] = fact[i - 1] * i % p;
        }
        long r = 1;
        long m = n;
        while (m > 0) {
            if (((m / p) & 1) == 1) {
                r = (p - r) % p;
            }
            r = r * fact[(int) (m % p)] % p;
            m /= p;
        }
        return r;
    }

    /** Grade a claimed trailing-zero count of n! in base b. */
    public static Grade grade(long n, long b, long claimed) {
        return trailingZeros(n, b) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: every power of the prime ladled out and counted. Clean pour.";
            case SLIPPED -> "Forgemaster: the ladle slipped. Sum n over p, p squared, p cubed, and take the scarcest.";
        };
    }
}
