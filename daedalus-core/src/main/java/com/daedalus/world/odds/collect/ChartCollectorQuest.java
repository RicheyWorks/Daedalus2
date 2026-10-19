// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.collect;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_star_chart: the arks' star chart was torn into {@link #FRAGMENTS} pieces and scattered through the salvage
 * crates, one random piece per crate. The supply skiff hauls crates until it sails. The Keeper's counter takes
 * {@link #TRADE_RATE} spare duplicates for any piece you name. Haul at least the Keeper's number (90% with the
 * trade-in) and chart the way home. No wagering.
 */
public final class ChartCollectorQuest {

    public static final int FRAGMENTS = 8;
    public static final int TRADE_RATE = 3;
    public static final double CONFIDENCE = 0.90;
    public static final int MAX_CRATES = 120;

    /** Quest stages. */
    public enum Stage { PLANNING, CHARTED, TORN }

    private final ChartFragments math = new ChartFragments(FRAGMENTS);
    private final int advised = math.smallestCrates(CONFIDENCE, TRADE_RATE, MAX_CRATES);
    private final int advisedNoTrade = math.smallestCrates(CONFIDENCE, 0, MAX_CRATES);
    private Stage stage = Stage.PLANNING;
    private CrateHaul haul;
    private int hauled;

    public Stage stage() {
        return stage;
    }

    /** Crates the Keeper advises with his trade-in. */
    public int advised() {
        return advised;
    }

    /** Crates needed for the same confidence without the trade-in. */
    public int advisedNoTrade() {
        return advisedNoTrade;
    }

    /** Exact chance of a full chart from {@code crates} with the trade-in. */
    public double chance(int crates) {
        return math.completeWithTradeIn(crates, TRADE_RATE);
    }

    /** Hauls {@code crates} on {@code seed}; returns the final stage. */
    public Stage haul(int crates, long seed) {
        if (stage != Stage.PLANNING) {
            throw new IllegalStateException("skiff already sailed: " + stage);
        }
        if (crates < 1 || crates > MAX_CRATES) {
            throw new IllegalArgumentException("haul between 1 and " + MAX_CRATES + ": " + crates);
        }
        hauled = crates;
        haul = CrateHaul.open(FRAGMENTS, crates, new OddsRng(seed));
        stage = haul.full(FRAGMENTS, TRADE_RATE) ? Stage.CHARTED : Stage.TORN;
        return stage;
    }

    /** Fragments traded in at the counter (0 before hauling or if none were needed). */
    public int traded() {
        return haul == null || stage != Stage.CHARTED ? 0 : FRAGMENTS - haul.distinct();
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case PLANNING -> String.format(Locale.ROOT,
                    "Eight pieces, one a crate. Alone you'd want %d crates; bring me spares,"
                            + " three for any piece, and %d gives %.0f%%.",
                    advisedNoTrade, advised, chance(advised) * 100);
            case CHARTED -> String.format(Locale.ROOT, "%d crates, %d pieces found, %d traded at my counter. Charted.",
                    hauled, haul.distinct(), traded());
            case TORN -> String.format(Locale.ROOT,
                    "%d crates, %d pieces and %d spares. Still %d short; the skiff has sailed.", hauled,
                    haul.distinct(), haul.duplicates(), FRAGMENTS - haul.distinct());
        };
    }
}
