// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lamplight;

/** Keeper Oriel at the oil shed. */
public final class KeeperLamplighter {
    public static final String GREETING = "%d lamp posts in a ring, each with a little oil left out. Tell me the first "
            + "post where the lamplighter can start and walk the whole ring without his can running dry.";
    public static final String LATER = "Post %d works, but post %d works too and comes first.";
    public static final String DRY = "From post %d his can runs dry before the ring is done.";
    public static final String SHORT = "The ring burns more oil than the posts hold. No start will do.";
    public static final String THANKS = "Post %d it is. Every lamp lit, can never empty!";
    public static final String DONE = "The lamps glow all the way round the ring.";

    private KeeperLamplighter() {
    }

    /** The line for this ring. */
    public static String line(LamplighterRound r) {
        if (r.start() == LamplighterRound.NONE) {
            return SHORT;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == LamplighterRound.Outcome.LATER) {
            return String.format(LATER, r.named(), r.start());
        }
        if (r.last() == LamplighterRound.Outcome.DRY) {
            return String.format(DRY, r.named());
        }
        return String.format(GREETING, r.posts());
    }
}
