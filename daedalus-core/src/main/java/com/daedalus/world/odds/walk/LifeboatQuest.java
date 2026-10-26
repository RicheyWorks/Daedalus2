// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.walk;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_lifeboat_drift: after the wreck the lifeboat lies {@link #START} cables off the reef, {@link #HARBOUR} from
 * the harbour lights. The current wins slightly ({@link #WIND} shoreward a watch). Rowing a watch costs one of
 * {@link #RATIONS} biscuit rations and tilts the odds by {@link #TILT}. The Keeper (by lantern) calls when to row.
 * No wagering.
 */
public final class LifeboatQuest {

    public static final int HARBOUR = 10;
    public static final int START = 4;
    public static final double WIND = 0.45;
    public static final double TILT = 0.20;
    public static final int RATIONS = 3;

    /** Quest stages. */
    public enum Stage { ADRIFT, HARBOUR, REEF }

    private final LifeboatDrift table = new LifeboatDrift(HARBOUR, WIND, TILT, RATIONS);
    private Stage stage = Stage.ADRIFT;
    private int cable = START;
    private int rations = RATIONS;
    private int watches;
    private int rowed;

    public Stage stage() {
        return stage;
    }

    public int cable() {
        return cable;
    }

    public int rations() {
        return rations;
    }

    public int watches() {
        return watches;
    }

    /** The Keeper's rowing plan for the rations left, over cables 0..N ('R' row, '.' drift). */
    public String plan() {
        return table.plan(rations);
    }

    /** Exact P(harbour) from here if the crew only drifts. */
    public double driftOnlyChance() {
        return table.chance(cable, 0);
    }

    /** Exact P(harbour) from here on the Keeper's plan. */
    public double bestChance() {
        return table.chance(cable, rations);
    }

    /** Whether the Keeper calls "row" this watch. */
    public boolean adviseRow() {
        return stage == Stage.ADRIFT && table.rows(cable, rations);
    }

    /** One watch: row (spend a ration) or drift, on {@code rng}; returns the new stage. */
    public Stage watch(boolean rowThisWatch, OddsRng rng) {
        if (stage != Stage.ADRIFT) {
            throw new IllegalStateException("voyage over: " + stage);
        }
        if (rowThisWatch && rations == 0) {
            throw new IllegalStateException("no rations left to row");
        }
        double p = WIND;
        if (rowThisWatch) {
            p = table.rowChance();
            rations--;
            rowed++;
        }
        cable += rng.chance(p) ? 1 : -1;
        watches++;
        if (cable >= HARBOUR) {
            stage = Stage.HARBOUR;
        } else if (cable <= 0) {
            stage = Stage.REEF;
        }
        return stage;
    }

    /** Plays the Keeper's plan to the end on {@code seed}; returns the final stage. */
    public Stage followKeeper(long seed) {
        OddsRng rng = new OddsRng(seed);
        while (stage == Stage.ADRIFT) {
            watch(adviseRow(), rng);
        }
        return stage;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case ADRIFT -> String.format(Locale.ROOT,
                    "%d cables to the lights, %d off the reef, %d rations. Drift alone and it's %.0f%%;"
                            + " row when I call and it's %.0f%%. %s",
                    HARBOUR - cable, cable, rations, driftOnlyChance() * 100, bestChance() * 100,
                    adviseRow() ? "Row now." : "Rest the oars.");
            case HARBOUR -> String.format(Locale.ROOT, "Harbour lights after %d watches, %d rowed. Ashore.", watches,
                    rowed);
            case REEF -> String.format(Locale.ROOT, "The reef took her after %d watches, %d rowed. Swim for it.",
                    watches, rowed);
        };
    }
}
