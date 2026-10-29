// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.relay;

/** Keeper Oriel at the first lighthouse. */
public final class KeeperRelayLines {
    public static final String GREETING = "A signal from lighthouse 0 to lighthouse %d, lamp to lamp. A relay is "
            + "only as clear as its haziest sightline, so pick the clearest way.";
    public static final String PASSING = "Lamp %d lit, haziest sightline so far %d.";
    public static final String DIM = "It reached, but its haziest sightline is %d where %d could be. Too faint.";
    public static final String NO_RELAY = "No line of lamps reaches the far light tonight. The signal waits.";
    public static final String THANKS = "Clear across the whole sea. They will see it on the far isle.";
    public static final String DONE = "Let the lamps burn down. Good signalling.";

    private KeeperRelayLines() {
    }

    /** The line for this relay. */
    public static String line(LighthouseRelay r) {
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.clearest() < 0) {
            return NO_RELAY;
        }
        if (r.last() == LighthouseRelay.Outcome.DIM) {
            return String.format(DIM, r.haziest(), r.clearest());
        }
        if (r.at() == 0) {
            return String.format(GREETING, r.lamps() - 1);
        }
        return String.format(PASSING, r.at(), r.haziest());
    }
}
