// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.dice;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/**
 * Plays the Keeper's pass-line game with seeded storm dice. One round: come-out roll, then roll for the point if one is
 * set. With an odds multiple {@code m}, the player backs every point with m herbs at true odds.
 */
public final class StormDice {

    private StormDice() {
    }

    /** One die face from {@code rng}. */
    static int die(OddsRng rng) {
        return 1 + (int) Math.floor(rng.nextDouble() * 6);
    }

    /** Result of one round: net herbs (pass stake 1 + odds stake m) and rolls taken. */
    public record Round(boolean won, int point, double net, int rolls) {
    }

    /** Plays one round with pass stake 1 and odds multiple {@code m}. */
    public static Round play(OddsRng rng, int m) {
        if (m < 0) {
            throw new IllegalArgumentException("multiple must be >= 0: " + m);
        }
        int rolls = 1;
        int comeOut = die(rng) + die(rng);
        if (comeOut == 7 || comeOut == 11) {
            return new Round(true, 0, 1.0, rolls);
        }
        if (!DiceMath.isPoint(comeOut)) {
            return new Round(false, 0, -1.0, rolls);
        }
        while (true) {
            rolls++;
            int r = die(rng) + die(rng);
            if (r == comeOut) {
                return new Round(true, comeOut, 1.0 + m * DiceMath.trueOdds(comeOut), rolls);
            }
            if (r == 7) {
                return new Round(false, comeOut, -1.0 - m, rolls);
            }
        }
    }

    /** Seeded pass-line wins over {@code trials} rounds: {estimate, wilsonLo, wilsonHi}. */
    public static double[] passWinEstimate(long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int wins = 0;
        for (int t = 0; t < trials; t++) {
            if (play(OddsRng.forTrial(seed, t), 0).won()) {
                wins++;
            }
        }
        double[] ci = Intervals.wilson(wins, trials);
        return new double[] {wins / (double) trials, ci[0], ci[1]};
    }
}
