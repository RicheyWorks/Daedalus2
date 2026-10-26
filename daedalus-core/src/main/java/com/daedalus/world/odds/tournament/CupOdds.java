// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tournament;

import com.daedalus.world.odds.OddsRng;
import java.util.Objects;

/**
 * The Odds Keeper's title board for the Squall Cup: each angler's chance to win the whole cup, estimated by replaying
 * the bracket many times. Trial {@code t} uses {@link OddsRng#forTrial(long, long)}, so a board is a pure function of
 * (bracket, heat, seed, trials).
 */
public final class CupOdds {

    private final int trials;
    private final int[] titles;

    private CupOdds(int trials, int[] titles) {
        this.trials = trials;
        this.titles = titles;
    }

    /** Replays the cup {@code trials} times from {@code seed}. */
    public static CupOdds simulate(Bracket bracket, Heat heat, long seed, int trials) {
        Objects.requireNonNull(bracket, "bracket");
        Objects.requireNonNull(heat, "heat");
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int[] titles = new int[bracket.anglers().size()];
        for (int t = 0; t < trials; t++) {
            titles[bracket.champion(heat, OddsRng.forTrial(seed, t))]++;
        }
        return new CupOdds(trials, titles);
    }

    public int trials() {
        return trials;
    }

    /** Cups won by angler {@code i} across the trials. */
    public int titles(int i) {
        return titles[i];
    }

    /** Estimated title chance of angler {@code i}. */
    public double chance(int i) {
        return titles[i] / (double) trials;
    }

    /** Fair decimal odds (1 / chance); infinite for an angler who never won a trial. */
    public double fairOdds(int i) {
        return titles[i] == 0 ? Double.POSITIVE_INFINITY : trials / (double) titles[i];
    }

    /** Index of the favourite (most titles; ties to the higher seed). */
    public int favourite() {
        int best = 0;
        for (int i = 1; i < titles.length; i++) {
            if (titles[i] > titles[best]) {
                best = i;
            }
        }
        return best;
    }
}
