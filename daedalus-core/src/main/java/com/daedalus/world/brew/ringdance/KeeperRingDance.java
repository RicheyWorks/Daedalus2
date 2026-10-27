// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.ringdance;

/** Keeper Oriel by the dancing ground. */
public final class KeeperRingDance {
    public static final String GREETING = "%d dancers in a ring, crowns %s. Each holds a ribbon with one partner in "
            + "the other crown, and no ribbons may cross. How many ways can they pair up?";
    public static final String WRONG = "Not %d. Count the ways again.";
    public static final String NO_WAY = "However they try, some ribbon crosses or joins two of the same crown.";
    public static final String THANKS = "That many dances! We'll try one each night of the festival.";
    public static final String DONE = "The ribbons swirl and never tangle.";

    private KeeperRingDance() {
    }

    /** The line for this ring. */
    public static String line(RingDance r) {
        if (r.ways() == 0) {
            return NO_WAY;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == RingDance.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.dancers(), r.crowns());
    }
}
