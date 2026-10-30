// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hauling;

/** Keeper Oriel at the foot of the hill. */
public final class KeeperHaulLines {
    public static final String GREETING = "%d sacks in a line, and %d days to cart them up the hill in that order. "
            + "Plan it so the heaviest day is as light as it can be. The pony is old.";
    public static final String HEAVY = "One day carries %d. Split it better and no day needs more than %d.";
    public static final String THANKS = "Even days. The pony will make it.";
    public static final String DONE = "The grain is in the loft.";

    private KeeperHaulLines() {
    }

    /** The line for this hill. */
    public static String line(HaulingDays h) {
        if (h.quest().currentStep() == null) {
            return DONE;
        }
        if (h.last() == HaulingDays.Outcome.HEAVY) {
            return String.format(HEAVY, h.heaviest(), h.lightest());
        }
        return String.format(GREETING, h.sacks(), h.days());
    }
}
