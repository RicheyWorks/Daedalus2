// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.nets;

/** Keeper Oriel on the net loft. */
public final class KeeperNetLines {
    public static final String GREETING = "%d menders, %d torn nets, and each mender knows only some knots. One net "
            + "each, and mend as many as we can before the tide.";
    public static final String CANT_KNOT = "Mender %d does not know net %d's knot. Pick another.";
    public static final String FEW = "%d nets mended where %d could be. Shuffle the menders.";
    public static final String THANKS = "Every net that could be mended is mended. The boats go out at dawn.";
    public static final String DONE = "The nets are drying. Off to the fire.";

    private KeeperNetLines() {
    }

    /** The line for this loft. */
    public static String line(NetMending n) {
        if (n.quest().currentStep() == null) {
            return DONE;
        }
        if (n.last() == NetMending.Outcome.CANT_KNOT) {
            int[] r = n.refused();
            return String.format(CANT_KNOT, r[0], r[1]);
        }
        if (n.last() == NetMending.Outcome.FEW) {
            return String.format(FEW, n.assigned(), n.most());
        }
        return String.format(GREETING, n.menders(), n.nets());
    }
}
