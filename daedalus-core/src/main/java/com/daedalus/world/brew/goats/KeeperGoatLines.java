// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.goats;

/** Keeper Oriel below the goat cliff. */
public final class KeeperGoatLines {
    public static final String GREETING = "A kid is stuck on the cliff, %d ledges down and %d across. The old goat leaps "
            + "two one way and one the other. Get her there in as few leaps as you can, and mind the crumbled ledges.";
    public static final String FELL = "That ledge is crumbled. She'd have slipped. Try another way.";
    public static final String STRAY = "She's still not beside the kid.";
    public static final String LONG = "%d leaps. She could do it in %d.";
    public static final String THANKS = "Mother and kid together again. Listen to them bleat.";
    public static final String DONE = "The goats are grazing on the cliff top.";

    private KeeperGoatLines() {
    }

    /** The line for this cliff. */
    public static String line(GoatLeaps g) {
        if (g.quest().currentStep() == null) {
            return DONE;
        }
        if (g.last() == GoatLeaps.Outcome.FELL) {
            return FELL;
        }
        if (g.last() == GoatLeaps.Outcome.STRAY) {
            return STRAY;
        }
        if (g.last() == GoatLeaps.Outcome.LONG) {
            return String.format(LONG, g.used(), g.fewest());
        }
        return String.format(GREETING, g.rows(), g.cols());
    }
}
