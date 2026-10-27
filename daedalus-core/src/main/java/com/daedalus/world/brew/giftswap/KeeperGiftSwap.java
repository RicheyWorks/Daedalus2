// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.giftswap;

/** Keeper Oriel in the midwinter hall. */
public final class KeeperGiftSwap {
    public static final String GREETING = "%d friends put gifts in the basket and each draws one. "
            + "In how many draws does nobody get their own gift?";
    public static final String WRONG = "Not %d. If even one friend draws their own gift, the swap fails.";
    public static final String ALONE = "One friend can't swap with nobody. Nothing to count.";
    public static final String THANKS = "Every good draw counted! Let the swap begin.";
    public static final String DONE = "Wrapped, drawn and opened, and nobody's gift came home.";

    private KeeperGiftSwap() {
    }

    /** The line for this swap. */
    public static String line(GiftSwap r) {
        if (r.alone()) {
            return ALONE;
        }
        if (r.quest().currentStep() == null) {
            return DONE;
        }
        if (r.last() == GiftSwap.Outcome.WRONG) {
            return String.format(WRONG, r.named());
        }
        return String.format(GREETING, r.friends());
    }
}
