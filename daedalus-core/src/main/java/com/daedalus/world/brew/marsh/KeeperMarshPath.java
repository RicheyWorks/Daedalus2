// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.marsh;

/** Keeper Oriel at the marsh edge. */
public final class KeeperMarshPath {
    public static final String GREETING = "The marsh reads %s, with . for tussocks and ~ for pools. "
            + "From the near corner to the far corner, what is the fewest steps?";
    public static final String WRONG = "Not %d. The pools won't let you walk a straight line.";
    public static final String SUNK = "The pools cut off the far corner. No path to count.";
    public static final String THANKS = "Fewest steps! My boots are barely wet.";
    public static final String DONE = "The reeds are cut and the tussocks remember your path.";

    private KeeperMarshPath() {
    }

    /** The line for this marsh. */
    public static String line(MarshPath r) {
        if (r.sunk()) {
            return SUNK;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == MarshPath.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.rows());
    }
}
