// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lowtide;

/** Keeper Oriel on the tidal flats. */
public final class KeeperTideLines {
    public static final String GREETING = "%d hours in the almanac, and the flats take %d hours to cross. Pick the "
            + "hour to set out so the deepest water on the way is as low as it gets.";
    public static final String DEEP = "Setting out at hour %d, the water reaches %d. It never needs to pass %d. Wait "
            + "for a better tide.";
    public static final String THANKS = "Dry boots, or near enough. That was the safest tide.";
    public static final String DONE = "You're across. The tide is coming back in behind you.";

    private KeeperTideLines() {
    }

    /** The line for this almanac. */
    public static String line(LowTideWalk w) {
        if (w.quest().currentStep() == null) {
            return DONE;
        }
        if (w.last() == LowTideWalk.Outcome.DEEP) {
            return String.format(DEEP, w.start(), w.danger(w.start()), w.safest());
        }
        return String.format(GREETING, w.hours(), w.walkHours());
    }
}
