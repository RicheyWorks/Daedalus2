// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;

/**
 * Automorph Anvil: a stamp n is automorphic when n squared ends in n's own digits (5^2 = 25, 76^2 = 5776). The smith
 * checks a stamp in any base and forges the two nontrivial k-digit automorphic tails of base 10 (the idempotents
 * mod 10^k) by Hensel lifting x -&gt; 3x^2 - 2x^3, without searching.
 *
 * <p>Reusable API: {@link #isAutomorphic} (plain long, bases 2..36) and {@link #tails} (BigInteger, k up to
 * {@link #MAX_DIGITS}).
 */
public final class AutomorphAnvil {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_automorph_anvil";
    /** Largest supported tail length. */
    public static final int MAX_DIGITS = 5000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private AutomorphAnvil() {
    }

    /** True when n^2 ends in the base-b digits of n (n &gt;= 0). */
    public static boolean isAutomorphic(long n, int base) {
        if (n < 0 || base < 2 || base > 36) {
            throw new IllegalArgumentException("bad stamp query");
        }
        BigInteger b = BigInteger.valueOf(base);
        BigInteger m = BigInteger.ONE;
        long x = n;
        do {
            m = m.multiply(b);
            x /= base;
        } while (x > 0);
        BigInteger bn = BigInteger.valueOf(n);
        return bn.multiply(bn).mod(m).equals(bn);
    }

    /**
     * The two nontrivial solutions of x^2 = x mod 10^k, as {e5, e2}: e5 = 0 mod 5^k, 1 mod 2^k (ends ...625) and
     * e2 = 1 - e5 mod 10^k (ends ...376). A tail may have leading zeros.
     */
    public static BigInteger[] tails(int k) {
        if (k < 1 || k > MAX_DIGITS) {
            throw new IllegalArgumentException("tail length out of range: " + k);
        }
        BigInteger mod = BigInteger.TEN.pow(k);
        BigInteger x = BigInteger.valueOf(5);
        BigInteger three = BigInteger.valueOf(3);
        BigInteger two = BigInteger.TWO;
        for (int got = 1; got < k; got *= 2) {
            BigInteger x2 = x.multiply(x).mod(mod);
            x = three.multiply(x2).subtract(two.multiply(x2).multiply(x)).mod(mod);
        }
        BigInteger e2 = BigInteger.ONE.subtract(x).mod(mod);
        return new BigInteger[] {x, e2};
    }

    /** Grade a claimed k-digit automorphic tail (true when it is one of 0, 1, e5, e2 mod 10^k). */
    public static Grade grade(int k, BigInteger claimed) {
        BigInteger mod = BigInteger.TEN.pow(k);
        if (claimed == null || claimed.signum() < 0 || claimed.compareTo(mod) >= 0) {
            return Grade.SLIPPED;
        }
        return claimed.multiply(claimed).mod(mod).equals(claimed) ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: square it and the stamp comes back. The anvil remembers.";
            case SLIPPED -> "Forgemaster: the stamp slipped. Lift from 5 with 3x^2 - 2x^3, doubling the digits.";
        };
    }
}
