// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.match;

/**
 * Birthday-problem odds on a circular year of {@code nights}: chance that some two of {@code crew} sailors were born
 * on the same night, or within {@code window} nights of each other (the year wraps). P(no near pair) = prod over i of
 * (d - n k - i) / d for i = 1..n-1, which is the classic product when k = 0.
 */
public final class BirthNightOdds {

    public static final int MAX_NIGHTS = 10_000;
    public static final int MAX_CREW = 2_000;

    private final int nights;

    public BirthNightOdds(int nights) {
        if (nights < 2 || nights > MAX_NIGHTS) {
            throw new IllegalArgumentException("nights must be in [2, " + MAX_NIGHTS + "]: " + nights);
        }
        this.nights = nights;
    }

    public int nights() {
        return nights;
    }

    /** P(some two of {@code crew} share a night). */
    public double shareChance(int crew) {
        return nearChance(crew, 0);
    }

    /** P(some two of {@code crew} were born within {@code window} nights of each other, wrapping the year). */
    public double nearChance(int crew, int window) {
        check(crew, window);
        if (crew < 2) {
            return 0.0;
        }
        if ((long) crew * (window + 1) > nights) {
            return 1.0;
        }
        double none = 1.0;
        for (int i = 1; i < crew; i++) {
            none *= (nights - (double) crew * window - i) / nights;
        }
        return Math.max(0.0, Math.min(1.0, 1.0 - none));
    }

    /** Expected pairs within {@code window} nights: C(n, 2) (2k + 1) / d (capped window). */
    public double expectedPairs(int crew, int window) {
        check(crew, window);
        int span = Math.min(nights, 2 * window + 1);
        return crew * (crew - 1) / 2.0 * span / nights;
    }

    /** Smallest crew with at least {@code confidence} chance of a pair within {@code window}. */
    public int smallestCrew(double confidence, int window) {
        if (!(confidence > 0 && confidence < 1)) {
            throw new IllegalArgumentException("confidence must be in (0, 1): " + confidence);
        }
        for (int n = 2; n <= MAX_CREW; n++) {
            if (nearChance(n, window) >= confidence) {
                return n;
            }
        }
        return -1;
    }

    private void check(int crew, int window) {
        if (crew < 0 || crew > MAX_CREW) {
            throw new IllegalArgumentException("crew must be in [0, " + MAX_CREW + "]: " + crew);
        }
        if (window < 0 || window >= nights) {
            throw new IllegalArgumentException("window must be in [0, " + (nights - 1) + "]: " + window);
        }
    }
}
