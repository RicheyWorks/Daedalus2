// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.bayes;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;
import java.util.Objects;

/**
 * Quest q_rigged_coin: the rival bookmaker (G77) swapped one of the Keeper's {@link #COINS} storm coins for a rigged
 * one that lands heads {@link #RIGGED_P} of the time. Each flip costs a herb from a {@link #BUDGET}-flip purse. The
 * Keeper keeps the exact posterior P(coin i is the rigged one) and an SPRT per coin; accuse the right coin to win.
 */
public final class RiggedCoinQuest {

    public static final int COINS = 3;
    public static final double FAIR_P = 0.5;
    public static final double RIGGED_P = 0.7;
    public static final int BUDGET = 30;
    public static final double ALPHA = 0.05;
    public static final double BETA = 0.05;

    /** Quest stages. */
    public enum Stage { FLIPPING, CAUGHT, WRONG_COIN, OUT_OF_HERBS }

    private final int rigged;
    private final OddsRng rng;
    private final int[] heads = new int[COINS];
    private final int[] tails = new int[COINS];
    private final Sprt[] tests = new Sprt[COINS];
    private Stage stage = Stage.FLIPPING;
    private int used;

    public RiggedCoinQuest(long seed) {
        OddsRng setup = new OddsRng(seed);
        this.rigged = (int) Math.floor(setup.nextDouble() * COINS);
        this.rng = new OddsRng(setup.nextLong());
        for (int i = 0; i < COINS; i++) {
            tests[i] = new Sprt(FAIR_P, RIGGED_P, ALPHA, BETA);
        }
    }

    public Stage stage() {
        return stage;
    }

    public int flipsLeft() {
        return BUDGET - used;
    }

    /** Flips coin {@code i}; returns true for heads. */
    public boolean flip(int i) {
        if (stage != Stage.FLIPPING) {
            throw new IllegalStateException("quest over: " + stage);
        }
        Objects.checkIndex(i, COINS);
        if (used >= BUDGET) {
            throw new IllegalStateException("no herbs left to flip");
        }
        boolean h = rng.chance(i == rigged ? RIGGED_P : FAIR_P);
        if (h) {
            heads[i]++;
        } else {
            tails[i]++;
        }
        tests[i].record(h);
        used++;
        return h;
    }

    /** SPRT decision on coin {@code i} so far. */
    public Sprt.Decision verdict(int i) {
        return tests[i].decision();
    }

    /**
     * Exact posterior that coin {@code i} is the rigged one, from a uniform prior: proportional to
     * (p1/p0)^heads_i x ((1-p1)/(1-p0))^tails_i.
     */
    public double posterior(int i) {
        Objects.checkIndex(i, COINS);
        double[] logw = new double[COINS];
        double max = Double.NEGATIVE_INFINITY;
        for (int c = 0; c < COINS; c++) {
            logw[c] = heads[c] * Math.log(RIGGED_P / FAIR_P) + tails[c] * Math.log((1 - RIGGED_P) / (1 - FAIR_P));
            max = Math.max(max, logw[c]);
        }
        double z = 0;
        for (int c = 0; c < COINS; c++) {
            z += Math.exp(logw[c] - max);
        }
        return Math.exp(logw[i] - max) / z;
    }

    /** The coin with the highest posterior (ties to the lowest index). */
    public int suspect() {
        int best = 0;
        for (int c = 1; c < COINS; c++) {
            if (posterior(c) > posterior(best)) {
                best = c;
            }
        }
        return best;
    }

    /** Accuses coin {@code i}; ends the quest. */
    public Stage accuse(int i) {
        if (stage != Stage.FLIPPING) {
            throw new IllegalStateException("quest over: " + stage);
        }
        Objects.checkIndex(i, COINS);
        stage = i == rigged ? Stage.CAUGHT : Stage.WRONG_COIN;
        return stage;
    }

    /** Gives up when the purse is empty without accusing. */
    public Stage forfeit() {
        if (stage != Stage.FLIPPING) {
            throw new IllegalStateException("quest over: " + stage);
        }
        stage = Stage.OUT_OF_HERBS;
        return stage;
    }

    /** Revealed only once the quest is over; -1 while flipping. */
    public int riggedCoin() {
        return stage == Stage.FLIPPING ? -1 : rigged;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case FLIPPING -> String.format(Locale.ROOT,
                    "%d flips left. My money is on coin %d at %.0f%%. Flip until the ledger is sure, not until you are.",
                    flipsLeft(), suspect() + 1, posterior(suspect()) * 100);
            case CAUGHT -> "That's the one. Weighted with ark lead. The rival owes me a coin and an apology.";
            case WRONG_COIN -> String.format(Locale.ROOT,
                    "Honest coin, that. It was coin %d. Streaks lie; counts don't.", rigged + 1);
            case OUT_OF_HERBS -> "Purse is empty. The rival keeps his secret today.";
        };
    }
}
