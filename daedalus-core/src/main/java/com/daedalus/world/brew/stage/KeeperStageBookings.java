// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.stage;

/** Keeper Oriel at the festival stage. */
public final class KeeperStageBookings {
    public static final String GREETING = "The bands ask for the stage: %s (start, end, coins). "
            + "One band at a time. What is the most the stage can earn?";
    public static final String WRONG = "Not %d. Fitting the most bands isn't the same as earning the most coins.";
    public static final String EMPTY = "No band asked for the stage. Nothing to earn.";
    public static final String THANKS = "The most coins! The festival chest is full.";
    public static final String DONE = "The music plays, one band after another.";

    private KeeperStageBookings() {
    }

    /** The line for this stage. */
    public static String line(StageBookings r) {
        if (r.empty()) {
            return EMPTY;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == StageBookings.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.bookings());
    }
}
