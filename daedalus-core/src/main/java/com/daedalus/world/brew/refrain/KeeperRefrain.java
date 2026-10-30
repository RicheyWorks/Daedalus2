// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.refrain;

/** Keeper Oriel with the work song drummers. */
public final class KeeperRefrain {
    public static final String GREETING = "The work song goes %s. How many times does the refrain %s start in it? "
            + "Count the ones that overlap too.";
    public static final String WRONG = "Not %d. Listen again, beat by beat.";
    public static final String NEVER_SUNG = "That refrain is never sung in this song.";
    public static final String THANKS = "That's how often we all shout! The drummers will know.";
    public static final String DONE = "Everyone shouts the refrain right on the beat.";

    private KeeperRefrain() {
    }

    /** The line for this song. */
    public static String line(RefrainCount r) {
        if (r.times() == 0) {
            return NEVER_SUNG;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == RefrainCount.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.song(), r.refrain());
    }
}
