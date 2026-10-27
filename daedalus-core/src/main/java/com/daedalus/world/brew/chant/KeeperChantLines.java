// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chant;

/** Keeper Oriel at the chant circle. */
public final class KeeperChantLines {
    public static final String GREETING = "The chant is %s. The mirror verse is the longest stretch that sings the same "
            + "backwards. Mark where it starts and ends.";
    public static final String SHORT = "That mirrors, but only %d long. One is %d.";
    public static final String BROKEN = "%s doesn't sing the same backwards.";
    public static final String THANKS = "The mirror verse! Sing it both ways.";
    public static final String DONE = "The circle sings the mirror verse.";

    private KeeperChantLines() {
    }

    /** The line for this chant. */
    public static String line(MirrorChant c) {
        if (c.quest().currentStep() == null) {
            return DONE;
        }
        if (c.last() == MirrorChant.Outcome.SHORT) {
            return String.format(SHORT, c.marked().length(), c.longest());
        }
        if (c.last() == MirrorChant.Outcome.BROKEN) {
            return String.format(BROKEN, c.marked());
        }
        return String.format(GREETING, c.chant());
    }
}
