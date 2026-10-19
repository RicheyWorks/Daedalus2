// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.fires;

/** Keeper Oriel at the sea-map table. */
public final class KeeperFireLines {
    public static final String GREETING = "Fires on every island, so one can call the others. Each link burns wood by "
            + "the mile. The sea stacks can hold a fire too, if it saves wood.";
    public static final String BUILDING = "%d links lit, %d wood. Not every island can see a fire yet.";
    public static final String READY = "Everyone's joined. Send the signal round.";
    public static final String SMOKY = "It went round, but you burned %d where %d would do. Douse a link and think again.";
    public static final String THANKS = "Every island answered, and the woodpile hardly noticed. Now nobody's ever more "
            + "than a fire away.";
    public static final String DONE = "The fires are banked every night. Anyone can call.";

    private KeeperFireLines() {
    }

    /** The line for this fire state. */
    public static String line(SignalFires s) {
        if (s.quest().currentStep() == null) {
            return DONE;
        }
        if (s.last() == SignalFires.Outcome.SMOKY) {
            return String.format(SMOKY, s.wood(), s.bestWood());
        }
        if (s.lit().isEmpty()) {
            return GREETING;
        }
        return s.joined() ? READY : String.format(BUILDING, s.lit().size(), s.wood());
    }
}
