// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.baskets;

/** Keeper Oriel on the ferry dock. */
public final class KeeperTwinBaskets {
    public static final String GREETING = "The baskets on the dock weigh %s, and each ferry trip carries two that weigh %d together. "
            + "How many pairs could go?";
    public static final String WRONG = "Not %d. A with B is the same pair as B with A.";
    public static final String FEW = "One basket can't make a pair. Nothing to count.";
    public static final String THANKS = "Every pair found! The ferry runs full.";
    public static final String DONE = "Two by two, the baskets cross the water.";

    private KeeperTwinBaskets() {
    }

    /** The line for this dock. */
    public static String line(TwinBaskets r) {
        if (r.few()) {
            return FEW;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == TwinBaskets.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.baskets(), r.load());
    }
}
