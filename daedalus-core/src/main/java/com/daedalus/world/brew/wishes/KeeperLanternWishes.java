// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.wishes;

/** Keeper Oriel at the lantern rack. */
public final class KeeperLanternWishes {
    public static final String GREETING = "%d lanterns and %d wishes. Each wish has two parts, like 'lantern 1 lit or "
            + "lantern 3 dark', and a villager is happy if either part comes true. Light them so everyone is happy.";
    public static final String UNHAPPY = "Unhappy villagers with that lighting: %d.";
    public static final String IMPOSSIBLE = "These wishes pull against each other. No lighting makes everyone happy.";
    public static final String THANKS = "Every wish granted! Light them up.";
    public static final String DONE = "The lanterns glow and every villager smiles.";

    private KeeperLanternWishes() {
    }

    /** The line for this festival. */
    public static String line(LanternWishes w) {
        if (!w.possible()) {
            return IMPOSSIBLE;
        }
        if (w.quest().currentStep() == null) {
            return DONE;
        }
        if (w.last() == LanternWishes.Outcome.UNHAPPY) {
            return String.format(UNHAPPY, w.unhappy());
        }
        return String.format(GREETING, w.lanterns(), w.wishCount());
    }
}
