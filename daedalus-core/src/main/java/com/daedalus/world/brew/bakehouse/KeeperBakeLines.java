// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.bakehouse;

/** Keeper Oriel at the bakehouse door. */
public final class KeeperBakeLines {
    public static final String GREETING = "%d harvest loaves. One kneading table, one oven, and every loaf is "
            + "kneaded before it bakes. Choose the order that has them all out soonest.";
    public static final String QUEUED = "%d of %d loaves in the queue.";
    public static final String LATE = "All baked by hour %d, but hour %d was possible. The feast is waiting.";
    public static final String THANKS = "Every loaf out of the oven at the first possible hour. Smell that.";
    public static final String DONE = "The oven is cooling. Tear off a crust.";

    private KeeperBakeLines() {
    }

    /** The line for this bakehouse. */
    public static String line(Bakehouse b) {
        if (b.quest().currentStep() == null) {
            return DONE;
        }
        if (b.last() == Bakehouse.Outcome.LATE) {
            return String.format(LATE, b.finish(), b.soonest());
        }
        if (b.queued() == 0) {
            return String.format(GREETING, b.loaves());
        }
        return String.format(QUEUED, b.queued(), b.loaves());
    }
}
