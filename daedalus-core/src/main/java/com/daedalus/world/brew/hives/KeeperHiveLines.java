// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hives;

/** Keeper Oriel among the hives. */
public final class KeeperHiveLines {
    public static final String GREETING = "Hives numbered 1 to %d. The beekeepers say a hive is lucky if no smaller "
            + "number but 1 divides it, and 1 itself is not lucky. How many lucky hives are there?";
    public static final String MISCOUNT = "You said %d. There are %d lucky hives.";
    public static final String THANKS = "That's the count. A ribbon on every lucky hive!";
    public static final String DONE = "The lucky hives hum with ribbons on.";

    private KeeperHiveLines() {
    }

    /** The line for this hill. */
    public static String line(LuckyHives h) {
        if (h.quest().currentStep() == null) {
            return DONE;
        }
        if (h.last() == LuckyHives.Outcome.MISCOUNT) {
            return String.format(MISCOUNT, h.named(), h.lucky());
        }
        return String.format(GREETING, h.hives());
    }
}
