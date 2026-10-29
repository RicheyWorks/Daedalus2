// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.seawall;

/** Keeper Oriel on the sea wall. */
public final class KeeperWallLines {
    public static final String GREETING = "%d stones along the sea wall, all different heights. Cut one storm board "
            + "to sit flush on them, as big as it can be, before winter.";
    public static final String OVERHANG = "A board %d high over stones %d to %d sticks up past stone %d. The wind "
            + "will rip it off.";
    public static final String SMALL = "It fits, but covers %d where %d could be covered. Cut a bigger one.";
    public static final String THANKS = "Flush on the stones and as big as the wall allows. Let winter come.";
    public static final String DONE = "The board is nailed up. Listen to the waves.";

    private KeeperWallLines() {
    }

    /** The line for this wall. */
    public static String line(SeaWall w) {
        if (w.quest().currentStep() == null) {
            return DONE;
        }
        if (w.last() == SeaWall.Outcome.OVERHANG) {
            return String.format(OVERHANG, w.boardHeight(), w.from(), w.to(), w.lowStone());
        }
        if (w.last() == SeaWall.Outcome.SMALL) {
            return String.format(SMALL, w.boardArea(), w.largest());
        }
        return String.format(GREETING, w.stones());
    }
}
