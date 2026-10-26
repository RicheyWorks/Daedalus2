// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

/**
 * Confidence intervals shared by every OddsReaper odds model (combat, fishing, later parlays). Public so other
 * {@code com.daedalus.world} modules reuse one honest formula instead of each growing its own.
 */
public final class Intervals {

    /** Two-sided 95% normal quantile. */
    public static final double Z95 = 1.959963984540054;

    private Intervals() {
    }

    /**
     * Wilson score interval for {@code k} successes in {@code n} trials: {low, high}. Honest near 0 and 1, where the
     * plain normal interval collapses or leaves [0, 1].
     *
     * @throws IllegalArgumentException if {@code n < 1} or {@code k} is outside [0, n]
     */
    public static double[] wilson(int k, int n) {
        if (n < 1 || k < 0 || k > n) {
            throw new IllegalArgumentException("wilson needs 0 <= k <= n and n >= 1, got k=" + k + " n=" + n);
        }
        double p = (double) k / n;
        double z2 = Z95 * Z95;
        double denom = 1 + z2 / n;
        double centre = (p + z2 / (2.0 * n)) / denom;
        double half = Z95 * Math.sqrt(p * (1 - p) / n + z2 / (4.0 * n * n)) / denom;
        return new double[] {Math.max(0, centre - half), Math.min(1, centre + half)};
    }
}
