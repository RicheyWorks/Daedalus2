// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.forks;

/** Keeper Oriel at the spring. */
public final class KeeperForkLines {
    public static final String GREETING = "The melt streams fork and meet again across %d pools down to the sea. The "
            + "children want to race paper boats: how many different ways can a boat float from the spring to the sea?";
    public static final String WRONG = "%d? Follow the streams again; where they fork, the ways add up.";
    public static final String THANKS = "That many! Every child can take a different way.";
    public static final String DONE = "Paper boats bob all the way down to the sea.";

    private KeeperForkLines() {
    }

    /** The line for this hillside. */
    public static String line(StreamForks f) {
        if (f.quest().currentStep() == null) {
            return DONE;
        }
        if (f.last() == StreamForks.Outcome.WRONG) {
            return String.format(WRONG, f.named());
        }
        return String.format(GREETING, f.pools());
    }
}
