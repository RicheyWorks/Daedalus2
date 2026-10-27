// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.applebaskets;

/** Keeper Oriel at the orchard gate. */
public final class KeeperAppleBaskets {
    public static final String GREETING = "%d apples, all alike, and %d baskets that can take any number, even none. "
            + "How many different ways can the apples be shared?";
    public static final String WRONG = "Not %d. The apples are alike: only how many go in each basket matters.";
    public static final String NO_APPLES = "The trees are bare. No apples to share.";
    public static final String THANKS = "Every share counted! The orchard is grateful.";
    public static final String DONE = "Basket by basket, the harvest goes home.";

    private KeeperAppleBaskets() {
    }

    /** The line for this harvest. */
    public static String line(AppleBaskets r) {
        if (r.noApples()) {
            return NO_APPLES;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == AppleBaskets.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.apples(), r.baskets());
    }
}
