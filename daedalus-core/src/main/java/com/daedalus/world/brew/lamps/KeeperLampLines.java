// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lamps;

/** Keeper Oriel at the fair fence. */
public final class KeeperLampLines {
    public static final String GREETING = "%d fence posts, and every family hangs a lamp along a run of them. The "
            + "fiddler plays by the brightest post. Which post is it?";
    public static final String DIM = "Post %d has %d light. Another post has %d.";
    public static final String THANKS = "That's the spot. I'll fetch the fiddler.";
    public static final String DONE = "The fair is lit. Listen to the fiddle.";

    private KeeperLampLines() {
    }

    /** The line for this fence. */
    public static String line(LampPosts l) {
        if (l.quest().currentStep() == null) {
            return DONE;
        }
        if (l.last() == LampPosts.Outcome.DIM) {
            return String.format(DIM, l.pointed(), l.light(l.pointed()), l.brightest());
        }
        return String.format(GREETING, l.posts());
    }
}
