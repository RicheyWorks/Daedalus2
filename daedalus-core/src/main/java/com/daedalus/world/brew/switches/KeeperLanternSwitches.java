// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.switches;

/** Keeper Oriel at the harbour switch board. */
public final class KeeperLanternSwitches {
    public static final String GREETING = "The harbour lanterns read %s, and the boats need %s. "
            + "Each switch flips one lantern. What is the fewest flips?";
    public static final String WRONG = "Not %d. Count the lanterns that differ, not the gap between the numbers.";
    public static final String MATCH = "The lanterns already show the signal. No flips needed.";
    public static final String THANKS = "Fewest flips! The boats read us clearly.";
    public static final String DONE = "On, off, on: the harbour speaks in light.";

    private KeeperLanternSwitches() {
    }

    /** The line for this row. */
    public static String line(LanternSwitches r) {
        if (r.match()) {
            return MATCH;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == LanternSwitches.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.row(r.now()), r.row(r.want()));
    }
}
