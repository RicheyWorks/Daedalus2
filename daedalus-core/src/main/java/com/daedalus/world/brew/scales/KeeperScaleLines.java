// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.scales;

/** Keeper Oriel at the trade scale. */
public final class KeeperScaleLines {
    public static final String GREETING = "%d treasures and a trade scale that takes %d weight. Load it as close to "
            + "%d as you can without going over.";
    public static final String LIGHT = "That load is %d. You can get to %d.";
    public static final String OVER = "That's %d. The scale tips past %d.";
    public static final String THANKS = "As close as it goes. The trader shakes your hand.";
    public static final String DONE = "The trade is made. Good weight.";

    private KeeperScaleLines() {
    }

    /** The line for this hoard. */
    public static String line(TreasureScales s) {
        if (s.quest().currentStep() == null) {
            return DONE;
        }
        if (s.last() == TreasureScales.Outcome.LIGHT) {
            return String.format(LIGHT, s.loaded(), s.best());
        }
        if (s.last() == TreasureScales.Outcome.OVER) {
            return String.format(OVER, s.loaded(), s.cap());
        }
        return String.format(GREETING, s.weights().size(), s.cap(), s.cap());
    }
}
