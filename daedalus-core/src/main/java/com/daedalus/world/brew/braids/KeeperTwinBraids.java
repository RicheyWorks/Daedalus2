// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.braids;

/** Keeper Oriel at the braiding bench. */
public final class KeeperTwinBraids {
    public static final String GREETING = "Two braids, %s and %s. Name the longest run of beads that shows up in both, "
            + "in the same order. The beads needn't touch.";
    public static final String SHORT = "Those %d beads are in both braids, but a run of %d is there too.";
    public static final String NOT_SHARED = "That run isn't in both braids in that order.";
    public static final String NO_COMMON = "These braids share no bead at all. Nothing to match.";
    public static final String THANKS = "The longest shared run. The twin braids will hang together!";
    public static final String DONE = "The twin braids hang side by side over the door.";

    private KeeperTwinBraids() {
    }

    /** The line for these braids. */
    public static String line(TwinBraids b) {
        if (b.longest() == 0) {
            return NO_COMMON;
        }
        if (b.quest().currentStep() == null) {
            return DONE;
        }
        if (b.last() == TwinBraids.Outcome.SHORT) {
            return String.format(SHORT, b.named(), b.longest());
        }
        if (b.last() == TwinBraids.Outcome.NOT_SHARED) {
            return NOT_SHARED;
        }
        return String.format(GREETING, b.left(), b.right());
    }
}
