// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.gauge;

/** Keeper Oriel at the tide gauge. */
public final class KeeperGaugeLines {
    public static final String GREETING = "The gauge logged %d hours of water. The boat goes out at hour %d and back at "
            + "hour %d. How low does the water get while it's out?";
    public static final String WRONG = "You said %d. The water drops to %d.";
    public static final String THANKS = "That's the low. The keel will clear it.";
    public static final String DONE = "The boat came home over the low water safely.";

    private KeeperGaugeLines() {
    }

    /** The line for this log. */
    public static String line(TideGauge g) {
        if (g.quest().currentStep() == null) {
            return DONE;
        }
        if (g.last() == TideGauge.Outcome.WRONG) {
            return String.format(WRONG, g.named(), g.low(g.from(), g.to()));
        }
        return String.format(GREETING, g.hours(), g.from(), g.to());
    }
}
