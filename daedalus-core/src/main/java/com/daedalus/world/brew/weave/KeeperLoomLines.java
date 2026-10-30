// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.weave;

/** Keeper Oriel at the loom. */
public final class KeeperLoomLines {
    public static final String GREETING = "A strip of %d threads, and the family pattern is %s. Mark the first place "
            + "the pattern starts, and we'll cut the sash there.";
    public static final String FRAYED = "At thread %d the pattern breaks. It first starts at %d.";
    public static final String MISSING = "That pattern isn't in this strip at all. Weave another.";
    public static final String THANKS = "Clean cut. The sash is yours to wear.";
    public static final String DONE = "The sash is cut. Wear it to the fair.";

    private KeeperLoomLines() {
    }

    /** The line for this loom. */
    public static String line(LoomPattern l) {
        if (l.quest().currentStep() == null) {
            return DONE;
        }
        if (l.last() == LoomPattern.Outcome.FRAYED) {
            return l.first() < 0 ? MISSING : String.format(FRAYED, l.marked(), l.first());
        }
        return String.format(GREETING, l.strip().length(), l.pattern());
    }
}
