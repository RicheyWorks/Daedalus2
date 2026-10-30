// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.namestones;

/** Keeper Oriel at the name stones. */
public final class KeeperNameLines {
    public static final String GREETING = "%d families, and a stone for each. Carving is slow: cut only the start of "
            + "each name, just enough that nobody mistakes one family's stone for another's.";
    public static final String AMBIGUOUS = "The stone for the %s family could belong to another family too.";
    public static final String LONG = "That's %d letters of carving. %d would tell every family apart.";
    public static final String THANKS = "Short and clear. Every family knows its stone.";
    public static final String DONE = "The stones are set along the path.";

    private KeeperNameLines() {
    }

    /** The line for these stones. */
    public static String line(NameStones s) {
        if (s.quest().currentStep() == null) {
            return DONE;
        }
        if (s.last() == NameStones.Outcome.AMBIGUOUS) {
            return String.format(AMBIGUOUS, s.name(s.clash()));
        }
        if (s.last() == NameStones.Outcome.LONG) {
            return String.format(LONG, s.carved(), s.fewest());
        }
        return String.format(GREETING, s.families());
    }
}
