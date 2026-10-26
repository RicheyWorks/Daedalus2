// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.match;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_birth_nights: at the ark muster the Keeper asks how many sailors it takes before two more likely than not
 * share a birth night of the {@link #NIGHTS}-night island year, and how many for two born within a night of each
 * other. You guess both, then a crew of {@link #CREW} is mustered and the lanterns are lit for matching nights. A guess
 * within {@link #SLACK} of the truth earns the Keeper's nod. No wagering.
 */
public final class BirthNightQuest {

    public static final int NIGHTS = 365;
    public static final int CREW = 30;
    public static final int SLACK = 2;
    public static final double EVEN = 0.5;

    /** Quest stages. */
    public enum Stage { GUESSING, MUSTERED }

    private final BirthNightOdds odds = new BirthNightOdds(NIGHTS);
    private final int sameAnswer = odds.smallestCrew(EVEN, 0);
    private final int nearAnswer = odds.smallestCrew(EVEN, 1);
    private Stage stage = Stage.GUESSING;
    private int sameGuess;
    private int nearGuess;
    private CrewMuster muster;

    public Stage stage() {
        return stage;
    }

    /** Smallest crew for an even chance of a shared night. */
    public int sameAnswer() {
        return sameAnswer;
    }

    /** Smallest crew for an even chance of two births within one night. */
    public int nearAnswer() {
        return nearAnswer;
    }

    /** Lodges both guesses and musters the crew on {@code seed}. */
    public Stage guess(int sameNight, int withinOne, long seed) {
        if (stage != Stage.GUESSING) {
            throw new IllegalStateException("crew already mustered");
        }
        if (sameNight < 2 || withinOne < 2 || sameNight > NIGHTS + 1 || withinOne > NIGHTS + 1) {
            throw new IllegalArgumentException("guesses must be in [2, " + (NIGHTS + 1) + "]");
        }
        sameGuess = sameNight;
        nearGuess = withinOne;
        muster = CrewMuster.muster(NIGHTS, CREW, new OddsRng(seed));
        stage = Stage.MUSTERED;
        return stage;
    }

    /** Guesses within the slack (0, 1 or 2). */
    public int nods() {
        if (stage != Stage.MUSTERED) {
            return 0;
        }
        return (Math.abs(sameGuess - sameAnswer) <= SLACK ? 1 : 0) + (Math.abs(nearGuess - nearAnswer) <= SLACK ? 1 : 0);
    }

    /** Whether the mustered crew has a shared night. */
    public boolean crewShares() {
        return muster != null && muster.hasPairWithin(0);
    }

    /** Closest gap between two births in the mustered crew, or -1 before the muster. */
    public int closestGap() {
        return muster == null ? -1 : muster.closestGap();
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case GUESSING -> String.format(Locale.ROOT,
                    "A %d-night year. How many hands before two share a birth night, more likely than not?"
                            + " And within a night of each other?", NIGHTS);
            case MUSTERED -> String.format(Locale.ROOT,
                    "%d for a shared night (%.1f%%), %d within a night (%.1f%%). Thirty mustered: %s, closest %d"
                            + " nights apart (%.0f%% for thirty). %d of 2 nods.",
                    sameAnswer, odds.shareChance(sameAnswer) * 100, nearAnswer, odds.nearChance(nearAnswer, 1) * 100,
                    crewShares() ? "two share a night" : "no shared night", closestGap(), odds.shareChance(CREW) * 100,
                    nods());
        };
    }
}
