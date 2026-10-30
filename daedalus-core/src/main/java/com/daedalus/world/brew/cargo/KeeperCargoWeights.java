// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cargo;

/** Keeper Oriel on the quay. */
public final class KeeperCargoWeights {
    public static final String GREETING = "The crates on the quay weigh %s. The boat takes any of them, at least one. "
            + "How many different loads could the scale read?";
    public static final String WRONG = "Not %d. Different crates can add up to the same load.";
    public static final String EMPTY = "The quay is empty. No load to weigh.";
    public static final String THANKS = "Every load counted! The trader can't fool us now.";
    public static final String DONE = "The scale creaks, and the boat sails heavy.";

    private KeeperCargoWeights() {
    }

    /** The line for this quay. */
    public static String line(CargoWeights r) {
        if (r.empty()) {
            return EMPTY;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == CargoWeights.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.crates());
    }
}
