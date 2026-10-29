// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.parade;

/** Keeper Oriel at the head of the beach. */
public final class KeeperParadeLines {
    public static final String GREETING = "Each lantern a little higher than the one before, front to back, so the ships "
            + "can see us climb. Keep as many walking as that allows.";
    public static final String LINING = "%d walking.";
    public static final String NOT_RISING = "%d walking, but someone's lantern doesn't climb. Sit them out.";
    public static final String DIM = "It climbs, but only %d walk where %d could. Who's sitting out that needn't?";
    public static final String THANKS = "Every lantern higher than the last, and nearly everyone walking. Bright!";
    public static final String DONE = "The parade's done. Lanterns out, off to bed.";

    private KeeperParadeLines() {
    }

    /** The line for this parade. */
    public static String line(LanternParade p) {
        if (p.quest().currentStep() == null) {
            return DONE;
        }
        if (p.last() == LanternParade.Outcome.DIM) {
            return String.format(DIM, p.parade().size(), p.longest());
        }
        if (p.parade().isEmpty()) {
            return GREETING;
        }
        return p.rising() ? String.format(LINING, p.parade().size())
                : String.format(NOT_RISING, p.parade().size());
    }
}
