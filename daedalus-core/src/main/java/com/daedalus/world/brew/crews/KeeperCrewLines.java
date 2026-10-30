// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.crews;

/** Keeper Oriel on the fishing quay. */
public final class KeeperCrewLines {
    public static final String GREETING = "%d boats and %d crews, and every crew rows each boat at its own pace. One "
            + "crew to a boat, and the fewest hours on the oars in all.";
    public static final String CLASH = "One crew can't row two boats. Somebody is left on the quay.";
    public static final String COSTLY = "That rota takes %d hours. It can be done in %d.";
    public static final String THANKS = "The fewest hours on the oars. The crews will thank you.";
    public static final String DONE = "The boats are out. Watch for the nets coming in.";

    private KeeperCrewLines() {
    }

    /** The line for this harbour. */
    public static String line(FishingCrews f) {
        if (f.quest().currentStep() == null) {
            return DONE;
        }
        if (f.last() == FishingCrews.Outcome.CLASH) {
            return CLASH;
        }
        if (f.last() == FishingCrews.Outcome.COSTLY) {
            return String.format(COSTLY, f.cost(), f.fewest());
        }
        return String.format(GREETING, f.boats(), f.boats());
    }
}
