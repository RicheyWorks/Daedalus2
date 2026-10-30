// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.mats;

/** Keeper Oriel on the beach. */
public final class KeeperMatLines {
    public static final String GREETING = "%d drying mats laid along the beach, some over each other. How many paces "
            + "of sand do they cover?";
    public static final String MISCOUNT = "You said %d. The mats cover %d paces.";
    public static final String THANKS = "That's the cover. Spread the fish to dry.";
    public static final String DONE = "The fish are drying in the sun.";

    private KeeperMatLines() {
    }

    /** The line for this beach. */
    public static String line(BeachMats b) {
        if (b.quest().currentStep() == null) {
            return DONE;
        }
        if (b.last() == BeachMats.Outcome.MISCOUNT) {
            return String.format(MISCOUNT, b.named(), b.covered());
        }
        return String.format(GREETING, b.mats().size());
    }
}
