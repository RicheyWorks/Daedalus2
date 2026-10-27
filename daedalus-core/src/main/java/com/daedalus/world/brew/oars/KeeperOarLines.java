// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.oars;

/** Keeper Oriel at the oar pile. */
public final class KeeperOarLines {
    public static final String GREETING = "%d oars in the pile. The new boat's oarlocks span %d: pick two oars that "
            + "together come as close to that as they can without passing it.";
    public static final String OVER = "Together that's %d. Past the span: they'd clash in the middle.";
    public static final String SHORT = "That's %d. A better pair reaches %d.";
    public static final String THANKS = "A fine pair. She'll row straight.";
    public static final String DONE = "The oars are in the locks.";

    private KeeperOarLines() {
    }

    /** The line for this pile. */
    public static String line(TwinOars t) {
        if (t.quest().currentStep() == null) {
            return DONE;
        }
        if (t.last() == TwinOars.Outcome.OVER) {
            return String.format(OVER, t.picked());
        }
        if (t.last() == TwinOars.Outcome.SHORT) {
            return String.format(SHORT, t.picked(), t.best());
        }
        return String.format(GREETING, t.oars(), t.span());
    }
}
