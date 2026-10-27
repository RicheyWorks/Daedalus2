// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.feasts;

/** Keeper Oriel with the village hall book. */
public final class KeeperFeastLines {
    public static final String GREETING = "%d families want the hall for their harvest feast, and it holds one at "
            + "a time. Book the feasts that bring the most cheer.";
    public static final String OVERLAP = "Feasts %d and %d both want the hall at once. Strike one.";
    public static final String DIM = "%d cheer booked where %d could be. Look at the book again.";
    public static final String THANKS = "The hall never stood empty when it could have rung. Best harvest in years.";
    public static final String DONE = "The hall is swept. Save me some pie.";

    private KeeperFeastLines() {
    }

    /** The line for this hall book. */
    public static String line(HarvestFeasts h) {
        if (h.quest().currentStep() == null) {
            return DONE;
        }
        if (h.last() == HarvestFeasts.Outcome.OVERLAP) {
            int[] c = h.overlap();
            return String.format(OVERLAP, c[0], c[1]);
        }
        if (h.last() == HarvestFeasts.Outcome.DIM) {
            return String.format(DIM, h.bookedCheer(), h.most());
        }
        return String.format(GREETING, h.feasts());
    }
}
