// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;

/**
 * G295 The Sounding Line: the leadsman's soundings come back as huge whole numbers, and the chart
 * wants their whole square and k-th roots. Floor k-th roots by Newton's method on BigInteger
 * (exact, never through doubles), the remainder left over, and perfect-power detection: writing
 * n as a^b with the largest b.
 */
public final class SoundingLine {

    public static final String QUEST_ID = "q_sounding_line";

    /** n = base^exp with exp as large as possible (exp = 1 when n is no perfect power). */
    public record Power(BigInteger base, int exp) { }

    private SoundingLine() { }

    /** Floor of the k-th root of n, for n >= 0 and k >= 1. */
    public static BigInteger root(BigInteger n, int k) {
        if (n.signum() < 0 || k < 1) {
            throw new IllegalArgumentException("need n >= 0 and k >= 1");
        }
        if (k == 1 || n.signum() == 0) {
            return n;
        }
        BigInteger bk = BigInteger.valueOf(k);
        BigInteger km1 = BigInteger.valueOf(k - 1L);
        BigInteger x = BigInteger.ONE.shiftLeft((n.bitLength() + k - 1) / k);
        while (true) {
            BigInteger y = km1.multiply(x).add(n.divide(x.pow(k - 1))).divide(bk);
            if (y.compareTo(x) >= 0) {
                return x;
            }
            x = y;
        }
    }

    public static BigInteger isqrt(BigInteger n) {
        return root(n, 2);
    }

    /** n minus the largest k-th power not above it. */
    public static BigInteger remainder(BigInteger n, int k) {
        return n.subtract(root(n, k).pow(k));
    }

    /** Largest exponent b with n = a^b, for n >= 2. */
    public static Power perfectPower(BigInteger n) {
        if (n.compareTo(BigInteger.TWO) < 0) {
            throw new IllegalArgumentException("need n >= 2");
        }
        for (int b = n.bitLength(); b >= 2; b--) {
            BigInteger r = root(n, b);
            if (r.pow(b).equals(n)) {
                return new Power(r, b);
            }
        }
        return new Power(n, 1);
    }

    /** Quest q_sounding_line: name the base and the largest exponent of the sounding. */
    public static boolean quest(BigInteger n, BigInteger base, int exp) {
        return perfectPower(n).equals(new Power(base, exp));
    }
}