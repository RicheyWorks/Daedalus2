// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.concert;

/** Old Wick and the audience at the Graduation Concert. */
public final class ConcertLines {
    public static final String GREETING = "Five songs from the children, then all of us on the island song. Mind the "
            + "keys: every jump between them loses the crowd a little.";
    public static final String WARMTH = "The green is at %d. %d more solo%s before the choir.";
    public static final String READY = "That's the solos. Bring in the choir.";
    public static final String CHEER = "They're on their feet! The whole green is singing it back.";
    public static final String ROUGH = "Too many jumps; they lost the thread. Same time tomorrow, smoother this time.";
    public static final String THANKS = "When I was their age the arks were still flying. Tonight it felt like they "
            + "never left.";
    public static final String DONE = "The children want to play the harbour next. Can't stop them now.";

    private ConcertLines() {
    }

    /** The line for this concert state. */
    public static String line(GraduationConcert c) {
        if (c.quest().currentStep() == null) {
            return DONE;
        }
        if (c.result() != null) {
            return c.result() == GraduationConcert.Outcome.CHEERED ? CHEER : ROUGH;
        }
        int left = GraduationConcert.SOLOS - c.setList().size();
        if (left == 0) {
            return READY;
        }
        if (c.setList().isEmpty()) {
            return GREETING;
        }
        return String.format(WARMTH, c.warmth(), left, left == 1 ? "" : "s");
    }
}
