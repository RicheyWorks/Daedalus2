// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.verse;

/** Keeper Oriel by the carved stern board. */
public final class KeeperVerseLines {
    public static final String GREETING = "They're singing \"%s\". The stern says \"%s\". Mend it gently; every change "
            + "is one more thing for small heads to unlearn.";
    public static final String MENDING = "\"%s\" now, after %d changes.";
    public static final String READY = "That's the carving, letter for letter. Sing it.";
    public static final String ROUGH = "Right words, but %d changes where %d would do. Start over and go lighter.";
    public static final String THANKS = "That's how the verse went when the boat was built. Well mended.";
    public static final String DONE = "They'll sing it right on every shore now.";

    private KeeperVerseLines() {
    }

    /** The line for this verse. */
    public static String line(VerseMend v) {
        if (v.quest().currentStep() == null) {
            return DONE;
        }
        if (v.last() == VerseMend.Outcome.ROUGH) {
            return String.format(ROUGH, v.changes(), v.fewest());
        }
        if (v.changes() == 0) {
            return String.format(GREETING, v.sung(), v.carved());
        }
        return v.current().equals(v.carved()) ? READY : String.format(MENDING, v.current(), v.changes());
    }
}
