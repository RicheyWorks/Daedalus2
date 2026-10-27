// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.doors;

/** Keeper Oriel at the paint pots. */
public final class KeeperLuckyDoors {
    public static final String GREETING = "Doors numbered 1 to %d. A door is lucky when its digits add up to %d. How "
            + "many lucky doors get a painted shell?";
    public static final String WRONG = "Not %d. Count again, digit by digit.";
    public static final String NO_LUCK = "No door on this street adds up to that. No shells to paint.";
    public static final String THANKS = "That many lucky doors! Fetch the paint.";
    public static final String DONE = "Every lucky door wears a painted shell.";

    private KeeperLuckyDoors() {
    }

    /** The line for this street. */
    public static String line(LuckyDoors d) {
        if (d.lucky() == 0) {
            return NO_LUCK;
        }
        if (d.quest().currentStep() == null) {
            return DONE;
        }
        if (d.last() == LuckyDoors.Outcome.WRONG) {
            return String.format(WRONG, d.named());
        }
        return String.format(GREETING, d.doors(), d.luck());
    }
}
