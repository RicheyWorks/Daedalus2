// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cairns;

/** Keeper Oriel on the hill path. */
public final class KeeperCairnRun {
    public static final String GREETING = "On the walk I found cairns numbered %s, in that order. "
            + "How long is the longest run of consecutive numbers still standing?";
    public static final String WRONG = "Not %d. The order I found them in doesn't matter, only which numbers stand.";
    public static final String NONE = "Every cairn is down. No run to rebuild.";
    public static final String THANKS = "The longest run! We'll rebuild the path along it.";
    public static final String DONE = "Stone by stone, the hill path finds its way.";

    private KeeperCairnRun() {
    }

    /** The line for this walk. */
    public static String line(CairnRun r) {
        if (r.none()) {
            return NONE;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == CairnRun.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.found());
    }
}
