// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.plots;

/** Keeper Oriel at the berry patch. */
public final class KeeperBerryLines {
    public static final String GREETING = "A patch of %d by %d bushes. Each child may pick one %d by %d square. Where "
            + "is the square with the most berries?";
    public static final String POOR = "That square has %d berries. One has %d.";
    public static final String THANKS = "The richest square. Fill the baskets!";
    public static final String DONE = "Baskets full of berries for the jam.";

    private KeeperBerryLines() {
    }

    /** The line for this patch. */
    public static String line(BerryPatch b) {
        if (b.quest().currentStep() == null) {
            return DONE;
        }
        if (b.last() == BerryPatch.Outcome.POOR) {
            return String.format(POOR, b.picked(), b.richest());
        }
        return String.format(GREETING, b.rows(), b.cols(), b.side(), b.side());
    }
}
