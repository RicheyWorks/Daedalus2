// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.round;

/** Fisher Dov on the jetty, and the gulls. */
public final class DovRoundLines {
    public static final String GREETING = "A round for the ark? One starts, the next comes in a few beats behind, "
            + "a third or a fifth up. Get it wrong and the gulls join in.";
    public static final String REHEARSE = "%d more go%s on the green before the ark's due.";
    public static final String SWEET = "Hear that? The gulls have gone quiet.";
    public static final String FAIR = "Close. Some of it rubbed. Try another entry.";
    public static final String SOUR = "The gulls are louder than you. Different beat, different interval.";
    public static final String READY = "Ark's on the horizon. Three voices at least, and make it sweet.";
    public static final String THANKS = "The far-island kids on that ark sang it back to you. First time I've "
            + "heard two islands in one song.";
    public static final String DONE = "Every ark gets a round now. The gulls have learned to wait.";

    private DovRoundLines() {
    }

    /** The line for this round state. */
    public static String line(HarbourRound r) {
        var step = r.quest().currentStep();
        if (step == null) {
            return DONE;
        }
        if (r.last() == HarbourRound.Outcome.SOUR) {
            return SOUR;
        }
        if (r.quest().stepIndex() == 0) {
            if (r.last() == null) {
                return GREETING;
            }
            long left = step.required() - r.quest().stepCount();
            return r.last() == HarbourRound.Outcome.FAIR ? FAIR : String.format(REHEARSE, left, left == 1 ? "" : "es");
        }
        return r.last() == HarbourRound.Outcome.FAIR ? FAIR : READY;
    }
}
