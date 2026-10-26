// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.benford;

/**
 * Benford's first-digit law and a chi-square audit against it. P(first digit d) = log10(1 + 1/d). The chi-square
 * statistic over the nine digits has 8 degrees of freedom; its upper tail for even df is exact:
 * P(X &gt; x) = e^(-x/2) sum over i &lt; 4 of (x/2)^i / i!.
 */
public final class BenfordLaw {

    /** Chi-square value with a 5% upper tail at 8 degrees of freedom. */
    public static final double CRITICAL_5PCT = 15.507313055865453;

    private BenfordLaw() {
    }

    /** P(first digit = {@code d}) for d in 1..9. */
    public static double firstDigit(int d) {
        if (d < 1 || d > 9) {
            throw new IllegalArgumentException("digit must be in [1, 9]: " + d);
        }
        return Math.log10(1.0 + 1.0 / d);
    }

    /** Leading digit of a positive finite value. */
    public static int leadingDigit(double value) {
        if (!(value > 0) || Double.isInfinite(value)) {
            throw new IllegalArgumentException("value must be positive and finite: " + value);
        }
        double v = value;
        while (v >= 10) {
            v /= 10;
        }
        while (v < 1) {
            v *= 10;
        }
        return Math.min(9, Math.max(1, (int) v));
    }

    /** Counts of first digits 1..9 (index 0 unused). */
    public static int[] digitCounts(double[] values) {
        int[] c = new int[10];
        for (double v : values) {
            c[leadingDigit(v)]++;
        }
        return c;
    }

    /** Chi-square of digit counts (index 1..9) against Benford. */
    public static double chiSquare(int[] counts) {
        if (counts == null || counts.length != 10) {
            throw new IllegalArgumentException("counts must have 10 entries (index 0 unused)");
        }
        int n = 0;
        for (int d = 1; d <= 9; d++) {
            if (counts[d] < 0) {
                throw new IllegalArgumentException("negative count");
            }
            n += counts[d];
        }
        if (n == 0) {
            throw new IllegalArgumentException("no entries");
        }
        double x = 0;
        for (int d = 1; d <= 9; d++) {
            double e = n * firstDigit(d);
            x += (counts[d] - e) * (counts[d] - e) / e;
        }
        return x;
    }

    /** Exact upper tail P(X &gt; x) of chi-square with 8 degrees of freedom. */
    public static double tail8(double x) {
        if (!(x >= 0)) {
            throw new IllegalArgumentException("x must be >= 0: " + x);
        }
        double h = x / 2.0;
        double term = 1.0;
        double sum = 1.0;
        for (int i = 1; i < 4; i++) {
            term *= h / i;
            sum += term;
        }
        return Math.exp(-h) * sum;
    }

    /** Whether the counts fail the 5% Benford audit. */
    public static boolean flagged(int[] counts) {
        return chiSquare(counts) > CRITICAL_5PCT;
    }
}
