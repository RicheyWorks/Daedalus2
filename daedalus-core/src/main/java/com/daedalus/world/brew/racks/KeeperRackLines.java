// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.racks;

/** Keeper Oriel in the smokehouse. */
public final class KeeperRackLines {
    public static final String GREETING = "%d sides of fish, and every rack holds %d. The fire is small this winter: "
            + "hang the catch on as few racks as you can.";
    public static final String OVERLOAD = "Rack %d is holding too much. It will snap into the fire.";
    public static final String WASTEFUL = "That is %d racks. The catch fits on %d.";
    public static final String THANKS = "As few racks as the catch allows. The smoke will reach every side.";
    public static final String DONE = "The fish are smoking. Smell that.";

    private KeeperRackLines() {
    }

    /** The line for this smokehouse. */
    public static String line(SmokehouseRacks s) {
        if (s.quest().currentStep() == null) {
            return DONE;
        }
        if (s.last() == SmokehouseRacks.Outcome.OVERLOAD) {
            return String.format(OVERLOAD, s.overRack());
        }
        if (s.last() == SmokehouseRacks.Outcome.WASTEFUL) {
            return String.format(WASTEFUL, s.racksUsed(), s.fewest());
        }
        return String.format(GREETING, s.sides(), s.load());
    }
}
