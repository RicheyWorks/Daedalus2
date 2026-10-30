// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G547 Stall Plaques (Studio horse lane): the sign painter letters the stable roll, horse names in
 * order, onto plaque lines of a fixed width, one space between names on a line. Ragged lines look
 * bad, so every line except the last scores the square of its leftover space; the painter wants the
 * least total (Knuth-Plass-style word wrap). {@link #best} is the exact O(n^2) DP over where each
 * line starts; {@link #fillEachLine} (put as many names as fit on each line, then break) leaves one
 * very short line after a run of full ones. Plain int[] API of name lengths; small and pure so it
 * ports to C++ for Unreal.
 */
public final class StallPlaques {

    public static final String QUEST_ID = "q_neat_plaques";
    public static final long INVALID = -1;

    /** A layout: total squared slack and the index of the first name on each line after the first. */
    public record Layout(long ugliness, int[] breaks) {
        public Layout {
            breaks = breaks.clone();
        }

        @Override
        public int[] breaks() {
            return breaks.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Layout l && l.ugliness == ugliness && Arrays.equals(l.breaks, breaks);
        }

        @Override
        public int hashCode() {
            return 31 * Long.hashCode(ugliness) + Arrays.hashCode(breaks);
        }

        @Override
        public String toString() {
            return "Layout[" + ugliness + ", " + Arrays.toString(breaks) + "]";
        }
    }

    private StallPlaques() { }

    /** Seeded name lengths in [minLen, maxLen]. */
    public static int[] names(long seed, int n, int minLen, int maxLen) {
        if (n < 0 || n > 4096 || minLen < 1 || maxLen < minLen) {
            throw new IllegalArgumentException("bad roll");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] len = new int[n];
        for (int i = 0; i < n; i++) {
            len[i] = minLen + rnd.nextInt(maxLen - minLen + 1);
        }
        return len;
    }

    /** Least total squared slack over all ways to break the roll into lines of the given width. */
    public static Layout best(int[] len, int width) {
        check(len, width);
        int n = len.length;
        long[] cost = new long[n + 1];
        int[] next = new int[n + 1];
        cost[n] = 0;
        next[n] = n;
        for (int i = n - 1; i >= 0; i--) {
            cost[i] = Long.MAX_VALUE;
            int used = -1;
            for (int j = i; j < n; j++) {
                used += len[j] + 1;
                if (used > width) {
                    break;
                }
                long slack = width - used;
                long c = (j == n - 1 ? 0 : slack * slack) + cost[j + 1];
                if (c < cost[i]) {
                    cost[i] = c;
                    next[i] = j + 1;
                }
            }
        }
        int[] breaks = new int[n];
        int k = 0;
        for (int i = next[0]; i < n; i = next[i]) {
            breaks[k++] = i;
        }
        return new Layout(cost[0], Arrays.copyOf(breaks, k));
    }

    /** Naive habit: fill each line with as many names as fit, then break. */
    public static Layout fillEachLine(int[] len, int width) {
        check(len, width);
        int n = len.length;
        int[] breaks = new int[n];
        int k = 0;
        int used = -1;
        for (int i = 0; i < n; i++) {
            if (used + len[i] + 1 > width) {
                breaks[k++] = i;
                used = -1;
            }
            used += len[i] + 1;
        }
        int[] b = Arrays.copyOf(breaks, k);
        return new Layout(ugliness(len, width, b), b);
    }

    /** Total squared slack of a layout, or INVALID when a line overflows or the breaks are not rising inside the roll. */
    public static long ugliness(int[] len, int width, int[] breaks) {
        check(len, width);
        int n = len.length;
        long total = 0;
        int start = 0;
        for (int k = 0; k <= breaks.length; k++) {
            int end = k < breaks.length ? breaks[k] : n;
            if (end <= start && !(n == 0 && breaks.length == 0) || end > n) {
                return INVALID;
            }
            int used = -1;
            for (int i = start; i < end; i++) {
                used += len[i] + 1;
            }
            if (used > width) {
                return INVALID;
            }
            if (k < breaks.length) {
                long slack = width - used;
                total += slack * slack;
            }
            start = end;
        }
        return total;
    }

    /** Quest q_neat_plaques: the painter's layout fits and is as neat as possible. */
    public static boolean quest(int[] len, int width, int[] breaks) {
        long got = ugliness(len, width, breaks);
        return got != INVALID && got == best(len, width).ugliness();
    }

    private static void check(int[] len, int width) {
        for (int l : len) {
            if (l < 1 || l > width) {
                throw new IllegalArgumentException("every name must fit on one line");
            }
        }
    }
}
