// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;

/**
 * Mersenne Bellows: a bellows with p folds blows 2^p - 1 puffs. The smith decides whether the blast is a prime blast
 * (a Mersenne prime) with the Lucas-Lehmer test, or names the smallest crack in it by trial factors 2kp + 1.
 *
 * <p>Reusable API: {@link #lucasLehmer}, {@link #isMersennePrime} and {@link #smallestFactor} for prime-or-any
 * exponents up to {@link #MAX_P}; reduction mod 2^p - 1 uses shift-and-add.
 */
public final class MersenneBellows {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_mersenne_bellows";
    /** Largest supported exponent. */
    public static final int MAX_P = 10_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private MersenneBellows() {
    }

    private static void check(int p) {
        if (p < 2 || p > MAX_P) {
            throw new IllegalArgumentException("exponent out of range: " + p);
        }
    }

    static boolean isPrimeInt(int n) {
        if (n < 2) {
            return false;
        }
        for (int f = 2; f * f <= n; f++) {
            if (n % f == 0) {
                return false;
            }
        }
        return true;
    }

    private static BigInteger modMersenne(BigInteger x, int p, BigInteger m) {
        BigInteger r = x;
        while (r.bitLength() > p) {
            r = r.and(m).add(r.shiftRight(p));
        }
        return r.equals(m) ? BigInteger.ZERO : r;
    }

    /** Lucas-Lehmer residue test for an odd prime p: true when 2^p - 1 is prime. */
    public static boolean lucasLehmer(int p) {
        check(p);
        if (p == 2) {
            return true;
        }
        if (!isPrimeInt(p)) {
            throw new IllegalArgumentException("exponent must be prime: " + p);
        }
        BigInteger m = BigInteger.ONE.shiftLeft(p).subtract(BigInteger.ONE);
        BigInteger s = BigInteger.valueOf(4);
        BigInteger two = BigInteger.TWO;
        for (int i = 0; i < p - 2; i++) {
            BigInteger t = modMersenne(s.multiply(s), p, m);
            s = t.compareTo(two) >= 0 ? t.subtract(two) : t.add(m).subtract(two);
        }
        return s.signum() == 0;
    }

    /** True when 2^p - 1 is prime, for any exponent 2..MAX_P (composite p gives false). */
    public static boolean isMersennePrime(int p) {
        check(p);
        return isPrimeInt(p) && lucasLehmer(p);
    }

    /**
     * Smallest prime factor of 2^p - 1 of the form 2kp + 1 with k &lt;= kMax, for prime p &gt; 2; 0 when none is
     * found within the bound.
     */
    public static long smallestFactor(int p, long kMax) {
        check(p);
        if (p == 2 || !isPrimeInt(p)) {
            throw new IllegalArgumentException("exponent must be an odd prime: " + p);
        }
        if (kMax < 0 || kMax > 1_000_000_000L) {
            throw new IllegalArgumentException("k bound out of range: " + kMax);
        }
        BigInteger e = BigInteger.valueOf(p);
        for (long k = 1; k <= kMax; k++) {
            long q = 2 * k * p + 1;
            long r8 = q & 7;
            if ((r8 == 1 || r8 == 7) && BigInteger.TWO.modPow(e, BigInteger.valueOf(q)).equals(BigInteger.ONE)) {
                BigInteger m = BigInteger.ONE.shiftLeft(p).subtract(BigInteger.ONE);
                return m.equals(BigInteger.valueOf(q)) ? 0 : q;
            }
        }
        return 0;
    }

    /** Grade a claim that the p-fold blast is (or is not) prime. */
    public static Grade grade(int p, boolean claimedPrime) {
        return isMersennePrime(p) == claimedPrime ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the blast rings true. Lucas and Lehmer counted every fold.";
            case SLIPPED -> "Forgemaster: the bellows slipped. A prime fold count does not make a prime blast.";
        };
    }
}
