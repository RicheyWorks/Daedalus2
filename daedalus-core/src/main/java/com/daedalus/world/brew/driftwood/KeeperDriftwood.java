// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.driftwood;

/** Keeper Oriel at the woodpile. */
public final class KeeperDriftwood {
    public static final String GREETING = "A driftwood plank %d long, and the trader's shell prices for each length "
            + "of piece. Cut the whole plank for the most shells.";
    public static final String CHEAP = "Those pieces fetch %d shells. Cut another way and they'd fetch %d.";
    public static final String WRONG_LENGTH = "Your pieces don't add up to the whole plank.";
    public static final String NO_BUYERS = "The trader won't give a single shell for any piece. Keep it for firewood.";
    public static final String THANKS = "The best cut! The trader's shells are ours.";
    public static final String DONE = "The pieces are traded and the shells are in the jar.";

    private KeeperDriftwood() {
    }

    /** The line for this plank. */
    public static String line(DriftwoodCuts d) {
        if (d.best() == 0) {
            return NO_BUYERS;
        }
        if (d.quest().currentStep() == null) {
            return DONE;
        }
        if (d.last() == DriftwoodCuts.Outcome.CHEAP) {
            return String.format(CHEAP, d.earned(), d.best());
        }
        if (d.last() == DriftwoodCuts.Outcome.WRONG_LENGTH) {
            return WRONG_LENGTH;
        }
        return String.format(GREETING, d.length());
    }
}
