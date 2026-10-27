// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.netrack;

/** Keeper Oriel on the jetty. */
public final class KeeperNetRack {
    public static final String GREETING = "The rack holds %d nets, and today the fishers ask for %s in that order. "
            + "Any net not on the rack is a trip to the shed. What is the fewest trips?";
    public static final String WRONG = "Not %d. Send back the net that won't be wanted for longest.";
    public static final String ROOMY = "The rack holds every net they want. No choices to make.";
    public static final String THANKS = "Fewest trips! My old legs thank you.";
    public static final String DONE = "The nets come and go and the shed path stays quiet.";

    private KeeperNetRack() {
    }

    /** The line for this rack. */
    public static String line(NetRack r) {
        if (r.roomy()) {
            return ROOMY;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == NetRack.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.slots(), r.asks());
    }
}
