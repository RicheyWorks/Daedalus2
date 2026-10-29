// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.pools;

/** Keeper Oriel at the tide pools. */
public final class KeeperPoolLines {
    public static final String GREETING = "%d rocks on the shelf. Rain is coming. Tell me how much water the pools "
            + "will hold, so we know if the crabs stay wet till the tide.";
    public static final String WRONG = "You said %d. The shelf held a different amount. Look again where the tall "
            + "rocks stand.";
    public static final String THANKS = "Exactly right. The crabs will be fine.";
    public static final String DONE = "The pools are full. Mind your step.";

    private KeeperPoolLines() {
    }

    /** The line for this shelf. */
    public static String line(TidePools p) {
        if (p.quest().currentStep() == null) {
            return DONE;
        }
        if (p.last() == TidePools.Outcome.WRONG) {
            return String.format(WRONG, p.guess());
        }
        return String.format(GREETING, p.rocks());
    }
}
