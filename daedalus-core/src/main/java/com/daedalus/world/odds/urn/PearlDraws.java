// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.urn;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/** Seeded draws from a {@link PolyaUrn}. */
public final class PearlDraws {

    private PearlDraws() {
    }

    /** White draws in {@code draws} seeded draws. */
    public static int draw(PolyaUrn urn, int draws, OddsRng rng) {
        if (draws < 0) {
            throw new IllegalArgumentException("draws must be >= 0: " + draws);
        }
        int w = 0;
        for (int m = 0; m < draws; m++) {
            if (rng.chance(urn.nextWhite(w, m))) {
                w++;
            }
        }
        return w;
    }

    /** Seeded P(exactly {@code whites} white in {@code draws}): {estimate, lo, hi}. */
    public static double[] simulate(PolyaUrn urn, int draws, int whites, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int hits = 0;
        for (int t = 0; t < trials; t++) {
            if (draw(urn, draws, OddsRng.forTrial(seed, t)) == whites) {
                hits++;
            }
        }
        double[] ci = Intervals.wilson(hits, trials);
        return new double[] {hits / (double) trials, ci[0], ci[1]};
    }
}
