// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.buckets;

/** Keeper Oriel at the brine trough. */
public final class KeeperBucketLines {
    public static final String GREETING = "Two unmarked buckets, %d and %d, and the pickle wants exactly %d of brine. "
            + "Fill, empty and pour between them, in as few moves as you can.";
    public static final String MISSED = "Neither bucket holds %d. The pickle will be too salty or too weak.";
    public static final String LONG = "Right amount, but %d moves. It can be done in %d.";
    public static final String THANKS = "Exactly right, and quick about it. Into the crock it goes.";
    public static final String DONE = "The pickle crock is sealed.";

    private KeeperBucketLines() {
    }

    /** The line for these buckets. */
    public static String line(TwoBuckets t) {
        if (t.quest().currentStep() == null) {
            return DONE;
        }
        if (t.last() == TwoBuckets.Outcome.MISSED) {
            return String.format(MISSED, t.target());
        }
        if (t.last() == TwoBuckets.Outcome.LONG) {
            return String.format(LONG, t.used(), t.fewest());
        }
        return String.format(GREETING, t.bucketA(), t.bucketB(), t.target());
    }
}
