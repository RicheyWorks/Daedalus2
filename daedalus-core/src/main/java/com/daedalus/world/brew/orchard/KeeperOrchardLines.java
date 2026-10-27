// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.orchard;

/** Keeper Oriel at the orchard gate. */
public final class KeeperOrchardLines {
    public static final String GREETING = "%d trees in the row. Strip any you like, but never two side by side, or "
            + "the bees have nowhere to go. Bring back the most apples.";
    public static final String PICKING = "%d apples in the basket so far.";
    public static final String NEIGHBOURS = "Trees %d and %d stand side by side and both are bare. The bees are cross.";
    public static final String LIGHT = "%d apples where %d could be. Look along the row again.";
    public static final String THANKS = "A full basket, and the bees still have their trees. Well picked.";
    public static final String DONE = "The baskets are in the cellar. Mind the wasps.";

    private KeeperOrchardLines() {
    }

    /** The line for this row. */
    public static String line(OrchardRows o) {
        if (o.quest().currentStep() == null) {
            return DONE;
        }
        if (o.last() == OrchardRows.Outcome.NEIGHBOURS) {
            int[] p = o.neighbours();
            return String.format(NEIGHBOURS, p[0], p[1]);
        }
        if (o.last() == OrchardRows.Outcome.LIGHT) {
            return String.format(LIGHT, o.basket(), o.most());
        }
        if (o.basket() == 0) {
            return String.format(GREETING, o.trees());
        }
        return String.format(PICKING, o.basket());
    }
}
