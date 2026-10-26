// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.stopping;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/**
 * A seeded lineup of ark-captain candidates, each with a distinct seamanship score, arriving in a random order
 * (Fisher-Yates over {@link OddsRng}). {@link #simulate} checks {@link StoppingRule#success} against seeded lineups.
 */
public final class CaptainLineup {

    private final double[] scores;

    private CaptainLineup(double[] scores) {
        this.scores = scores;
    }

    /** {@code n} candidates with scores 1..n shuffled by {@code rng}. */
    public static CaptainLineup shuffled(int n, OddsRng rng) {
        if (n < 1) {
            throw new IllegalArgumentException("n must be >= 1: " + n);
        }
        double[] s = new double[n];
        for (int i = 0; i < n; i++) {
            s[i] = i + 1;
        }
        for (int i = n - 1; i > 0; i--) {
            int j = (int) Math.floor(rng.nextDouble() * (i + 1));
            double tmp = s[i];
            s[i] = s[j];
            s[j] = tmp;
        }
        return new CaptainLineup(s);
    }

    public int size() {
        return scores.length;
    }

    /** Score of the candidate interviewed {@code i}-th. */
    public double score(int i) {
        return scores[i];
    }

    /** Index of the best candidate. */
    public int best() {
        int b = 0;
        for (int i = 1; i < scores.length; i++) {
            if (scores[i] > scores[b]) {
                b = i;
            }
        }
        return b;
    }

    /** Index the cutoff-{@code r} rule picks. */
    public int pick(int r) {
        return StoppingRule.choose(scores, r);
    }

    /** Seeded success rate of cutoff {@code r} over {@code trials} lineups: {estimate, lo, hi}. */
    public static double[] simulate(int n, int r, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int hits = 0;
        for (int t = 0; t < trials; t++) {
            CaptainLineup l = shuffled(n, OddsRng.forTrial(seed, t));
            if (l.pick(r) == l.best()) {
                hits++;
            }
        }
        double[] ci = Intervals.wilson(hits, trials);
        return new double[] {hits / (double) trials, ci[0], ci[1]};
    }
}
