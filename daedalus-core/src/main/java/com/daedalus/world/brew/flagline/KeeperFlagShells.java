// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.flagline;

/** Keeper Oriel at the flag wall. */
public final class KeeperFlagShells {
    public static final String GREETING = "The shells lie %s. The flag is reds, then whites, then blues. Each move "
            + "swaps two shells. What is the fewest moves?";
    public static final String WRONG = "Not %d. Trade pairs first, then fix the three-way muddles.";
    public static final String ALREADY_FLAG = "These shells already make the flag. Nothing to swap.";
    public static final String THANKS = "Fewest swaps! The flag shells shine on the wall.";
    public static final String DONE = "The flag of shells hangs proud by the meeting yard.";

    private KeeperFlagShells() {
    }

    /** The line for these shells. */
    public static String line(FlagShells f) {
        if (f.fewest() == 0) {
            return ALREADY_FLAG;
        }
        if (f.quest().currentStep() == null) {
            return DONE;
        }
        if (f.last() == FlagShells.Outcome.WRONG) {
            return String.format(WRONG, f.named());
        }
        return String.format(GREETING, f.line());
    }
}
