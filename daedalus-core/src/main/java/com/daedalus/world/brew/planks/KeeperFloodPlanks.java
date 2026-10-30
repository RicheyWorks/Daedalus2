// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.planks;

/** Keeper Oriel on the floating dock. */
public final class KeeperFloodPlanks {
    public static final String GREETING = "The dock has %d planks, and the floods were %s (first plank, last plank, hands of rise). "
            + "How high is the highest plank?";
    public static final String WRONG = "Not %d. Floods over different planks don't stack.";
    public static final String CALM = "No floods this season. Every plank sits level.";
    public static final String THANKS = "Right! I'll tie the boats to that one.";
    public static final String DONE = "The tide rises and falls, and the dock rides it.";

    private KeeperFloodPlanks() {
    }

    /** The line for this dock. */
    public static String line(FloodPlanks r) {
        if (r.calm()) {
            return CALM;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == FloodPlanks.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.planks(), r.floods());
    }
}
