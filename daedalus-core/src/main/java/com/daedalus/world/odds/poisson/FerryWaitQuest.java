// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.poisson;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_ferry_wait: sky ferries reach the dock at random, one every {@link #MEAN_GAP} minutes on average. The Keeper
 * asks how long you will wait if you walk down at a random time. Guess, then wait at the dock. A guess within
 * {@link #SLACK} minutes of the true average earns his nod; the usual "half the gap" guess does not. No wagering.
 */
public final class FerryWaitQuest {

    public static final double MEAN_GAP = 20.0;
    public static final double SLACK = 3.0;
    public static final double LONG_WAIT = 30.0;
    public static final double DOCK_FROM = 200.0;
    public static final double DOCK_SPAN = 400.0;

    /** Quest stages. */
    public enum Stage { GUESSING, BOARDED }

    private final FerryClock clock = new FerryClock(MEAN_GAP);
    private Stage stage = Stage.GUESSING;
    private double guess;
    private FerryDay day;

    public Stage stage() {
        return stage;
    }

    /** Exact average wait from a random moment. */
    public double expectedWait() {
        return clock.expectedWait();
    }

    /** Exact P(waiting more than {@link #LONG_WAIT} minutes). */
    public double longWaitChance() {
        return clock.waitBeyond(LONG_WAIT);
    }

    /** Lodges the guess and walks to the dock at a seeded random minute; returns the final stage. */
    public Stage guess(double minutes, long seed) {
        if (stage != Stage.GUESSING) {
            throw new IllegalStateException("already aboard");
        }
        if (!(minutes >= 0 && minutes <= 600)) {
            throw new IllegalArgumentException("guess must be in [0, 600]: " + minutes);
        }
        guess = minutes;
        OddsRng rng = new OddsRng(seed);
        double arrival = DOCK_FROM + rng.nextDouble() * DOCK_SPAN;
        day = FerryDay.at(MEAN_GAP, arrival, rng);
        stage = Stage.BOARDED;
        return stage;
    }

    /** Whether the guess earned the Keeper's nod. */
    public boolean nod() {
        return stage == Stage.BOARDED && Math.abs(guess - clock.expectedWait()) <= SLACK;
    }

    /** Minutes waited (negative before boarding). */
    public double waited() {
        return day == null ? -1 : day.waited();
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case GUESSING -> String.format(Locale.ROOT,
                    "A ferry every %.0f minutes on average, but no timetable. Walk down any time: how long do you wait?",
                    MEAN_GAP);
            case BOARDED -> String.format(Locale.ROOT,
                    "You waited %.1f minutes in a %.1f-minute gap. Average wait %.0f, not %.0f: you tend to land in the"
                            + " long gaps (they average %.0f). Over %.0f minutes: %.0f%%. %s",
                    day.waited(), day.gap(), clock.expectedWait(), clock.timetableWait(), clock.landedGapMean(),
                    LONG_WAIT, longWaitChance() * 100, nod() ? "Good guess." : "Not my nod.");
        };
    }
}
