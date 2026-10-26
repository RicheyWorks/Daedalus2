// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.benford;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/** Seeded cargo ledgers: honest counts spread log-uniformly over whole decades, cooked ones made up as 3-digit numbers. */
public final class CargoLedger {

    /** Decades an honest ledger spans (1 to 10^DECADES). */
    public static final int DECADES = 4;

    private CargoLedger() {
    }

    /** An honest ledger: values 10^(DECADES u), exactly Benford in the first digit. */
    public static double[] honest(int entries, OddsRng rng) {
        checkEntries(entries);
        double[] v = new double[entries];
        for (int i = 0; i < entries; i++) {
            v[i] = Math.pow(10.0, DECADES * rng.nextDouble());
        }
        return v;
    }

    /** A cooked ledger: whole numbers 100..999 picked evenly, so every first digit is 1/9. */
    public static double[] cooked(int entries, OddsRng rng) {
        checkEntries(entries);
        double[] v = new double[entries];
        for (int i = 0; i < entries; i++) {
            v[i] = 100 + Math.min(899, (int) Math.floor(rng.nextDouble() * 900));
        }
        return v;
    }

    /** Seeded P(the 5% audit flags a ledger) over {@code trials}: {estimate, lo, hi}. */
    public static double[] flagRate(boolean cookedLedger, int entries, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int flags = 0;
        for (int t = 0; t < trials; t++) {
            OddsRng rng = OddsRng.forTrial(seed, t);
            double[] v = cookedLedger ? cooked(entries, rng) : honest(entries, rng);
            if (BenfordLaw.flagged(BenfordLaw.digitCounts(v))) {
                flags++;
            }
        }
        double[] ci = Intervals.wilson(flags, trials);
        return new double[] {flags / (double) trials, ci[0], ci[1]};
    }

    private static void checkEntries(int entries) {
        if (entries < 1 || entries > 100_000) {
            throw new IllegalArgumentException("entries must be in [1, 100000]: " + entries);
        }
    }
}
