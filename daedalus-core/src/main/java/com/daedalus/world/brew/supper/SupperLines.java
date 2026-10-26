// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.supper;

/**
 * Keeper Oriel, first met at the Seed-Song Spring, hosts beside you. Lines follow the supper quest; also listed in
 * STORY.md.
 */
public final class SupperLines {
    public static final String GREETING = "Everyone's coming, every fragment. Mind where you seat them: some of them "
            + "haven't spoken since the sky fell.";
    public static final String SERVE = "%d plate%s still to go. Ask them what they used to cook on the arks.";
    public static final String PLAY = "Put on a record. %d course%s left; play the tunes they hum.";
    public static final String COLD = "%d guest%s still looking at their plate. A friend beside them, the dish they "
            + "love, or their own tune would do it.";
    public static final String THANKS = "Listen to them. Nine fragments at one table, singing your records. That's the "
            + "island home.";
    public static final String DONE = "Leave the dishes. Sit, the next song's starting.";

    private SupperLines() {
    }

    /** The line for this supper state. */
    public static String line(HomecomingSupper s) {
        var step = s.quest().currentStep();
        if (step == null) {
            return DONE;
        }
        long left = step.required() - s.quest().stepCount();
        return switch (s.quest().stepIndex()) {
            case 0 -> GREETING;
            case 1 -> String.format(SERVE, left, left == 1 ? "" : "s");
            default -> String.format(PLAY, left, left == 1 ? "" : "s");
        };
    }
}
