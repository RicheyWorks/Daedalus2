// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hutfloor;

/** Keeper Oriel in the new hut. */
public final class KeeperHutFloor {
    public static final String GREETING = "A new hut floor, %d rows of %d squares, with posts where you see #. Each "
            + "reed mat covers two squares side by side. How many ways can we cover every bare square?";
    public static final String WRONG = "Not %d. Try laying them out again, row by row.";
    public static final String NO_FIT = "However we lay them, some square stays bare. The mats won't fit this floor.";
    public static final String THANKS = "That many layouts! We'll change the pattern every season.";
    public static final String DONE = "The reed mats lie snug round every post.";

    private KeeperHutFloor() {
    }

    /** The line for this floor. */
    public static String line(HutFloor f) {
        if (f.ways() == 0) {
            return NO_FIT;
        }
        if (f.quest().currentStep() == null) {
            return DONE;
        }
        if (f.last() == HutFloor.Outcome.WRONG) {
            return String.format(WRONG, f.named());
        }
        return String.format(GREETING, f.rows().size(), f.width());
    }
}
