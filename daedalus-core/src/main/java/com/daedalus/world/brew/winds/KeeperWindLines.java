// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.winds;

/** Keeper Oriel with the wind almanac. */
public final class KeeperWindLines {
    public static final String GREETING = "%d days in the almanac, fair winds and foul. Pick one unbroken run to "
            + "sail, and make the most of it.";
    public static final String WEAK = "Days %d to %d give %d, but the best run gives %d. Read it again.";
    public static final String THANKS = "The best winds of the season, and we caught every one. Hoist the sail.";
    public static final String DONE = "The almanac is shut. The wind will do the rest.";

    private KeeperWindLines() {
    }

    /** The line for this almanac. */
    public static String line(FairWinds w) {
        if (w.quest().currentStep() == null) {
            return DONE;
        }
        if (w.last() == FairWinds.Outcome.WEAK) {
            return String.format(WEAK, w.from(), w.to(), w.chosenSum(), w.best());
        }
        return String.format(GREETING, w.days());
    }
}
