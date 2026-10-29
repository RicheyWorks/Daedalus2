// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chantwords;

/** Keeper Oriel at the festival circle. */
public final class KeeperChantWords {
    public static final String GREETING = "The chant runs %s, and the blessing words are %s. "
            + "Counting every place one is sung, overlaps too, how many blessings are there?";
    public static final String WRONG = "Not %d. Count every time a blessing is sung, not just which ones.";
    public static final String SILENT = "No blessing is sung in this chant. Nothing to count.";
    public static final String THANKS = "Every blessing counted! The festival is well begun.";
    public static final String DONE = "The chant fades and the blessings stay.";

    private KeeperChantWords() {
    }

    /** The line for this chant. */
    public static String line(ChantWords r) {
        if (r.silent()) {
            return SILENT;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == ChantWords.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.chant(), r.words());
    }
}
