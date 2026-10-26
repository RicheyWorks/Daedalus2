// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.match;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;
import java.util.Arrays;

/** A seeded crew's birth nights, uniform on the year, with the closest circular gap between any two. */
public final class CrewMuster {

    private final int[] births;
    private final int nights;

    private CrewMuster(int[] births, int nights) {
        this.births = births;
        this.nights = nights;
    }

    /** Musters {@code crew} sailors on a year of {@code nights} with {@code rng}. */
    public static CrewMuster muster(int nights, int crew, OddsRng rng) {
        if (nights < 2 || crew < 0) {
            throw new IllegalArgumentException("bad muster");
        }
        int[] b = new int[crew];
        for (int i = 0; i < crew; i++) {
            b[i] = Math.min(nights - 1, (int) Math.floor(rng.nextDouble() * nights));
        }
        Arrays.sort(b);
        return new CrewMuster(b, nights);
    }

    /** A crew with the given birth nights (0-based, 0..nights-1); night nights-1 and night 0 are neighbours. */
    public static CrewMuster of(int nights, int... births) {
        if (nights < 2 || births == null) {
            throw new IllegalArgumentException("bad crew");
        }
        int[] b = births.clone();
        for (int x : b) {
            if (x < 0 || x >= nights) {
                throw new IllegalArgumentException("night must be in [0, " + (nights - 1) + "]: " + x);
            }
        }
        Arrays.sort(b);
        return new CrewMuster(b, nights);
    }

    /** Birth nights, sorted (a copy). */
    public int[] births() {
        return births.clone();
    }

    /** Smallest circular gap in nights between two sailors, or -1 for fewer than two. */
    public int closestGap() {
        if (births.length < 2) {
            return -1;
        }
        int best = births[0] + nights - births[births.length - 1];
        for (int i = 1; i < births.length; i++) {
            best = Math.min(best, births[i] - births[i - 1]);
        }
        return best;
    }

    /** Whether two sailors were born within {@code window} nights. */
    public boolean hasPairWithin(int window) {
        int gap = closestGap();
        return gap >= 0 && gap <= window;
    }

    /** Seeded P(pair within {@code window}) over {@code trials}: {estimate, lo, hi}. */
    public static double[] simulate(int nights, int crew, int window, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int hits = 0;
        for (int t = 0; t < trials; t++) {
            if (muster(nights, crew, OddsRng.forTrial(seed, t)).hasPairWithin(window)) {
                hits++;
            }
        }
        double[] ci = Intervals.wilson(hits, trials);
        return new double[] {hits / (double) trials, ci[0], ci[1]};
    }
}
