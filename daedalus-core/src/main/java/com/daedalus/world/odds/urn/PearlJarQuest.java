// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.urn;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_pearl_jar: the Keeper's jar starts with one white and one black pearl; each pearl drawn goes back with
 * another of its colour. {@link #DRAWS} draws are made. Before the draws you name a band of the final white share
 * (one of {@link #BANDS} equal bands); the Keeper shows the exact chance of each band first. No wagering.
 */
public final class PearlJarQuest {

    public static final int DRAWS = 20;
    public static final int BANDS = 3;

    /** Quest stages. */
    public enum Stage { CHOOSING, RIGHT_BAND, WRONG_BAND }

    private final PolyaUrn urn = new PolyaUrn(1, 1, 1);
    private Stage stage = Stage.CHOOSING;
    private int chosen = -1;
    private int whites = -1;

    public Stage stage() {
        return stage;
    }

    /** Exact chance the final white share lands in band {@code band} (0 = lowest third). */
    public double bandChance(int band) {
        checkBand(band);
        double[] p = urn.whiteCounts(DRAWS);
        double sum = 0;
        for (int w = 0; w <= DRAWS; w++) {
            if (bandOf(w) == band) {
                sum += p[w];
            }
        }
        return sum;
    }

    /** The band holding a final count of {@code w} white draws (share (1 + w) / (2 + DRAWS)). */
    public static int bandOf(int w) {
        double share = (1.0 + w) / (2.0 + DRAWS);
        return Math.min(BANDS - 1, (int) Math.floor(share * BANDS));
    }

    /** White draws after the quest (-1 before). */
    public int whites() {
        return whites;
    }

    /** Names {@code band} and makes the draws on {@code seed}; returns the final stage. */
    public Stage choose(int band, long seed) {
        if (stage != Stage.CHOOSING) {
            throw new IllegalStateException("the pearls are drawn");
        }
        checkBand(band);
        chosen = band;
        whites = PearlDraws.draw(urn, DRAWS, new OddsRng(seed));
        stage = bandOf(whites) == band ? Stage.RIGHT_BAND : Stage.WRONG_BAND;
        return stage;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case CHOOSING -> String.format(Locale.ROOT,
                    "One white, one black, and each pearl brings a twin. After %d draws: lowest third %.0f%%,"
                            + " middle %.0f%%, top %.0f%%. Name your third.",
                    DRAWS, bandChance(0) * 100, bandChance(1) * 100, bandChance(2) * 100);
            case RIGHT_BAND -> String.format(Locale.ROOT, "%d white of %d. Third %d, as you said.", whites, DRAWS,
                    chosen + 1);
            case WRONG_BAND -> String.format(Locale.ROOT, "%d white of %d: third %d, not your %d. The jar remembers"
                    + " its first pearls.", whites, DRAWS, bandOf(whites) + 1, chosen + 1);
        };
    }

    private static void checkBand(int band) {
        if (band < 0 || band >= BANDS) {
            throw new IllegalArgumentException("band must be in [0, " + (BANDS - 1) + "]: " + band);
        }
    }
}
