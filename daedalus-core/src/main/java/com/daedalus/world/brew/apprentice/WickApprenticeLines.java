// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.apprentice;

/** Old Wick at the lantern board. */
public final class WickApprenticeLines {
    public static final String GREETING = "Four children who want to stay, four masters with a spare bench. Pin them up "
            + "on the lantern board. Mind: if a child and a master both fancy each other over who they've got, they'll "
            + "sort it out themselves, and not kindly.";
    public static final String PINNING = "%d child%s still to pin.";
    public static final String READY = "Board's full. Light the lanterns when you're sure.";
    public static final String UNSTABLE = "%s slipped off to %s's workshop before the lanterns were out. Fix the board.";
    public static final String THANKS = "Not one of them looking over the fence. The families can sail easy now.";
    public static final String DONE = "Apprentices at every bench. The island's got its next keepers.";

    private WickApprenticeLines() {
    }

    /** The line for this board state. */
    public static String line(Apprenticeships a) {
        if (a.quest().currentStep() == null) {
            return DONE;
        }
        if (a.announced() == Apprenticeships.Outcome.UNSTABLE) {
            Apprenticeships.Pair p = a.blockingPairs(a.board()).get(0);
            return String.format(UNSTABLE, p.child(), p.master());
        }
        int left = a.childPrefs().size() - a.board().size();
        if (a.board().isEmpty()) {
            return GREETING;
        }
        return left == 0 ? READY : String.format(PINNING, left, left == 1 ? "" : "ren");
    }
}
