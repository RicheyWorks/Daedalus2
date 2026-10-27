// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.flags;

/** Keeper Oriel at the flag locker. */
public final class KeeperFlagLines {
    public static final String GREETING = "%d isles, and no two that share a shore may fly the same colour. Dye as "
            + "few cloths as you can.";
    public static final String DYEING = "%d of %d isles flagged so far.";
    public static final String CLASH = "Isles %d and %d share a shore and the same colour. Sailors will be lost.";
    public static final String WASTEFUL = "No clashes, but %d colours where %d would do. Dye is dear.";
    public static final String THANKS = "Every isle its own from its neighbours, and not a pot of dye wasted.";
    public static final String DONE = "The flags are up. Watch them in the wind.";

    private KeeperFlagLines() {
    }

    /** The line for these flags. */
    public static String line(IslandFlags f) {
        if (f.quest().currentStep() == null) {
            return DONE;
        }
        if (f.last() == IslandFlags.Outcome.CLASH) {
            int[] c = f.clash();
            return String.format(CLASH, c[0], c[1]);
        }
        if (f.last() == IslandFlags.Outcome.WASTEFUL) {
            return String.format(WASTEFUL, f.coloursUsed(), f.fewest());
        }
        if (f.flagged() == 0) {
            return String.format(GREETING, f.isles());
        }
        return String.format(DYEING, f.flagged(), f.isles());
    }
}
