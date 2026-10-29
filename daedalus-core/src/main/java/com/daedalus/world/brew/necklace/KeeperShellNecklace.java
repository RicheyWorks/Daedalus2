// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.necklace;

/** Keeper Oriel at the craft table. */
public final class KeeperShellNecklace {
    public static final String GREETING = "The children strung the shells %s. Any unbroken run can be cut as a bracelet. "
            + "How many different bracelets could there be?";
    public static final String WRONG = "Not %d. Two cuts with the same shells in the same order are the same bracelet.";
    public static final String BARE = "There are no shells on this string yet. Nothing to cut.";
    public static final String THANKS = "Every bracelet counted! A hundred tales, and still you count true.";
    public static final String DONE = "The necklace shines, and every bracelet in it.";

    private KeeperShellNecklace() {
    }

    /** The line for this necklace. */
    public static String line(ShellNecklace r) {
        if (r.bare()) {
            return BARE;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == ShellNecklace.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.shells());
    }
}
