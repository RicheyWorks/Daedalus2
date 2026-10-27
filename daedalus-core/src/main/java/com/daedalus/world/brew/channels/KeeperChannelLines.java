// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.channels;

/** Keeper Oriel at the spring sluice. */
public final class KeeperChannelLines {
    public static final String GREETING = "%d basins down the hill, joined by stone channels of different widths. "
            + "Open the sluice to the most water the channels can carry to the cistern, and not a bucket more.";
    public static final String OVERFLOW = "%d buckets an hour? The channels will spill over the fields.";
    public static final String SHORT = "%d buckets an hour is safe, but the channels can carry %d. The village is thirsty.";
    public static final String THANKS = "Full channels, and not a drop spilled. The cistern will fill by evening.";
    public static final String DONE = "Listen to the water running down the hill.";

    private KeeperChannelLines() {
    }

    /** The line for this hillside. */
    public static String line(WaterChannels w) {
        if (w.quest().currentStep() == null) {
            return DONE;
        }
        if (w.last() == WaterChannels.Outcome.OVERFLOW) {
            return String.format(OVERFLOW, w.named());
        }
        if (w.last() == WaterChannels.Outcome.SHORT) {
            return String.format(SHORT, w.named(), w.most());
        }
        return String.format(GREETING, w.basins());
    }
}
