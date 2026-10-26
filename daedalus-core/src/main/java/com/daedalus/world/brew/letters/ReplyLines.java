// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.letters;

/**
 * Fisher Dov (G66) runs the ark post now. Lines follow the letters quest; the epilogue line is what a supper guest
 * says once their old friend writes back. Also listed in STORY.md.
 */
public final class ReplyLines {
    public static final String GREETING = "The arks are running again. Seal a jar, write a letter, and I'll see it "
            + "gets there. Mind the long runs: a jar that turns on the way does more harm than no jar at all.";
    public static final String SHIP = "%d more parcel%s to send. Cover the long runs if you've the salt.";
    public static final String WAIT = "%d parcel%s still afloat. The arks are slow; the jars aren't.";
    public static final String REPLY = "Letters come back on the return ark. %d more to wait for.";
    public static final String THANKS = "Letters from every run. The far islands know the homestead's name now.";
    public static final String DONE = "There's always an ark going somewhere. Bring a jar.";
    public static final String EPILOGUE = "A letter came from %s! I thought they'd gone down with the sky.";

    private ReplyLines() {
    }

    /** The line for this post state. */
    public static String line(LettersByArk x) {
        var step = x.quest().currentStep();
        if (step == null) {
            return DONE;
        }
        long left = step.required() - x.quest().stepCount();
        return switch (x.quest().stepIndex()) {
            case 0 -> x.quest().stepCount() == 0 ? GREETING : String.format(SHIP, left, left == 1 ? "" : "s");
            case 1 -> String.format(WAIT, x.afloat().size(), x.afloat().size() == 1 ? "" : "s");
            default -> String.format(REPLY, left);
        };
    }
}
