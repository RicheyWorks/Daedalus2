// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.ferry;

/** Keeper Oriel on the harbour steps. */
public final class KeeperFerryLines {
    public static final String GREETING = "Isle %d to isle %d, and every ferry charges in shells. Get us home for "
            + "as few as the tide allows.";
    public static final String SAILING = "Isle %d now, %d shells paid.";
    public static final String DEAR = "Home, but %d shells where %d would have done. Try again tomorrow.";
    public static final String NO_ROUTE = "No ferry runs that way home tonight. We stay put.";
    public static final String THANKS = "Home, and not a shell wasted on the way. The purse thanks you.";
    public static final String DONE = "The ferries are tied up. Sleep well.";

    private KeeperFerryLines() {
    }

    /** The line for this crossing. */
    public static String line(FerryCrossing f) {
        if (f.quest().currentStep() == null) {
            return DONE;
        }
        if (f.cheapest() < 0) {
            return NO_ROUTE;
        }
        if (f.last() == FerryCrossing.Outcome.DEAR) {
            return String.format(DEAR, f.paid(), f.cheapest());
        }
        if (f.at() == 0 && f.paid() == 0) {
            return String.format(GREETING, 0, f.isles() - 1);
        }
        return String.format(SAILING, f.at(), f.paid());
    }
}
