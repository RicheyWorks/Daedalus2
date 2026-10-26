// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.bayes;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/**
 * Seeded operating characteristics of an SPRT: flip a coin whose true heads chance is {@code trueP} until the test
 * decides (or {@code maxFlips} run out), many times. Reports how often it called RIGGED, how often it ran out, and the
 * mean flips used. Trial {@code t} uses {@link OddsRng#forTrial(long, long)}.
 */
public record SprtOdds(int trials, int rigged, int undecided, double meanFlips) {

    public static SprtOdds simulate(double p0, double p1, double alpha, double beta, double trueP, int maxFlips,
            long seed, int trials) {
        if (trials < 1 || maxFlips < 1) {
            throw new IllegalArgumentException("trials and maxFlips must be >= 1");
        }
        if (!(trueP >= 0 && trueP <= 1)) {
            throw new IllegalArgumentException("trueP must be in [0, 1]: " + trueP);
        }
        int rigged = 0;
        int undecided = 0;
        long flips = 0;
        for (int t = 0; t < trials; t++) {
            OddsRng rng = OddsRng.forTrial(seed, t);
            Sprt s = new Sprt(p0, p1, alpha, beta);
            Sprt.Decision d = Sprt.Decision.CONTINUE;
            while (d == Sprt.Decision.CONTINUE && s.flips() < maxFlips) {
                d = s.record(rng.chance(trueP));
            }
            flips += s.flips();
            if (d == Sprt.Decision.RIGGED) {
                rigged++;
            } else if (d == Sprt.Decision.CONTINUE) {
                undecided++;
            }
        }
        return new SprtOdds(trials, rigged, undecided, flips / (double) trials);
    }

    public double riggedRate() {
        return rigged / (double) trials;
    }

    /** 95% Wilson interval on the RIGGED-call rate. */
    public double[] riggedInterval() {
        return Intervals.wilson(rigged, trials);
    }
}
