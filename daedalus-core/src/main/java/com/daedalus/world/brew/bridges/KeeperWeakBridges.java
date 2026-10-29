// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.bridges;

/** Keeper Oriel at the bridge rope store. */
public final class KeeperWeakBridges {
    public static final String GREETING = "%d islets and %d rope bridges. Mark every bridge that, if it snapped, "
            + "would leave someone cut off. Only those get new rope this winter.";
    public static final String MISSED = "You marked %d, but %d bridges would cut someone off.";
    public static final String WRONG = "One you marked has another way round. Save the rope.";
    public static final String SCATTERED = "Some islets have no bridge to the rest at all. Build first, mend later.";
    public static final String THANKS = "Exactly the weak ones. New rope on every one!";
    public static final String DONE = "The weak bridges have fresh rope. No one will be cut off.";

    private KeeperWeakBridges() {
    }

    /** The line for these islets. */
    public static String line(WeakBridges w) {
        if (!w.joined()) {
            return SCATTERED;
        }
        if (w.quest().currentStep() == null) {
            return DONE;
        }
        if (w.last() == WeakBridges.Outcome.MISSED) {
            return String.format(MISSED, w.named(), w.weak().size());
        }
        if (w.last() == WeakBridges.Outcome.WRONG) {
            return WRONG;
        }
        return String.format(GREETING, w.islets(), w.bridgeCount());
    }
}
