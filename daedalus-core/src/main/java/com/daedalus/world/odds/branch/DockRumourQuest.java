// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.branch;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_dock_rumour: the Keeper needs word of the storm-ark sailing to reach every dock before the tide turns,
 * {@link #GENERATIONS} tellings from now. Each sailor tells {@link #MATES} mates and each believes and passes it on
 * with chance {@link #BELIEF}. You buy grog for 1..{@link #MAX_SEEDS} first tellers; the word must still be going
 * at the last telling. No wagering.
 */
public final class DockRumourQuest {

    public static final int MATES = 3;
    public static final double BELIEF = 0.4;
    public static final int GENERATIONS = 8;
    public static final int MAX_SEEDS = 6;
    public static final double CONFIDENCE = 0.90;

    /** Quest stages. */
    public enum Stage { PLANNING, SPREAD, FIZZLED }

    private final BranchingOdds law = BranchingOdds.binomial(MATES, BELIEF);
    private Stage stage = Stage.PLANNING;
    private long[] tellers;
    private int seeds;

    public Stage stage() {
        return stage;
    }

    /** Exact P(the word is still going at the last telling) from {@code firstTellers}. */
    public double chance(int firstTellers) {
        return law.aliveAt(GENERATIONS, firstTellers);
    }

    /** Fewest first tellers the Keeper advises for {@link #CONFIDENCE} by the tide. */
    public int advised() {
        for (int s = 1; s <= MAX_SEEDS; s++) {
            if (chance(s) >= CONFIDENCE) {
                return s;
            }
        }
        return MAX_SEEDS;
    }

    /** Tellers per telling after the spread (a copy), or an empty array before it. */
    public long[] tellers() {
        return tellers == null ? new long[0] : tellers.clone();
    }

    /** Buys grog for {@code firstTellers} and lets the word run on {@code seed}; returns the final stage. */
    public Stage spread(int firstTellers, long seed) {
        if (stage != Stage.PLANNING) {
            throw new IllegalStateException("the word is already out: " + stage);
        }
        if (firstTellers < 1 || firstTellers > MAX_SEEDS) {
            throw new IllegalArgumentException("first tellers must be in [1, " + MAX_SEEDS + "]: " + firstTellers);
        }
        seeds = firstTellers;
        tellers = RumourSpread.spread(law, firstTellers, GENERATIONS, new OddsRng(seed));
        stage = tellers[GENERATIONS] > 0 ? Stage.SPREAD : Stage.FIZZLED;
        return stage;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case PLANNING -> String.format(Locale.ROOT,
                    "One teller and the word lives to the tide %.0f%% of the time. Buy grog for %d and it's %.0f%%.",
                    chance(1) * 100, advised(), chance(advised()) * 100);
            case SPREAD -> String.format(Locale.ROOT, "%d first tellers, %d sailors telling it at the tide. Every dock"
                    + " knows.", seeds, tellers[GENERATIONS]);
            case FIZZLED -> String.format(Locale.ROOT, "%d first tellers and the word died out by telling %d.", seeds,
                    lastAlive() + 1);
        };
    }

    private int lastAlive() {
        int g = 0;
        while (g < GENERATIONS && tellers[g + 1] > 0) {
            g++;
        }
        return g;
    }
}
