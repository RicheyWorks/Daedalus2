// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.boats;

/** Keeper Oriel on the landing beach. */
public final class KeeperBoatLines {
    public static final String GREETING = "Two boats, one pile of cargo. Split it so neither one sits low in the water.";
    public static final String LOADING = "%d crates still on the sand. A carries %d, B carries %d.";
    public static final String READY = "Everything's aboard. Push off when you're happy with it.";
    public static final String LISTING = "She's listing: %d stone between them where %d would do. Shift something.";
    public static final String THANKS = "Both boats riding level. The crossing will be kind to us.";
    public static final String DONE = "Load them like that every landfall.";

    private KeeperBoatLines() {
    }

    /** The line for this landing. */
    public static String line(TwoBoats b) {
        if (b.quest().currentStep() == null) {
            return DONE;
        }
        if (b.last() == TwoBoats.Outcome.LISTING) {
            return String.format(LISTING, b.difference(), b.bestDifference());
        }
        if (b.loaded().isEmpty()) {
            return GREETING;
        }
        int left = b.ashore().size();
        return left == 0 ? READY
                : String.format(LOADING, left, b.weight(TwoBoats.Boat.A), b.weight(TwoBoats.Boat.B));
    }
}
