// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.bells;

/** Keeper Oriel in the bell tower. */
public final class KeeperBellLines {
    public static final String GREETING = "%d bells, and each rings on its own beat. They all rang together just now. "
            + "On which beat do they next ring together?";
    public static final String OFFBEAT = "On beat %d not every bell rings.";
    public static final String LATE = "They do ring together on beat %d, but sooner, on beat %d.";
    public static final String THANKS = "Right on the beat. Pull the ropes!";
    public static final String DONE = "The bells ring as one. The whole island hears.";

    private KeeperBellLines() {
    }

    /** The line for this tower. */
    public static String line(BellTower b) {
        if (b.quest().currentStep() == null) {
            return DONE;
        }
        if (b.last() == BellTower.Outcome.OFFBEAT) {
            return String.format(OFFBEAT, b.named());
        }
        if (b.last() == BellTower.Outcome.LATE) {
            return String.format(LATE, b.named(), b.together());
        }
        return String.format(GREETING, b.periods().size());
    }
}
