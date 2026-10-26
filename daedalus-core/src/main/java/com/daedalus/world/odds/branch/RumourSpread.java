// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.branch;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/** Seeded generations of tellers drawn from a {@link BranchingOdds} law. */
public final class RumourSpread {

    /** Tellers above this count are treated as "everyone has heard"; the walk stops early as alive. */
    public static final long CROWD = 1_000_000L;

    private RumourSpread() {
    }

    /** Tellers in each generation 0..{@code generations} from {@code seeds} first tellers (stops early at 0 or CROWD). */
    public static long[] spread(BranchingOdds law, int seeds, int generations, OddsRng rng) {
        if (seeds < 1 || generations < 0) {
            throw new IllegalArgumentException("bad spread");
        }
        double[] p = law.offspring();
        long[] gen = new long[generations + 1];
        gen[0] = seeds;
        for (int g = 1; g <= generations; g++) {
            long prev = gen[g - 1];
            if (prev == 0 || prev >= CROWD) {
                gen[g] = prev;
                continue;
            }
            long next = 0;
            for (long t = 0; t < prev; t++) {
                next += draw(p, rng);
            }
            gen[g] = Math.min(next, CROWD);
        }
        return gen;
    }

    /** Seeded P(word alive at generation {@code generations}): {estimate, lo, hi}. */
    public static double[] simulate(BranchingOdds law, int seeds, int generations, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int alive = 0;
        for (int t = 0; t < trials; t++) {
            long[] gen = spread(law, seeds, generations, OddsRng.forTrial(seed, t));
            if (gen[generations] > 0) {
                alive++;
            }
        }
        double[] ci = Intervals.wilson(alive, trials);
        return new double[] {alive / (double) trials, ci[0], ci[1]};
    }

    private static int draw(double[] p, OddsRng rng) {
        double u = rng.nextDouble();
        double acc = 0;
        for (int k = 0; k < p.length; k++) {
            acc += p[k];
            if (u < acc) {
                return k;
            }
        }
        return p.length - 1;
    }
}
