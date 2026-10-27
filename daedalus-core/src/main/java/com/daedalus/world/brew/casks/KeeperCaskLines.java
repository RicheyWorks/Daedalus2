// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.casks;

/** Keeper Oriel at the landfall spring. */
public final class KeeperCaskLines {
    public static final String GREETING = "The tank takes %d measures, no more, no less. Every cask we haul is a trip up "
            + "the hill, so use as few as you can.";
    public static final String FILLING = "%d of %d in the tank.";
    public static final String READY = "Right to the line. Seal it.";
    public static final String WASTEFUL = "Full, but that was %d casks where %d would do. My knees noticed.";
    public static final String NO_FILL = "No mix of these casks makes %d. We'll top it up by hand at the next spring.";
    public static final String THANKS = "Exact, and hardly a trip wasted. The spring thanks you.";
    public static final String DONE = "The tank's sealed and sweet.";

    private KeeperCaskLines() {
    }

    /** The line for this filling. */
    public static String line(WaterCasks w) {
        if (w.quest().currentStep() == null) {
            return DONE;
        }
        if (w.last() == WaterCasks.Outcome.WASTEFUL) {
            return String.format(WASTEFUL, w.poured().size(), w.fewest());
        }
        if (w.last() == WaterCasks.Outcome.NO_FILL) {
            return String.format(NO_FILL, w.measure());
        }
        if (w.poured().isEmpty()) {
            return String.format(GREETING, w.measure());
        }
        return w.level() == w.measure() ? READY : String.format(FILLING, w.level(), w.measure());
    }
}
