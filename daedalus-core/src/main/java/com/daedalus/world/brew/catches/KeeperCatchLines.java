// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.catches;

/** Keeper Oriel at the fish table. */
public final class KeeperCatchLines {
    public static final String GREETING = "%d fish on the table. The cook wants the %d%s smallest for the soup. How long "
            + "is it?";
    public static final String WRONG = "You said %d. The %d%s smallest is %d long.";
    public static final String THANKS = "That's the fish. Into the pot!";
    public static final String DONE = "The fish soup is simmering.";

    private KeeperCatchLines() {
    }

    static String nth(int k) {
        return k % 100 >= 11 && k % 100 <= 13 ? "th" : k % 10 == 1 ? "st" : k % 10 == 2 ? "nd" : k % 10 == 3 ? "rd" : "th";
    }

    /** The line for this catch. */
    public static String line(MiddleCatch c) {
        if (c.quest().currentStep() == null) {
            return DONE;
        }
        if (c.last() == MiddleCatch.Outcome.WRONG) {
            return String.format(WRONG, c.named(), c.rank(), nth(c.rank()), c.kth());
        }
        return String.format(GREETING, c.lengths().size(), c.rank(), nth(c.rank()));
    }
}
