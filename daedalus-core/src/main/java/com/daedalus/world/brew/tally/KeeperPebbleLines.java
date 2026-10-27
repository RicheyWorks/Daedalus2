// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.tally;

/** Keeper Oriel at the pebble game. */
public final class KeeperPebbleLines {
    public static final String GREETING = "%d pebbles in a line. You may only swap two neighbours at a time. How few "
            + "swaps line them up smallest to largest?";
    public static final String MISCOUNT = "You said %d swaps. It takes %d.";
    public static final String THANKS = "Exactly that many. Tally it on the stick!";
    public static final String DONE = "The pebbles stand in order, smallest first.";

    private KeeperPebbleLines() {
    }

    /** The line for this game. */
    public static String line(PebbleLine p) {
        if (p.quest().currentStep() == null) {
            return DONE;
        }
        if (p.last() == PebbleLine.Outcome.MISCOUNT) {
            return String.format(MISCOUNT, p.named(), p.swaps());
        }
        return String.format(GREETING, p.sizes().size());
    }
}
