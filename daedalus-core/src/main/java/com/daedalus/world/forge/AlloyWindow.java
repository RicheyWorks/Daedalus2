// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Alloy Window (contest gap G264): a train of ore carts rolls past the forge, and the alloy recipe needs given counts
 * of each ore. Find the shortest run of consecutive carts that holds the whole recipe.
 *
 * <p>The tool is plain: {@link #shortest} is the O(n + kinds) two-pointer minimum window over an {@code int[]} of ore
 * kinds 0..kinds-1 and an {@code int[]} of needed counts. Any project can use it for minimum-cover window queries.
 */
public final class AlloyWindow {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_alloy_window";

    /** How a pick went. */
    public enum Grade { PURE, SLAG }

    /** Carts [from, to) of the train; {@code NONE} when no run holds the recipe. */
    public record Window(int from, int to) {

        /** No window. */
        public static final Window NONE = new Window(-1, -1);

        /** Window length (0 for NONE). */
        public int length() {
            return to - from;
        }
    }

    private AlloyWindow() {
    }

    /** {@code n} seeded carts of ore kinds 0..kinds-1. Same seed, same train. */
    public static int[] train(long seed, int n, int kinds) {
        if (n < 0 || kinds < 1) {
            throw new IllegalArgumentException("need n >= 0 and kinds >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] t = new int[n];
        for (int i = 0; i < n; i++) {
            t[i] = r.nextInt(kinds);
        }
        return t;
    }

    private static void validate(int[] carts, int[] need) {
        for (int c : carts) {
            if (c < 0 || c >= need.length) {
                throw new IllegalArgumentException("unknown ore " + c);
            }
        }
        for (int x : need) {
            if (x < 0) {
                throw new IllegalArgumentException("negative need");
            }
        }
    }

    /** The shortest window holding at least need[k] carts of every ore k (earliest on ties). */
    public static Window shortest(int[] carts, int[] need) {
        validate(carts, need);
        int missing = 0;
        int[] left = need.clone();
        for (int x : need) {
            missing += x;
        }
        if (missing == 0) {
            return new Window(0, 0);
        }
        int bestFrom = -1;
        int bestLen = Integer.MAX_VALUE;
        int lo = 0;
        for (int hi = 0; hi < carts.length; hi++) {
            if (left[carts[hi]]-- > 0) {
                missing--;
            }
            while (missing == 0) {
                if (hi + 1 - lo < bestLen) {
                    bestLen = hi + 1 - lo;
                    bestFrom = lo;
                }
                if (++left[carts[lo++]] > 0) {
                    missing++;
                }
            }
        }
        return bestFrom < 0 ? Window.NONE : new Window(bestFrom, bestFrom + bestLen);
    }

    /** True if carts[from, to) hold the whole recipe. */
    public static boolean holds(int[] carts, int[] need, Window w) {
        validate(carts, need);
        if (w.from() < 0 || w.to() > carts.length || w.from() > w.to()) {
            return false;
        }
        int[] got = new int[need.length];
        for (int i = w.from(); i < w.to(); i++) {
            got[carts[i]]++;
        }
        for (int k = 0; k < need.length; k++) {
            if (got[k] < need[k]) {
                return false;
            }
        }
        return true;
    }

    /** PURE only for a run that holds the recipe and is as short as possible. */
    public static Grade grade(int[] carts, int[] need, Window pick) {
        Window best = shortest(carts, need);
        return best != Window.NONE && holds(carts, need, pick) && pick.length() == best.length()
                ? Grade.PURE : Grade.SLAG;
    }

    /** The Forgemaster's line for a pick. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case PURE -> "Forgemaster: every ore the recipe asks for, and not one cart more. That melt will ring true.";
            case SLAG -> "Forgemaster: short of ore or heavy with waste. Watch the train again.";
        };
    }
}
