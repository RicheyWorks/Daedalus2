// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.tidemarks;

/** Keeper Oriel on the sea wall. */
public final class KeeperTideMarks {
    public static final String GREETING = "The sea wall reads %s, one mark per high tide. "
            + "How many different runs of %d marks are on it?";
    public static final String WRONG = "Not %d. A run that comes back is still one run.";
    public static final String SHORT = "The wall is shorter than the run. Nothing to read.";
    public static final String THANKS = "Every pattern read! I know what the sea is saying.";
    public static final String DONE = "The tide writes and the wall remembers.";

    private KeeperTideMarks() {
    }

    /** The line for this wall. */
    public static String line(TideMarks r) {
        if (r.shortWall()) {
            return SHORT;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == TideMarks.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.marks(), r.len());
    }
}
