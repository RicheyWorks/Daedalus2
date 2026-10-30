// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.walkways;

/** Keeper Oriel on the marsh. */
public final class KeeperWalkwayLines {
    public static final String GREETING = "%d stilt huts over the marsh. Lay plank walkways so anyone can walk from any "
            + "hut to any other, with as few planks as you can.";
    public static final String BROKEN = "Somebody's hut is still cut off. They'd have to wade.";
    public static final String DEAR = "That takes %d planks. Every hut can be joined with %d.";
    public static final String THANKS = "Every hut joined, and planks to spare. Good work.";
    public static final String DONE = "Mind the gaps between the planks.";

    private KeeperWalkwayLines() {
    }

    /** The line for this marsh. */
    public static String line(HutWalkways h) {
        if (h.quest().currentStep() == null) {
            return DONE;
        }
        if (h.last() == HutWalkways.Outcome.BROKEN) {
            return BROKEN;
        }
        if (h.last() == HutWalkways.Outcome.DEAR) {
            return String.format(DEAR, h.laid(), h.cheapest());
        }
        return String.format(GREETING, h.huts());
    }
}
