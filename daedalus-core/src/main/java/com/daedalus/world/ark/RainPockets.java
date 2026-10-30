// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.ark.ArkCellar.State;

import java.util.SplittableRandom;

/**
 * G220 Rain Pockets: after a storm, rain pools between the Cinder Shelf's basalt columns (G147
 * landfall). Each column holds {@code min(tallest to its left, tallest to its right) - height}
 * litres. {@link #pockets} computes every column in one O(n) two-pointer pass; {@link #topUp}
 * hauls the pooled litres into the G196 {@link ArkCellar} cistern, spilling over its cap.
 */
public final class RainPockets {

    public static final String QUEST_ID = "q_rain_pockets";

    private RainPockets() { }

    /** Seeded shelf of {@code n} column heights in [0, maxHeight). */
    public static int[] columns(long seed, int n, int maxHeight) {
        if (n < 0 || maxHeight <= 0) {
            throw new IllegalArgumentException("bad shelf");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] h = new int[n];
        for (int i = 0; i < n; i++) {
            h[i] = rnd.nextInt(maxHeight);
        }
        return h;
    }

    /** Litres held above each column. */
    public static int[] pockets(int[] heights) {
        int n = heights.length;
        int[] w = new int[n];
        int l = 0;
        int r = n - 1;
        int leftMax = 0;
        int rightMax = 0;
        while (l <= r) {
            if (heights[l] < 0 || heights[r] < 0) {
                throw new IllegalArgumentException("negative height");
            }
            if (heights[l] <= heights[r]) {
                leftMax = Math.max(leftMax, heights[l]);
                w[l] = leftMax - heights[l];
                l++;
            } else {
                rightMax = Math.max(rightMax, heights[r]);
                w[r] = rightMax - heights[r];
                r--;
            }
        }
        return w;
    }

    public static long total(int[] heights) {
        long sum = 0;
        for (int v : pockets(heights)) {
            sum += v;
        }
        return sum;
    }

    /** Haul {@code litres} into the cistern; anything over the cap spills. */
    public static State topUp(ArkCellar cellar, State s, long litres) {
        if (litres < 0) {
            throw new IllegalArgumentException("negative litres");
        }
        double cap = cellar.rules().cisternCapL();
        return new State(Math.min(cap, s.cisternL() + litres), s.cellar());
    }

    /** Quest q_rain_pockets: the shelf must hold at least {@code target} litres after the storm. */
    public static boolean quest(int[] heights, long target) {
        return total(heights) >= target;
    }
}
