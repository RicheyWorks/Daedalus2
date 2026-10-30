// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.spans;

/** Keeper Oriel at the drum post. */
public final class KeeperDrumLines {
    public static final String GREETING = "%d huts and %d places a drum line could run. Pick lines so a drum at any hut "
            + "is heard at every hut, for the least rope.";
    public static final String DEAR = "That links every hut with %d rope. It can be done with %d.";
    public static final String BROKEN = "Some hut wouldn't hear the drum.";
    public static final String CUT_OFF = "No set of these lines reaches every hut. We need more rope paths.";
    public static final String THANKS = "Least rope, every hut linked. Beat the drum!";
    public static final String DONE = "The drums carry across the whole village.";

    private KeeperDrumLines() {
    }

    /** The line for this village. */
    public static String line(DrumLines d) {
        if (d.cheapest() == DrumLines.NONE) {
            return CUT_OFF;
        }
        if (d.quest().currentStep() == null) {
            return DONE;
        }
        if (d.last() == DrumLines.Outcome.DEAR) {
            return String.format(DEAR, d.picked(), d.cheapest());
        }
        if (d.last() == DrumLines.Outcome.BROKEN) {
            return BROKEN;
        }
        return String.format(GREETING, d.huts(), d.lines().size());
    }
}
