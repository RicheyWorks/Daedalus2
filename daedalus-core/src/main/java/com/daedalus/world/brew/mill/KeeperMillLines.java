// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.mill;

/** Keeper Oriel at the windmill. */
public final class KeeperMillLines {
    public static final String GREETING = "%d sacks of grain. The stone grinds two at a time into one, and every "
            + "pound in the pair is work. Grind them all into one with the least work.";
    public static final String GRINDING = "%d sacks left, %d work so far.";
    public static final String HEAVY = "One sack, but %d work where %d would do. The sails are tired.";
    public static final String THANKS = "One sack of flour, and the mill barely broke a sweat.";
    public static final String DONE = "The sails are furled. Flour on your nose.";

    private KeeperMillLines() {
    }

    /** The line for this mill. */
    public static String line(GrainMill m) {
        if (m.quest().currentStep() == null) {
            return DONE;
        }
        if (m.last() == GrainMill.Outcome.HEAVY) {
            return String.format(HEAVY, m.work(), m.least());
        }
        if (m.work() == 0) {
            return String.format(GREETING, m.sacks().size());
        }
        return String.format(GRINDING, m.sacks().size(), m.work());
    }
}
