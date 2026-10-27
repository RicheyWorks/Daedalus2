// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Pan Balance (contest gap G311): the assayer splits a heap of ingots between two scale pans as evenly as possible.
 * Name the smallest imbalance and a split that achieves it, and say whether an exact target weight can be made.
 *
 * <p>The tool is plain: subset-sum DP over reachable sums where each sum remembers the first ingot that reached it,
 * which makes reconstruction a simple walk back. Totals are capped at {@link #MAX_TOTAL}. Any project can use it for
 * partition, loot splitting, or exact-change checks.
 */
public final class PanBalance {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_pan_balance";

    /** Largest total weight accepted. */
    public static final int MAX_TOTAL = 1 << 22;

    /** How a split went. */
    public enum Grade { LEVEL, TILTED }

    private PanBalance() {
    }

    /** {@code n} seeded ingots weighing 1..maxWeight. Same seed, same heap. */
    public static int[] ingots(long seed, int n, int maxWeight) {
        if (n < 0 || maxWeight < 1) {
            throw new IllegalArgumentException("need n >= 0 and maxWeight >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] w = new int[n];
        for (int i = 0; i < n; i++) {
            w[i] = 1 + r.nextInt(maxWeight);
        }
        return w;
    }

    private static int total(int[] w) {
        long t = 0;
        for (int x : w) {
            if (x < 0) {
                throw new IllegalArgumentException("weights must be non-negative");
            }
            t += x;
        }
        if (t > MAX_TOTAL) {
            throw new IllegalArgumentException("total weight too large: " + t);
        }
        return (int) t;
    }

    /** from[s] = first ingot index that reaches sum s, -1 for s = 0, -2 if unreachable. */
    private static int[] table(int[] w) {
        int t = total(w);
        int[] from = new int[t + 1];
        Arrays.fill(from, -2);
        from[0] = -1;
        for (int i = 0; i < w.length; i++) {
            for (int s = t; s >= w[i]; s--) {
                if (from[s] == -2 && from[s - w[i]] != -2 && w[i] > 0) {
                    from[s] = i;
                }
            }
        }
        return from;
    }

    /** True if some subset of ingots weighs exactly {@code target}. */
    public static boolean reachable(int[] w, int target) {
        int[] from = table(w);
        return target >= 0 && target < from.length && from[target] != -2;
    }

    /** Ingots for the left pan of an optimal split (the lighter-or-equal pan). */
    public static boolean[] bestSplit(int[] w) {
        int[] from = table(w);
        int s = (from.length - 1) / 2;
        while (from[s] == -2) {
            s--;
        }
        boolean[] left = new boolean[w.length];
        while (s > 0) {
            int i = from[s];
            left[i] = true;
            s -= w[i];
        }
        return left;
    }

    /** |right - left| for a split. */
    public static int imbalance(int[] w, boolean[] left) {
        int d = 0;
        for (int i = 0; i < w.length; i++) {
            d += left[i] ? -w[i] : w[i];
        }
        return Math.abs(d);
    }

    /** LEVEL only if the split is as even as possible. */
    public static Grade grade(int[] w, boolean[] left) {
        if (left.length != w.length) {
            return Grade.TILTED;
        }
        return imbalance(w, left) == imbalance(w, bestSplit(w)) ? Grade.LEVEL : Grade.TILTED;
    }

    /** The Forgemaster's line for a split. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case LEVEL -> "Forgemaster: the pans hang as level as these ingots allow. An honest assay.";
            case TILTED -> "Forgemaster: the beam tilts more than it must. Shift an ingot and weigh again.";
        };
    }
}
