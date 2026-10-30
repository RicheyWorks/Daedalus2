// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.splice;

/** Keeper Oriel at the rope walk. */
public final class KeeperSpliceLines {
    public static final String GREETING = "%d rope lengths in a row, each ending in a different thickness. Splice "
            + "neighbours until one rope is left. What is the least work it can take?";
    public static final String HEAVY = "That's %d work. It can be done with %d.";
    public static final String THANKS = "Least work. That's a sailor's splice.";
    public static final String DONE = "One long rope, ready for the boat.";

    private KeeperSpliceLines() {
    }

    /** The line for this rope walk. */
    public static String line(RopeSplicing r) {
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == RopeSplicing.Outcome.HEAVY) {
            return String.format(HEAVY, r.named(), r.least());
        }
        return String.format(GREETING, r.ropes());
    }
}
