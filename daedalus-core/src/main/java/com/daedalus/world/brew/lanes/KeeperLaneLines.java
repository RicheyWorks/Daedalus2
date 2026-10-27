// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lanes;

/** Keeper Oriel at the harbour gate. */
public final class KeeperLaneLines {
    public static final String GREETING = "The inn's down there, past every stall in town. East or south only, and keep "
            + "the little ones out of the thick of it.";
    public static final String WALKING = "%d people passed so far.";
    public static final String READY = "That's the inn door. Knock.";
    public static final String JOSTLED = "We made it, but through %d people where %d would do. Back up and find the "
            + "quiet lanes.";
    public static final String THANKS = "Through the market and hardly an elbow. Well walked.";
    public static final String DONE = "Supper's on at the inn.";

    private KeeperLaneLines() {
    }

    /** The line for this walk. */
    public static String line(MarketLanes m) {
        if (m.quest().currentStep() == null) {
            return DONE;
        }
        if (m.last() == MarketLanes.Outcome.JOSTLED) {
            return String.format(JOSTLED, m.passed(), m.least());
        }
        if (m.row() == 0 && m.col() == 0) {
            return GREETING;
        }
        return m.atInn() ? READY : String.format(WALKING, m.passed());
    }
}
