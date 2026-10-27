// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.watch;

/** Keeper Oriel at the rota board on deck. */
public final class KeeperWatchLines {
    public static final String GREETING = "Somebody stays awake from dusk to dawn, every hour of it. Wake as few as "
            + "you can; they'll need their sleep tomorrow.";
    public static final String ROTA = "%d on the rota. Hour %d has nobody yet.";
    public static final String READY = "Every hour's watched. Call the night.";
    public static final String WEARY = "The night was kept, but you woke %d where %d would do. Let someone sleep.";
    public static final String NO_COVER = "Nobody offered hour %d. We'll take turns at the tiller and say no more "
            + "about it.";
    public static final String THANKS = "Watched all night, and most of the boat slept through it. That's seamanship.";
    public static final String DONE = "The rota's chalked for every night now.";

    private KeeperWatchLines() {
    }

    /** The line for this rota. */
    public static String line(NightWatch w) {
        if (w.quest().currentStep() == null) {
            return DONE;
        }
        if (w.last() == NightWatch.Outcome.WEARY) {
            return String.format(WEARY, w.woken().size(), w.fewest());
        }
        if (w.last() == NightWatch.Outcome.NO_COVER) {
            return String.format(NO_COVER, w.firstUnoffered());
        }
        if (w.woken().isEmpty()) {
            return GREETING;
        }
        int gap = w.firstGap();
        return gap < 0 ? READY : String.format(ROTA, w.woken().size(), gap);
    }
}
