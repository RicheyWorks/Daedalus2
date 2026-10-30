// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chores;

/** Keeper Oriel at the village hall. */
public final class KeeperChoreDays {
    public static final String GREETING = "%d chores before the festival, and some must wait: %s. "
            + "Everyone works at once. What is the fewest days?";
    public static final String WRONG = "Not %d. Chores with nothing between them can share a day.";
    public static final String TANGLED = "These chores wait on each other in a loop. They can never be done.";
    public static final String THANKS = "Fewest days! The festival can start early.";
    public static final String DONE = "Swept, set and lit, one layer at a time.";

    private KeeperChoreDays() {
    }

    /** The line for this list. */
    public static String line(ChoreDays r) {
        if (r.tangled()) {
            return TANGLED;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == ChoreDays.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.chores(), r.rules());
    }
}
