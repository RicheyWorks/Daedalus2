// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.vote;

/** Keeper Oriel at the voting jar. */
public final class KeeperVoteLines {
    public static final String GREETING = "%d shells in the voting jar, each marked with a choice. A choice wins only "
            + "with more than half the shells. Which choice wins, or does none?";
    public static final String WRONG = "Not so. %s";
    public static final String WINNER = "Choice %d has more than half.";
    public static final String NO_WINNER = "No choice has more than half. We vote again.";
    public static final String THANKS = "That's the count. The village has spoken.";
    public static final String DONE = "The vote is settled.";

    private KeeperVoteLines() {
    }

    /** The truth about this vote. */
    static String truth(VillageVote v) {
        return v.majority() == VillageVote.NONE ? NO_WINNER : String.format(WINNER, v.majority());
    }

    /** The line for this vote. */
    public static String line(VillageVote v) {
        if (v.quest().currentStep() == null) {
            return DONE;
        }
        if (v.last() == VillageVote.Outcome.WRONG) {
            return String.format(WRONG, truth(v));
        }
        return String.format(GREETING, v.shells().size());
    }
}
