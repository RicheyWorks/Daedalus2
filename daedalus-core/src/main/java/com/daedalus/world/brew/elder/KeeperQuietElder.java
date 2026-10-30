// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.elder;

/** Keeper Oriel at the gathering fire. */
public final class KeeperQuietElder {
    public static final String GREETING = "%d islanders round the fire. One may be the quiet elder: "
            + "everyone knows them, and they know no one by name. Who is it?";
    public static final String WRONG = "Islander %d isn't the quiet elder.";
    public static final String NO_ELDER = "No quiet elder sits at this fire tonight.";
    public static final String THANKS = "The quiet elder! Give them the first cup of tea.";
    public static final String DONE = "The quiet elder sips tea and listens.";

    private KeeperQuietElder() {
    }

    /** The line for this gathering. */
    public static String line(QuietElder q) {
        if (q.elder() == QuietElder.NONE) {
            return NO_ELDER;
        }
        if (q.quest().currentStep() == null) {
            return DONE;
        }
        if (q.last() == QuietElder.Outcome.WRONG) {
            return String.format(WRONG, q.named());
        }
        return String.format(GREETING, q.islanders());
    }
}
