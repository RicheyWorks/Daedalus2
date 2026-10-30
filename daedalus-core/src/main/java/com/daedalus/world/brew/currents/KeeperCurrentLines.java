// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.currents;

/** Keeper Oriel at the harbour chart. */
public final class KeeperCurrentLines {
    public static final String GREETING = "%d coves. Rowing costs effort, but some currents carry you and give it back. "
            + "Sail from cove 0 to cove %d for the least effort.";
    public static final String COSTLY = "That sail costs %d. One costs %d.";
    public static final String BROKEN = "No current runs that way.";
    public static final String WHIRLPOOL = "Those currents circle forever. Nobody sails into a whirlpool.";
    public static final String THANKS = "Least effort. The rowers will thank you.";
    public static final String DONE = "The boat rides the currents home.";

    private KeeperCurrentLines() {
    }

    /** The line for this sea. */
    public static String line(SeaCurrents s) {
        if (s.whirlpool()) {
            return WHIRLPOOL;
        }
        if (s.quest().currentStep() == null) {
            return DONE;
        }
        if (s.last() == SeaCurrents.Outcome.COSTLY) {
            return String.format(COSTLY, s.sailed(), s.cost(s.to()));
        }
        if (s.last() == SeaCurrents.Outcome.BROKEN) {
            return BROKEN;
        }
        return String.format(GREETING, s.coves(), s.to());
    }
}
