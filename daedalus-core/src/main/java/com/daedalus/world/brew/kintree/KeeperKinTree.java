// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.kintree;

/** Keeper Oriel at the hearth. */
public final class KeeperKinTree {
    public static final String GREETING = "The kin tree lists each islander's parent: %s. "
            + "How many steps apart are islanders %d and %d?";
    public static final String WRONG = "Not %d. Climb only as far as the nearest shared ancestor.";
    public static final String SAME = "That's the same islander twice. No steps at all.";
    public static final String THANKS = "Right! You read the tree like an elder.";
    public static final String DONE = "Branch by branch, the island remembers its own.";

    private KeeperKinTree() {
    }

    /** The line for this tree. */
    public static String line(KinTree r) {
        if (r.same()) {
            return SAME;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == KinTree.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.parents(), r.a(), r.b());
    }
}
