// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.sweep;

/** Keeper Oriel by the broom shed. */
public final class KeeperSweepersWalk {
    public static final String GREETING = "%d spots and %d sandy paths. Sweep every path exactly once in one walk; "
            + "a swept path must not be walked again.";
    public static final String BROKEN = "You'd have to jump from one path to another there. Walk, don't leap.";
    public static final String MISSED = "Every path once, no more, no less.";
    public static final String NO_WALK = "%d spots have an odd number of paths, or the paths don't all join. No single "
            + "walk can do it.";
    public static final String THANKS = "Every path swept, none twice. The yard shines!";
    public static final String DONE = "The paths are clean, broom back in the shed.";

    private KeeperSweepersWalk() {
    }

    /** The line for this yard. */
    public static String line(SweepersWalk s) {
        if (!s.possible()) {
            return String.format(NO_WALK, s.oddSpots());
        }
        if (s.quest().currentStep() == null) {
            return DONE;
        }
        if (s.last() == SweepersWalk.Outcome.BROKEN) {
            return BROKEN;
        }
        if (s.last() == SweepersWalk.Outcome.MISSED) {
            return MISSED;
        }
        return String.format(GREETING, s.spots(), s.pathCount());
    }
}
