// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.echo;

/** Keeper Oriel at the mouth of the echo cave. */
public final class KeeperEchoLines {
    public static final String GREETING = "The marks on the wall read \"%s\". Sing them in order, skip what you "
            + "like, but the cave only answers a chant that sounds the same backwards.";
    public static final String NO_ECHO = "\"%s\" does not come back the same. The cave stays silent.";
    public static final String SHORT = "It echoes, but %d notes where %d could. Sing more of the wall.";
    public static final String THANKS = "The whole cave sang it back. That is the longest echo the wall holds.";
    public static final String DONE = "Hush now, the cave is still ringing.";

    private KeeperEchoLines() {
    }

    /** The line for this cave. */
    public static String line(EchoCave c) {
        if (c.quest().currentStep() == null) {
            return DONE;
        }
        if (c.last() == EchoCave.Outcome.NO_ECHO) {
            return String.format(NO_ECHO, c.sung());
        }
        if (c.last() == EchoCave.Outcome.SHORT) {
            return String.format(SHORT, c.sung().length(), c.longest());
        }
        return String.format(GREETING, c.marks());
    }
}
