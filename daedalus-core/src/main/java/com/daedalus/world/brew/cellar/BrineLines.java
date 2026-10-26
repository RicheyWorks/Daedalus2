// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cellar;

/**
 * Aunt Brine keeps the salt pan and the cellar. Lines follow the cellar quest; also listed in STORY.md.
 */
public final class BrineLines {
    public static final String GREETING = "Cloud season's coming. When the Long Dark sets in there's no boats and no "
            + "laying, so whatever's not in a jar by then, you go without. Salt it, smoke it, dry it or pickle it.";
    public static final String METHODS = "That's %d way%s of keeping. Learn three; fresh doesn't count, it's gone in "
            + "a week.";
    public static final String JARS = "Now fill the shelves. %d more jar%s before the dark.";
    public static final String DARK = "Long Dark, day %d. Eat from the shelves, oldest jar first. Soak the salt "
            + "fish or you'll be drinking all night.";
    public static final String WAIT = "%d day%s till the dark. Keep the pan boiling.";
    public static final String MISSED = "The dark's passed and the shelves came up short. Next cloud season, fill "
            + "them sooner.";
    public static final String THANKS = "Five dark days and nobody went hungry. My mother kept the ark's cellar like "
            + "that. Here, take the old brine crock.";
    public static final String DONE = "The light's back. Compost the bad jars into the beds.";

    private BrineLines() {
    }

    /** The line for this cellar state. */
    public static String line(RootCellar c) {
        var step = c.quest().currentStep();
        if (step == null) {
            return DONE;
        }
        long left = step.required() - c.quest().stepCount();
        return switch (c.quest().stepIndex()) {
            case 0 -> c.quest().stepCount() == 0 ? GREETING
                    : String.format(METHODS, c.quest().stepCount(), c.quest().stepCount() == 1 ? "" : "s");
            case 1 -> String.format(JARS, left, left == 1 ? "" : "s");
            default -> c.darkOver() ? MISSED : c.isDark() ? String.format(DARK, c.quest().stepCount() + 1)
                    : String.format(WAIT, c.daysUntilDark(), c.daysUntilDark() == 1 ? "" : "s");
        };
    }
}
