// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G222 The Glass Drop: the ark glazier must learn the highest mast rung (0..n) from which a G45
 * ark-glass (T4) bottle survives a drop, with only {@code k} spare bottles. A bottle that
 * survives can be reused; a broken one is gone.
 *
 * <p>{@link #coverable}{@code (k, d)} is the most rungs that {@code k} bottles and {@code d}
 * drops can settle: {@code f(k, d) = f(k-1, d-1) + f(k, d-1) + 1}. {@link #minDrops} is the
 * smallest worst-case drop count and {@link #nextRung} the rung to try next. {@link #simulate}
 * plays the strategy against a hidden answer.
 */
public final class GlassDrop {

    public static final String QUEST_ID = "q_glass_drop";

    private static final long CAP = Long.MAX_VALUE / 4;

    public record Run(int drops, int bottlesBroken, int safeRung) { }

    private GlassDrop() { }

    public static long coverable(int bottles, int drops) {
        if (bottles < 0 || drops < 0) {
            throw new IllegalArgumentException("negative bottles or drops");
        }
        long[] f = new long[bottles + 1];
        for (int d = 1; d <= drops; d++) {
            for (int k = bottles; k >= 1; k--) {
                f[k] = Math.min(CAP, f[k] + f[k - 1] + 1);
            }
        }
        return f[bottles];
    }

    public static int minDrops(int bottles, int rungs) {
        if (rungs < 0) {
            throw new IllegalArgumentException("negative rungs");
        }
        if (rungs == 0) {
            return 0;
        }
        if (bottles <= 0) {
            throw new IllegalArgumentException("need at least one bottle");
        }
        int d = 0;
        while (coverable(bottles, d) < rungs) {
            d++;
        }
        return d;
    }

    /** Rung (1-based, counted from the lowest unknown rung) to drop from next. */
    public static int nextRung(int bottles, int rungs) {
        int d = minDrops(bottles, rungs);
        long r = coverable(bottles - 1, d - 1) + 1;
        return (int) Math.min(rungs, r);
    }

    /** Play the optimal strategy when the true highest safe rung is {@code safeRung}. */
    public static Run simulate(int bottles, int rungs, int safeRung) {
        if (safeRung < 0 || safeRung > rungs) {
            throw new IllegalArgumentException("safe rung out of range");
        }
        int lo = 0;
        int hi = rungs;
        int k = bottles;
        int drops = 0;
        int broken = 0;
        while (hi > lo) {
            int rung = lo + nextRung(k, hi - lo);
            drops++;
            if (rung > safeRung) {
                k--;
                broken++;
                hi = rung - 1;
            } else {
                lo = rung;
            }
        }
        return new Run(drops, broken, lo);
    }

    /** Quest q_glass_drop: settle the mast within the glazier's drop budget. */
    public static boolean quest(int bottles, int rungs, int dropBudget) {
        return minDrops(bottles, rungs) <= dropBudget;
    }
}
