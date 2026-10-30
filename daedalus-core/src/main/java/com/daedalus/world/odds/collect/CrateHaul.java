// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.collect;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/** Seeded salvage crates: each holds one uniformly random chart fragment. Checks {@link ChartFragments} by sampling. */
public final class CrateHaul {

    private final int distinct;
    private final int duplicates;

    private CrateHaul(int distinct, int duplicates) {
        this.distinct = distinct;
        this.duplicates = duplicates;
    }

    /** Opens {@code crates} crates of {@code fragments} kinds on {@code rng}. */
    public static CrateHaul open(int fragments, int crates, OddsRng rng) {
        if (fragments < 1 || crates < 0) {
            throw new IllegalArgumentException("bad haul");
        }
        boolean[] seen = new boolean[fragments];
        int distinct = 0;
        for (int i = 0; i < crates; i++) {
            int f = Math.min(fragments - 1, (int) Math.floor(rng.nextDouble() * fragments));
            if (!seen[f]) {
                seen[f] = true;
                distinct++;
            }
        }
        return new CrateHaul(distinct, crates - distinct);
    }

    public int distinct() {
        return distinct;
    }

    public int duplicates() {
        return duplicates;
    }

    /** Whether this haul makes a full chart of {@code fragments} at trade-in {@code rate} (0 = none). */
    public boolean full(int fragments, int rate) {
        int missing = fragments - distinct;
        return missing == 0 || (rate > 0 && rate * missing <= duplicates);
    }

    /** Seeded P(full chart) over {@code trials}: {estimate, lo, hi}. */
    public static double[] simulate(int fragments, int crates, int rate, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int hits = 0;
        for (int t = 0; t < trials; t++) {
            if (open(fragments, crates, OddsRng.forTrial(seed, t)).full(fragments, rate)) {
                hits++;
            }
        }
        double[] ci = Intervals.wilson(hits, trials);
        return new double[] {hits / (double) trials, ci[0], ci[1]};
    }
}
