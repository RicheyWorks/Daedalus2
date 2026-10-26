// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lofts;

/** Aunt Brine and the linen cupboard. */
public final class BrineLoftLines {
    public static final String GREETING = "Families off the ark, and every loft I air is a set of linen to wash. One "
            + "family to a loft, mind. Someone leaving in the morning frees it for someone coming that day.";
    public static final String HOUSING = "%d famil%s still on the jetty with their bags.";
    public static final String SPRAWL = "%d lofts aired? I could've done it with %d. Shuffle them round.";
    public static final String THANKS = "Everyone under a roof and not a sheet wasted. Their children have been "
            + "showing them the record player all morning.";
    public static final String DONE = "The lofts are aired whenever the ark's in.";

    private BrineLoftLines() {
    }

    /** The line for this loft state. */
    public static String line(GuestLofts g) {
        if (g.quest().currentStep() == null) {
            return DONE;
        }
        if (g.settled() == GuestLofts.Outcome.SPRAWL) {
            return String.format(SPRAWL, g.aired(), g.fewest());
        }
        int left = g.families().size() - g.housed();
        if (g.housed() == 0) {
            return GREETING;
        }
        return String.format(HOUSING, left, left == 1 ? "y" : "ies");
    }
}
