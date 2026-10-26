// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chests;

/** Keeper Oriel on the jetty, beside the open chests. */
public final class KeeperChestLines {
    public static final String GREETING = "One chest a family, and the boat won't take a pound over. Choose what "
            + "you'll miss most.";
    public static final String PACKING = "%d in the chest, %d of %d weight.";
    public static final String HEAVY = "It shuts, but there's a lighter way to carry more of home: %d memory where "
            + "%d would fit. Open it and try again.";
    public static final String THANKS = "Every chest closed warm. They'll unpack the whole island on the far shore.";
    public static final String DONE = "The chests are roped down. The boats can go.";

    private KeeperChestLines() {
    }

    /** The line for this family's chest. */
    public static String line(KeepsakeChests c, String family) {
        if (c.quest().currentStep() == null) {
            return DONE;
        }
        if (c.last() == KeepsakeChests.Outcome.HEAVY) {
            return String.format(HEAVY, c.memory(family), c.bestMemory(family));
        }
        if (c.packed(family).isEmpty()) {
            return GREETING;
        }
        return String.format(PACKING, c.packed(family).size(), c.weight(family), c.capacity(family));
    }
}
