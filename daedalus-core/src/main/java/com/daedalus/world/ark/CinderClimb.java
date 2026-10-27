// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

/**
 * G217 The Cinder Climb: at the G147 Cinder Shelf landfall the shore rises in basalt ledges of
 * seeded heights. Scouts walk the ledges in order, may skip any, but every step must be strictly
 * higher. {@link #longest} finds the longest climb with O(n log n) patience sorting and recovers
 * which ledges to use; {@link #greedy} (always step onto the next higher ledge) is the habit
 * that strands the scouts on a tall early ledge. Plain int[] API.
 */
public final class CinderClimb {

    public static final String QUEST_ID = "q_cinder_climb";

    public record Climb(int length, int[] ledges) {
        public Climb {
            ledges = ledges.clone();
        }

        @Override
        public int[] ledges() {
            return ledges.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Climb c && c.length == length && Arrays.equals(c.ledges, ledges);
        }

        @Override
        public int hashCode() {
            return 31 * length + Arrays.hashCode(ledges);
        }

        @Override
        public String toString() {
            return "Climb[" + length + ", " + Arrays.toString(ledges) + "]";
        }
    }

    private CinderClimb() { }

    /** Seeded shelf of {@code n} ledges with heights in [0, maxHeight). */
    public static int[] shelf(long seed, int n, int maxHeight) {
        if (n < 0 || maxHeight <= 0) {
            throw new IllegalArgumentException("bad shelf");
        }
        Random rnd = new Random(seed);
        int[] h = new int[n];
        for (int i = 0; i < n; i++) {
            h[i] = rnd.nextInt(maxHeight);
        }
        return h;
    }

    /** Longest strictly rising climb; {@code ledges} holds the chosen ledge indices in order. */
    public static Climb longest(int[] heights) {
        int n = heights.length;
        int[] tailIdx = new int[n];
        int[] prev = new int[n];
        int len = 0;
        for (int i = 0; i < n; i++) {
            int lo = 0;
            int hi = len;
            while (lo < hi) {
                int mid = (lo + hi) >>> 1;
                if (heights[tailIdx[mid]] < heights[i]) {
                    lo = mid + 1;
                } else {
                    hi = mid;
                }
            }
            prev[i] = lo > 0 ? tailIdx[lo - 1] : -1;
            tailIdx[lo] = i;
            if (lo == len) {
                len++;
            }
        }
        int[] path = new int[len];
        int k = len > 0 ? tailIdx[len - 1] : -1;
        for (int j = len - 1; j >= 0; j--) {
            path[j] = k;
            k = prev[k];
        }
        return new Climb(len, path);
    }

    /** Naive: start on the first ledge and always step onto the next strictly higher one. */
    public static Climb greedy(int[] heights) {
        List<Integer> path = new ArrayList<>();
        for (int i = 0; i < heights.length; i++) {
            if (path.isEmpty() || heights[i] > heights[path.get(path.size() - 1)]) {
                path.add(i);
            }
        }
        return new Climb(path.size(), path.stream().mapToInt(Integer::intValue).toArray());
    }

    /** True when {@code ledges} is an in-order, strictly rising climb on {@code heights}. */
    public static boolean valid(int[] heights, int[] ledges) {
        for (int j = 0; j < ledges.length; j++) {
            if (ledges[j] < 0 || ledges[j] >= heights.length) {
                return false;
            }
            if (j > 0 && (ledges[j] <= ledges[j - 1] || heights[ledges[j]] <= heights[ledges[j - 1]])) {
                return false;
            }
        }
        return true;
    }

    /** Quest q_cinder_climb: the scouts' climb must reach the longest possible length. */
    public static boolean quest(int[] heights, int[] scoutLedges) {
        return valid(heights, scoutLedges) && scoutLedges.length == longest(heights).length();
    }
}
