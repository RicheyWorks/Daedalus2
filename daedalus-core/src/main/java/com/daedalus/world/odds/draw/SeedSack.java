// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.draw;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/**
 * A physical ark seed sack: {@code total} seeds, {@code good} of them viable, drawn without replacement with a seeded
 * partial Fisher-Yates. {@link #simulate} checks {@link Hypergeometric#atLeast} against seeded draws.
 */
public final class SeedSack {

    private SeedSack() {
    }

    /** Draws {@code n} seeds from a sack; returns how many are viable. */
    public static int draw(int total, int good, int n, OddsRng rng) {
        if (total < 1 || good < 0 || good > total || n < 0 || n > total) {
            throw new IllegalArgumentException("bad sack or draw");
        }
        boolean[] viable = new boolean[total];
        for (int i = 0; i < good; i++) {
            viable[i] = true;
        }
        int hits = 0;
        for (int i = 0; i < n; i++) {
            int j = i + (int) Math.floor(rng.nextDouble() * (total - i));
            boolean tmp = viable[i];
            viable[i] = viable[j];
            viable[j] = tmp;
            if (viable[i]) {
                hits++;
            }
        }
        return hits;
    }

    /** Seeded P(at least {@code m} viable in {@code n}) over {@code trials}: {estimate, lo, hi}. */
    public static double[] simulate(int total, int good, int n, int m, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int hits = 0;
        for (int t = 0; t < trials; t++) {
            if (draw(total, good, n, OddsRng.forTrial(seed, t)) >= m) {
                hits++;
            }
        }
        double[] ci = Intervals.wilson(hits, trials);
        return new double[] {hits / (double) trials, ci[0], ci[1]};
    }
}
