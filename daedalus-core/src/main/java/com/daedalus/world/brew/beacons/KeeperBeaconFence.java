// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.beacons;

/** Keeper Oriel on the headland. */
public final class KeeperBeaconFence {
    public static final String GREETING = "The beacon posts stand at %s. "
            + "One tight rope goes around them all. How many posts does it bend at?";
    public static final String WRONG = "Not %d. Posts inside, or on a straight stretch, don't bend the rope.";
    public static final String FLAT = "The posts stand in one straight line. There's nothing to fence around.";
    public static final String THANKS = "Every corner found! The fence will hold.";
    public static final String DONE = "The rope hums in the wind and the beacons stay lit.";

    private KeeperBeaconFence() {
    }

    /** The line for this headland. */
    public static String line(BeaconFence r) {
        if (r.flat()) {
            return FLAT;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == BeaconFence.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.posts());
    }
}
