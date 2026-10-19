// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.exchange;

/**
 * Pell the rope-maker speaks for the neighbours. Lines follow the exchange quest; also listed in STORY.md.
 */
public final class TraderLines {
    public static final String GREETING = "No one's played us a tune since the sky fell. Bring a pressed copy and "
            + "we'll pay in rope, stone, eggs or fish.";
    public static final String MORE = "%d trade%s so far. Ask what we're humming for today; we pay double for that.";
    public static final String WANTED = "Now bring us the tunes we asked for. %d more of those.";
    public static final String THANKS = "Music on every fragment again. Take the good rope; you'll need it for "
            + "those bridges.";
    public static final String DONE = "Come back tomorrow. We'll be humming something new.";
    public static final String REFUSED = "We've heard that one plenty, thanks.";

    private TraderLines() {
    }

    /** The line for this exchange state. */
    public static String line(RecordExchange x) {
        var step = x.quest().currentStep();
        if (step == null) {
            return DONE;
        }
        int idx = x.quest().stepIndex();
        long count = x.quest().stepCount();
        if (idx == 0) {
            return count == 0 ? GREETING : String.format(MORE, count, count == 1 ? "" : "s");
        }
        return String.format(WANTED, step.required() - count);
    }
}
