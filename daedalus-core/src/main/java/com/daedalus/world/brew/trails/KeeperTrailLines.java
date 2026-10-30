// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.trails;

/** Keeper Oriel at the trail post. */
public final class KeeperTrailLines {
    public static final String GREETING = "%d huts on the hill and trails between them. The healer must walk from hut "
            + "%d to hut %d tonight. Show me the shortest way.";
    public static final String LONG = "That walk is %d. There is one of %d.";
    public static final String BROKEN = "There's no trail along that way.";
    public static final String THANKS = "That's the way. The healer is off with a lantern.";
    public static final String DONE = "The healer knows every short way now.";

    private KeeperTrailLines() {
    }

    /** The line for these trails. */
    public static String line(HillTrails h) {
        if (h.quest().currentStep() == null) {
            return DONE;
        }
        if (h.last() == HillTrails.Outcome.LONG) {
            return String.format(LONG, h.walked(), h.dist(h.from(), h.to()));
        }
        if (h.last() == HillTrails.Outcome.BROKEN) {
            return BROKEN;
        }
        return String.format(GREETING, h.huts(), h.from(), h.to());
    }
}
