// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.stopping;

/**
 * The look-then-leap rule for choosing the best of {@code n} candidates seen one at a time with no going back: let the
 * first {@code r} pass, then take the first who beats all of them. Exact success chance
 * P(r) = (r / n) x sum_{i = r + 1..n} 1 / (i - 1) for r >= 1, and P(0) = 1 / n.
 */
public final class StoppingRule {

    private StoppingRule() {
    }

    /** Exact chance the rule with cutoff {@code r} picks the single best of {@code n}. */
    public static double success(int n, int r) {
        if (n < 1 || r < 0 || r >= n) {
            throw new IllegalArgumentException("need n >= 1 and 0 <= r < n: n=" + n + " r=" + r);
        }
        if (r == 0) {
            return 1.0 / n;
        }
        double s = 0;
        for (int i = r + 1; i <= n; i++) {
            s += 1.0 / (i - 1);
        }
        return r / (double) n * s;
    }

    /** The cutoff with the highest exact success chance (ties to the smaller cutoff). */
    public static int bestCutoff(int n) {
        int best = 0;
        for (int r = 1; r < n; r++) {
            if (success(n, r) > success(n, best) + 1e-15) {
                best = r;
            }
        }
        return best;
    }

    /**
     * Applies the rule to a sequence of scores (higher is better): returns the index chosen, or the last index if no one
     * after the cutoff beats the look phase (you are stuck with the last candidate).
     */
    public static int choose(double[] scores, int r) {
        if (scores.length < 1 || r < 0 || r >= scores.length) {
            throw new IllegalArgumentException("need 0 <= r < scores.length");
        }
        double bar = Double.NEGATIVE_INFINITY;
        for (int i = 0; i < r; i++) {
            bar = Math.max(bar, scores[i]);
        }
        for (int i = r; i < scores.length; i++) {
            if (scores[i] > bar) {
                return i;
            }
        }
        return scores.length - 1;
    }
}
