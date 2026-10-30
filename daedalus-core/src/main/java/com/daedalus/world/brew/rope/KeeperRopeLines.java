// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.rope;

/** Keeper Oriel at the harbour rope stall. */
public final class KeeperRopeLines {
    public static final String GREETING = "They pay by the piece here, and not every length is worth the same. Cut the "
            + "whole coil, and cut it to fetch the most.";
    public static final String CUTTING = "%d pieces cut, %d left on the coil.";
    public static final String READY = "All cut. Take it to the stall.";
    public static final String THIN = "That fetched %d where %d was there for the cutting. Splice and try again.";
    public static final String THANKS = "Every bit of that coil sold at its best. We'll eat well tonight.";
    public static final String DONE = "The rope's sold and the purse is full.";

    private KeeperRopeLines() {
    }

    /** The line for this sale. */
    public static String line(RopeMarket r) {
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == RopeMarket.Outcome.THIN) {
            return String.format(THIN, r.value(), r.bestPrice());
        }
        if (r.pieces().isEmpty()) {
            return GREETING;
        }
        return r.left() == 0 ? READY : String.format(CUTTING, r.pieces().size(), r.left());
    }
}
