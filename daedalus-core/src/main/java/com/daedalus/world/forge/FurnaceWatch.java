// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Furnace Watch (contest gap G218): the great furnace logs a temperature every minute. A blade tempers only if the
 * stretch it sits in stays inside a band, so the watch needs the hottest and coldest reading of every window.
 *
 * <p>The tool is plain: {@link #windowMax} and {@link #windowMin} are O(n) monotone-deque sliding windows over an
 * {@code int[]}, and {@link #longestInBand} finds the longest stretch whose max - min stays within a width (two deques,
 * two pointers). Any project can use it for rolling peaks in telemetry or stable-signal detection. Pairs with
 * {@link BilletWelds}: welded bars go into the furnace next.
 */
public final class FurnaceWatch {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_furnace_watch";

    /** How a blade came out. */
    public enum Grade { TEMPERED, BRITTLE, SOFT }

    /** A stretch [from, to] inclusive. */
    public record Stretch(int from, int to) {

        /** Minutes in the stretch. */
        public int length() {
            return to - from + 1;
        }
    }

    private FurnaceWatch() {
    }

    /** A seeded log of {@code n} readings: a random walk from {@code start}, steps in [-step, step]. */
    public static int[] log(long seed, int n, int start, int step) {
        if (n < 0 || step < 0) {
            throw new IllegalArgumentException("need n >= 0 and step >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] t = new int[n];
        int cur = start;
        for (int i = 0; i < n; i++) {
            cur += r.nextInt(-step, step + 1);
            t[i] = cur;
        }
        return t;
    }

    /** Max of every window of k readings; result has n - k + 1 entries. */
    public static int[] windowMax(int[] a, int k) {
        return window(a, k, true);
    }

    /** Min of every window of k readings; result has n - k + 1 entries. */
    public static int[] windowMin(int[] a, int k) {
        return window(a, k, false);
    }

    private static int[] window(int[] a, int k, boolean max) {
        if (k < 1 || k > a.length) {
            throw new IllegalArgumentException("window must be 1.." + a.length);
        }
        int[] out = new int[a.length - k + 1];
        int[] dq = new int[a.length];
        int h = 0;
        int t = 0;
        for (int i = 0; i < a.length; i++) {
            while (t > h && (max ? a[dq[t - 1]] <= a[i] : a[dq[t - 1]] >= a[i])) {
                t--;
            }
            dq[t++] = i;
            if (dq[h] <= i - k) {
                h++;
            }
            if (i >= k - 1) {
                out[i - k + 1] = a[dq[h]];
            }
        }
        return out;
    }

    /** Earliest longest stretch whose max - min is at most {@code width}; null for an empty log. */
    public static Stretch longestInBand(int[] a, int width) {
        if (width < 0) {
            throw new IllegalArgumentException("width must be >= 0");
        }
        if (a.length == 0) {
            return null;
        }
        int[] hi = new int[a.length];
        int[] lo = new int[a.length];
        int hh = 0;
        int ht = 0;
        int lh = 0;
        int lt = 0;
        int left = 0;
        int bf = 0;
        int bt = 0;
        for (int i = 0; i < a.length; i++) {
            while (ht > hh && a[hi[ht - 1]] <= a[i]) {
                ht--;
            }
            hi[ht++] = i;
            while (lt > lh && a[lo[lt - 1]] >= a[i]) {
                lt--;
            }
            lo[lt++] = i;
            while ((long) a[hi[hh]] - a[lo[lh]] > width) {
                left++;
                if (hi[hh] < left) {
                    hh++;
                }
                if (lo[lh] < left) {
                    lh++;
                }
            }
            if (i - left > bt - bf) {
                bf = left;
                bt = i;
            }
        }
        return new Stretch(bf, bt);
    }

    /** A blade sitting in [from, to] with band [low, high]: BRITTLE if any reading is hotter, SOFT if colder. */
    public static Grade grade(int[] a, Stretch s, int low, int high) {
        if (s.from() < 0 || s.to() >= a.length || s.from() > s.to()) {
            throw new IllegalArgumentException("stretch outside the log");
        }
        int mx = Integer.MIN_VALUE;
        int mn = Integer.MAX_VALUE;
        for (int i = s.from(); i <= s.to(); i++) {
            mx = Math.max(mx, a[i]);
            mn = Math.min(mn, a[i]);
        }
        if (mx > high) {
            return Grade.BRITTLE;
        }
        return mn < low ? Grade.SOFT : Grade.TEMPERED;
    }

    /** The Forgemaster's line for a blade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TEMPERED -> "Forgemaster: blue at the spine, straw at the edge. That blade will hold.";
            case BRITTLE -> "Forgemaster: you let it run hot. It will snap on the first parry.";
            case SOFT -> "Forgemaster: the fire dipped. That edge will roll like lead.";
        };
    }
}
