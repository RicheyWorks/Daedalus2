// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.causeway;

/** Keeper Oriel at the causeway. */
public final class KeeperCausewayWade {
    public static final String GREETING = "The causeway reads %s, with . for dry stones and ~ for shallows. "
            + "Corner to corner, what is the fewest wet steps?";
    public static final String WRONG = "Not %d. The straight route isn't the driest.";
    public static final String DRY = "Every stone is dry today. No wading at all.";
    public static final String THANKS = "One wet step! My socks are grateful.";
    public static final String DONE = "The tide comes back and the causeway sleeps.";

    private KeeperCausewayWade() {
    }

    /** The line for this causeway. */
    public static String line(CausewayWade r) {
        if (r.dry()) {
            return DRY;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == CausewayWade.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.rows());
    }
}
