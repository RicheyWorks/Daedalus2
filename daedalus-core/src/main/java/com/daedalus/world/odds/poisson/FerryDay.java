// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.poisson;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/** A seeded ferry stream seen by one traveller who reaches the dock at minute {@code arrival}. */
public final class FerryDay {

    private final double wait;
    private final double gap;

    private FerryDay(double wait, double gap) {
        this.wait = wait;
        this.gap = gap;
    }

    /**
     * Runs ferries from minute 0 (exponential gaps of mean {@code meanGap}) past {@code arrival}; records the
     * traveller's wait and the length of the gap they landed in.
     */
    public static FerryDay at(double meanGap, double arrival, OddsRng rng) {
        if (!(meanGap > 0) || !(arrival >= 0)) {
            throw new IllegalArgumentException("bad ferry day");
        }
        double last = 0;
        double next = exp(meanGap, rng);
        while (next <= arrival) {
            last = next;
            next += exp(meanGap, rng);
        }
        return new FerryDay(next - arrival, next - last);
    }

    /** Minutes the traveller waited. */
    public double waited() {
        return wait;
    }

    /** Length of the ferry gap the traveller landed in. */
    public double gap() {
        return gap;
    }

    /** Seeded travellers at minute {@code arrival}: {mean wait, mean landed gap, P(wait > t), lo, hi}. */
    public static double[] simulate(double meanGap, double arrival, double beyond, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        double waits = 0;
        double gaps = 0;
        int longWaits = 0;
        for (int t = 0; t < trials; t++) {
            FerryDay d = at(meanGap, arrival, OddsRng.forTrial(seed, t));
            waits += d.wait;
            gaps += d.gap;
            if (d.wait > beyond) {
                longWaits++;
            }
        }
        double[] ci = Intervals.wilson(longWaits, trials);
        return new double[] {waits / trials, gaps / trials, longWaits / (double) trials, ci[0], ci[1]};
    }

    private static double exp(double mean, OddsRng rng) {
        return -mean * Math.log(1.0 - rng.nextDouble());
    }
}
