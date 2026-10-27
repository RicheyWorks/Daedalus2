// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.gossip;

/** Keeper Oriel at the washing stones. */
public final class KeeperGossip {
    public static final String GREETING = "%d islanders, and news only goes one way from teller to listener. How many "
            + "gossip circles are there, where news from anyone in it reaches everyone else in it?";
    public static final String WRONG = "Not %d. Follow the news round again.";
    public static final String LONE = "News never comes back round here. Everyone is on their own.";
    public static final String THANKS = "That's the count. Now I know who to tell first!";
    public static final String DONE = "The news goes round every circle by supper.";

    private KeeperGossip() {
    }

    /** The line for this village. */
    public static String line(GossipCircles g) {
        if (g.circles() == 0) {
            return LONE;
        }
        if (g.quest().currentStep() == null) {
            return DONE;
        }
        if (g.last() == GossipCircles.Outcome.WRONG) {
            return String.format(WRONG, g.named());
        }
        return String.format(GREETING, g.islanders());
    }
}
