// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.crabs;

/** Keeper Oriel at the crab pens. */
public final class KeeperCrabPens {
    public static final String GREETING = "One crab, and every moon each crab becomes %d. After %d moons we share them "
            + "into pens of %d. How many are left over?";
    public static final String WRONG = "Not %d. Square and halve, square and halve.";
    public static final String WASHED_OUT = "Each brood fills the pens exactly. None left over, nothing to count.";
    public static final String THANKS = "Exactly right! The left-over crabs go to the soup pot.";
    public static final String DONE = "The pens are full and the soup is on.";

    private KeeperCrabPens() {
    }

    /** The line for these pens. */
    public static String line(CrabPens c) {
        if (c.washedOut()) {
            return WASHED_OUT;
        }
        if (c.quest().currentStep() == null) {
            return DONE;
        }
        if (c.last() == CrabPens.Outcome.WRONG) {
            return String.format(WRONG, c.named());
        }
        return String.format(GREETING, c.brood(), c.moons(), c.pen());
    }
}
