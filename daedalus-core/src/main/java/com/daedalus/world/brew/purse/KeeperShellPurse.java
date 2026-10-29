// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.purse;

/** Keeper Oriel at the market stall. */
public final class KeeperShellPurse {
    public static final String GREETING = "The stall takes shells worth %s, and the bread costs %d. "
            + "How many different handfuls pay it exactly? Order does not matter.";
    public static final String WRONG = "Not %d. Two shells and one shell is the same handful whichever goes down first.";
    public static final String UNPAYABLE = "No handful of these shells pays that price. Nothing to count.";
    public static final String THANKS = "Every handful counted! The baker is impressed.";
    public static final String DONE = "The shells clink and the bread is paid for.";

    private KeeperShellPurse() {
    }

    /** The line for this purse. */
    public static String line(ShellPurse r) {
        if (r.unpayable()) {
            return UNPAYABLE;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == ShellPurse.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.coins(), r.total());
    }
}
