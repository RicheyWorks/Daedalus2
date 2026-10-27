// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.palms;

/** Keeper Oriel on the shore path. */
public final class KeeperPalmLines {
    public static final String GREETING = "%d palms along the shore path. The climber is on palm %d and wants to hop "
            + "to the first palm further along that stands taller. Which palm is it?";
    public static final String WRONG = "Palm %d isn't the first taller one. It's %s.";
    public static final String THANKS = "That's the one. Up she goes!";
    public static final String DONE = "Coconuts for everyone.";

    private KeeperPalmLines() {
    }

    /** The line for this shore. */
    public static String line(TallPalms p) {
        if (p.quest().currentStep() == null) {
            return DONE;
        }
        if (p.last() == TallPalms.Outcome.WRONG) {
            int n = p.nextTaller(p.asked());
            return String.format(WRONG, p.named(), n == TallPalms.NONE ? "no palm at all" : "palm " + n);
        }
        return String.format(GREETING, p.palms(), p.asked());
    }
}
