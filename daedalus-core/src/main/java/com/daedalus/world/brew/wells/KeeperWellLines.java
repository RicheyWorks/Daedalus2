// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.wells;

/** Keeper Oriel by the wells. */
public final class KeeperWellLines {
    public static final String GREETING = "%d wells and %d clay pipes laid between them. Wells joined by any run of "
            + "pipe share their water. How many separate groups are left?";
    public static final String WRONG = "You count %d. Walk the pipes again: some join wells that were already joined.";
    public static final String THANKS = "That's the count. Now we know which wells to watch in a dry spell.";
    public static final String DONE = "The wells are mapped. Drink up.";

    private KeeperWellLines() {
    }

    /** The line for these wells. */
    public static String line(WellPipes w) {
        if (w.quest().currentStep() == null) {
            return DONE;
        }
        if (w.last() == WellPipes.Outcome.WRONG) {
            return String.format(WRONG, w.named());
        }
        return String.format(GREETING, w.wells(), w.pipeCount());
    }
}
