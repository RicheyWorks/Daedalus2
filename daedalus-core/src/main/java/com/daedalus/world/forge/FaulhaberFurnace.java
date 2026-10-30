// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;

/**
 * Faulhaber Furnace: the furnace heats ingot k-th powers 1^k + 2^k + ... + n^k in one pour. The smith names the exact
 * total without stacking every ingot, using Faulhaber's formula built from the Bernoulli numbers.
 *
 * <p>Reusable API: {@link #bernoulli} (exact rational, B1 = +1/2 convention), {@link #coefficients} of the sum
 * polynomial and {@link #powerSum} (exact BigInteger) for 0 &lt;= k &lt;= {@link #MAX_K} and any n &gt;= 0.
 */
public final class FaulhaberFurnace {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_faulhaber_furnace";
    /** Largest supported power. */
    public static final int MAX_K = 60;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private FaulhaberFurnace() {
    }

    private static void checkK(int k) {
        if (k < 0 || k > MAX_K + 1) {
            throw new IllegalArgumentException("power out of range: " + k);
        }
    }

    private static BigInteger[] reduce(BigInteger num, BigInteger den) {
        if (den.signum() == 0) {
            throw new ArithmeticException("zero denominator");
        }
        BigInteger g = num.gcd(den);
        if (g.signum() == 0) {
            return new BigInteger[] {BigInteger.ZERO, BigInteger.ONE};
        }
        BigInteger n = num.divide(g);
        BigInteger d = den.divide(g);
        if (d.signum() < 0) {
            n = n.negate();
            d = d.negate();
        }
        return new BigInteger[] {n, d};
    }

    private static BigInteger[] sub(BigInteger[] a, BigInteger[] b) {
        return reduce(a[0].multiply(b[1]).subtract(b[0].multiply(a[1])), a[1].multiply(b[1]));
    }

    /** Bernoulli number B_m as {numerator, denominator} in lowest terms, with B_1 = +1/2. */
    public static BigInteger[] bernoulli(int m) {
        checkK(m);
        BigInteger[][] a = new BigInteger[m + 1][];
        for (int j = 0; j <= m; j++) {
            a[j] = reduce(BigInteger.ONE, BigInteger.valueOf(j + 1L));
            for (int i = j; i >= 1; i--) {
                BigInteger[] d = sub(a[i - 1], a[i]);
                a[i - 1] = reduce(d[0].multiply(BigInteger.valueOf(i)), d[1]);
            }
        }
        return a[0];
    }

    static BigInteger binom(int n, int r) {
        BigInteger c = BigInteger.ONE;
        for (int i = 0; i < r; i++) {
            c = c.multiply(BigInteger.valueOf((long) n - i)).divide(BigInteger.valueOf(i + 1L));
        }
        return c;
    }

    /**
     * Coefficients of S_k(n) = sum_{i=1..n} i^k as a polynomial in n: element e is {num, den} for n^e,
     * e = 0..k+1.
     */
    public static BigInteger[][] coefficients(int k) {
        if (k < 0 || k > MAX_K) {
            throw new IllegalArgumentException("power out of range: " + k);
        }
        BigInteger[][] c = new BigInteger[k + 2][];
        c[0] = new BigInteger[] {BigInteger.ZERO, BigInteger.ONE};
        for (int j = 0; j <= k; j++) {
            BigInteger[] b = bernoulli(j);
            c[k + 1 - j] = reduce(b[0].multiply(binom(k + 1, j)), b[1].multiply(BigInteger.valueOf(k + 1L)));
        }
        return c;
    }

    /** Exact 1^k + 2^k + ... + n^k (0^0 excluded, so k = 0 gives n). */
    public static BigInteger powerSum(int k, long n) {
        if (n < 0) {
            throw new IllegalArgumentException("negative count: " + n);
        }
        BigInteger[][] c = coefficients(k);
        BigInteger den = BigInteger.ONE;
        for (BigInteger[] q : c) {
            den = den.divide(den.gcd(q[1])).multiply(q[1]);
        }
        BigInteger x = BigInteger.valueOf(n);
        BigInteger acc = BigInteger.ZERO;
        for (int e = c.length - 1; e >= 0; e--) {
            acc = acc.multiply(x).add(c[e][0].multiply(den.divide(c[e][1])));
        }
        return acc.divide(den);
    }

    /** Grade a claimed furnace total. */
    public static Grade grade(int k, long n, BigInteger claimed) {
        return powerSum(k, n).equals(claimed) ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: one pour, every ingot counted. Bernoulli keeps the furnace honest.";
            case SLIPPED -> "Forgemaster: the pour slipped. Weigh each power of n by its Bernoulli share.";
        };
    }
}
