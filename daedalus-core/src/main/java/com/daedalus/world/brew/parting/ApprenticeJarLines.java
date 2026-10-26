// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.parting;

/** Aunt Brine and her new cellar apprentice. */
public final class ApprenticeJarLines {
    public static final String GREETING = "Every family wants a jar of home to sail with, and the apprentice has two "
            + "hands. Salt's a day, pickle or smoke two, drying three, per jar. Finish it after they've sailed and it "
            + "just sits on my shelf.";
    public static final String SHORT = "%d families sail with a jar. %d could. Look at who's leaving first.";
    public static final String THANKS = "As many jars as the days allowed, and not one left behind on the shelf. "
            + "That apprentice will do.";
    public static final String DONE = "The shelf's for parting jars now. Every ark that leaves takes a taste of here.";

    private ApprenticeJarLines() {
    }

    /** The line for this shelf state. */
    public static String line(PartingJars p) {
        if (p.quest().currentStep() == null) {
            return DONE;
        }
        if (p.last() == PartingJars.Outcome.SHORT) {
            return String.format(SHORT, p.lastOnTime(), p.best().size());
        }
        return GREETING;
    }
}
