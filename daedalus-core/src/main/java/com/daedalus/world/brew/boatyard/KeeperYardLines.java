// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.boatyard;

/** Keeper Oriel in the boatyard. */
public final class KeeperYardLines {
    public static final String GREETING = "%d jobs on the yard board, and some must wait for others. Jobs with nothing "
            + "to wait on can run side by side. What is the soonest day the new boat can launch?";
    public static final String EARLY = "Day %d? The hull would still be on the trestles. It can't be done that soon.";
    public static final String LATE = "Day %d is safe, but the boat could launch on day %d. Don't keep it ashore.";
    public static final String THANKS = "Right to the day. I'll tell the crews to ready the slipway.";
    public static final String DONE = "The new boat is launched. Hear the cheer from the quay.";

    private KeeperYardLines() {
    }

    /** The line for this yard. */
    public static String line(Boatyard y) {
        if (y.quest().currentStep() == null) {
            return DONE;
        }
        if (y.last() == Boatyard.Outcome.EARLY) {
            return String.format(EARLY, y.named());
        }
        if (y.last() == Boatyard.Outcome.LATE) {
            return String.format(LATE, y.named(), y.launchDay());
        }
        return String.format(GREETING, y.jobs());
    }
}
