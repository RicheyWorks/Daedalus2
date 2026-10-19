// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.draw;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_seed_sack: the arks' last sack of storm-herb seed holds {@link #SACK} seeds and only {@link #VIABLE} will
 * sprout. The herb terrace needs at least {@link #NEEDED} sprouts this season, and every seed planted is one less for
 * next year. Plant the fewest seeds that still give at least {@link #CONFIDENCE} chance of {@link #NEEDED} sprouts:
 * planting exactly the Keeper's number earns his nod; then the season is drawn once from the sack. In-game only.
 */
public final class SeedSackQuest {

    public static final int SACK = 60;
    public static final int VIABLE = 18;
    public static final int NEEDED = 4;
    public static final double CONFIDENCE = 0.90;

    /** Quest stages. */
    public enum Stage { PLANNING, TERRACE_GREEN, TERRACE_THIN }

    private final Hypergeometric sack = new Hypergeometric(SACK, VIABLE);
    private final int advised = sack.smallestDraw(NEEDED, CONFIDENCE);
    private Stage stage = Stage.PLANNING;
    private int planted;
    private int sprouted = -1;

    public Stage stage() {
        return stage;
    }

    /** The Keeper's advised number of seeds to plant. */
    public int advised() {
        return advised;
    }

    /** Exact chance that planting {@code n} gives at least {@link #NEEDED} sprouts. */
    public double chance(int n) {
        return sack.atLeast(n, NEEDED);
    }

    /** Plants {@code n} seeds and draws the season on {@code seed}; returns sprouts. */
    public int plant(int n, long seed) {
        if (stage != Stage.PLANNING) {
            throw new IllegalStateException("already planted: " + stage);
        }
        if (n < 1 || n > SACK) {
            throw new IllegalArgumentException("plant between 1 and " + SACK + ": " + n);
        }
        planted = n;
        sprouted = SeedSack.draw(SACK, VIABLE, n, new OddsRng(seed));
        stage = sprouted >= NEEDED ? Stage.TERRACE_GREEN : Stage.TERRACE_THIN;
        return sprouted;
    }

    /** Whether the player planted exactly the advised number. */
    public boolean thrifty() {
        return planted == advised;
    }

    public int sprouted() {
        return sprouted;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case PLANNING -> String.format(Locale.ROOT,
                    "Sixty seeds, eighteen good. Plant %d and it's %.0f%% the terrace greens. Every extra is next year's.",
                    advised, chance(advised) * 100);
            case TERRACE_GREEN -> thrifty()
                    ? String.format(Locale.ROOT, "%d sprouts from %d seeds, and the sack still holds next year.",
                            sprouted, planted)
                    : String.format(Locale.ROOT, "%d sprouts from %d seeds. Green, but %s.", sprouted, planted,
                            planted > advised ? "you spent next year's seed" : "you rolled the dice to get there");
            case TERRACE_THIN -> String.format(Locale.ROOT,
                    "Only %d sprouts. The terrace needs %d; the sack decides the rest.", sprouted, NEEDED);
        };
    }
}
