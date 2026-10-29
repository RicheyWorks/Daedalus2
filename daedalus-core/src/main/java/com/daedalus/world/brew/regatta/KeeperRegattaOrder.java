// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.regatta;

/** Keeper Oriel at the regatta finish. */
public final class KeeperRegattaOrder {
    public static final String GREETING = "The boats started in number order and finished %s. "
            + "How many pairs of boats swapped places?";
    public static final String WRONG = "Not %d. Boats far apart in the finish can have swapped too.";
    public static final String IN_ORDER = "They finished just as they started. Nothing swapped.";
    public static final String THANKS = "Every swap counted! The race judges agree.";
    public static final String DONE = "Sails down, and the harbour cheers every boat.";

    private KeeperRegattaOrder() {
    }

    /** The line for this finish. */
    public static String line(RegattaOrder r) {
        if (r.inOrder()) {
            return IN_ORDER;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == RegattaOrder.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.finish());
    }
}
