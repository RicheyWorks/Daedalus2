// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.rites;

/** Keeper Oriel with the festival list. */
public final class KeeperRiteLines {
    public static final String GREETING = "%d festival rites, and some must come after others. Of all the orders that "
            + "work, the elders want the one that reads first in the list. What is it?";
    public static final String OUT_OF_ORDER = "Rite %d can't come before rite %d.";
    public static final String NOT_FIRST = "That order works, but %s reads first.";
    public static final String TANGLED = "These rites wait on each other in a circle. No order can work.";
    public static final String THANKS = "That's the order. Ring the start!";
    public static final String DONE = "The rites run in order. The festival begins.";

    private KeeperRiteLines() {
    }

    /** The line for this festival. */
    public static String line(FestivalRites f) {
        if (f.tangled()) {
            return TANGLED;
        }
        if (f.quest().currentStep() == null) {
            return DONE;
        }
        if (f.last() == FestivalRites.Outcome.OUT_OF_ORDER) {
            return String.format(OUT_OF_ORDER, f.broken()[1], f.broken()[0]);
        }
        if (f.last() == FestivalRites.Outcome.NOT_FIRST) {
            return String.format(NOT_FIRST, f.order());
        }
        return String.format(GREETING, f.rites());
    }
}
