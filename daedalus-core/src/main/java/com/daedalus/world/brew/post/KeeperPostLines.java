// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.post;

/** Keeper Oriel on the post boat. */
public final class KeeperPostLines {
    public static final String GREETING = "Harvest letters for %d isles. Call at every one once and bring the boat "
            + "home to isle 0 by the shortest round.";
    public static final String ROWING = "%d isles called at, %d leagues rowed.";
    public static final String MISSED = "Home already? %d isles still wait for their letters.";
    public static final String LONG = "Every letter delivered, but %d leagues where %d would do. My arms ache.";
    public static final String THANKS = "Every isle has its letters, and not a stroke wasted. Fine rowing.";
    public static final String DONE = "The post bag is empty. Rest your oars.";

    private KeeperPostLines() {
    }

    /** The line for this round. */
    public static String line(IslandPost p) {
        if (p.quest().currentStep() == null) {
            return DONE;
        }
        if (p.last() == IslandPost.Outcome.MISSED) {
            return String.format(MISSED, p.isles() - p.called());
        }
        if (p.last() == IslandPost.Outcome.LONG) {
            return String.format(LONG, p.rowed(), p.shortest());
        }
        if (p.called() == 1) {
            return String.format(GREETING, p.isles());
        }
        return String.format(ROWING, p.called(), p.rowed());
    }
}
