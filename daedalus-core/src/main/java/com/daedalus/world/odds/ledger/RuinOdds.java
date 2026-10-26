// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.ledger;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;

/**
 * Seeded risk-of-ruin board for the Keeper's Ledger: from {@code start} herbs, repeat one kind of wager (chance
 * {@code p}, decimal odds) staking Kelly advice each time, until the bankroll reaches {@code target} (doubled), drops
 * below 1 herb (ruined), the Keeper advises no stake, or {@code maxWagers} run out (expired). Trial {@code t} uses
 * {@link OddsRng#forTrial(long, long)}.
 */
public final class RuinOdds {

    /** How one trial ended. */
    public enum Outcome { DOUBLED, RUINED, EXPIRED }

    private final int trials;
    private final int[] counts;

    private RuinOdds(int trials, int[] counts) {
        this.trials = trials;
        this.counts = counts;
    }

    /** Runs {@code trials} seeded bankrolls. */
    public static RuinOdds simulate(Plan plan, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int[] counts = new int[Outcome.values().length];
        for (int t = 0; t < trials; t++) {
            counts[plan.play(OddsRng.forTrial(seed, t)).ordinal()]++;
        }
        return new RuinOdds(trials, counts);
    }

    public int trials() {
        return trials;
    }

    public int count(Outcome o) {
        return counts[o.ordinal()];
    }

    public double chance(Outcome o) {
        return counts[o.ordinal()] / (double) trials;
    }

    /** 95% Wilson interval on the chance of {@code o}. */
    public double[] interval(Outcome o) {
        return Intervals.wilson(counts[o.ordinal()], trials);
    }

    /**
     * A staking plan: bankroll start and target, wager cap, the repeated wager (p, odds) and the Kelly shading.
     */
    public record Plan(int start, int target, int maxWagers, double p, double odds, double multiplier, double cap) {
        public Plan {
            if (start < 1 || target <= start || maxWagers < 1) {
                throw new IllegalArgumentException("need 1 <= start < target and maxWagers >= 1");
            }
            KellyStake.advise(start, p, odds, multiplier, cap);
        }

        /** Plays one bankroll on {@code rng}. */
        public Outcome play(OddsRng rng) {
            HerbLedger ledger = new HerbLedger(start);
            for (int w = 0; w < maxWagers; w++) {
                int stake = KellyStake.advise(ledger.balance(), p, odds, multiplier, cap);
                if (stake == 0) {
                    return Outcome.EXPIRED;
                }
                ledger.settle("plan", stake, odds, rng.chance(p));
                if (ledger.balance() >= target) {
                    return Outcome.DOUBLED;
                }
                if (ledger.broke()) {
                    return Outcome.RUINED;
                }
            }
            return Outcome.EXPIRED;
        }
    }
}
