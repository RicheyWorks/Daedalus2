// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Vein Survey (contest gap G330): a mine shaft of ore samples, and a batch of stretches {@code [l, r]}. Say how many
 * distinct ore kinds each stretch holds.
 *
 * <p>The tool is plain: {@link #distinctInRanges} is Mo's algorithm, offline, ordering queries by sqrt-sized blocks of
 * {@code l} with the odd-even trick on {@code r}, and moving two pointers with add/remove counts, in
 * O((n + q) sqrt n). Values are compressed first, so any {@code int} kinds work. Any project can use it for offline
 * range-distinct or other add/remove range aggregates.
 */
public final class VeinSurvey {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_vein_survey";

    /** How a survey went. */
    public enum Grade { CHARTED, MISCHARTED }

    private VeinSurvey() {
    }

    /** A seeded shaft of {@code n} samples of {@code kinds} ore kinds. */
    public static int[] shaft(long seed, int n, int kinds) {
        if (n < 0 || kinds < 1) {
            throw new IllegalArgumentException("need n >= 0 and kinds >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] s = new int[n];
        for (int i = 0; i < n; i++) {
            s[i] = r.nextInt(kinds);
        }
        return s;
    }

    /** {@code q} seeded inclusive stretches over a shaft of length {@code n >= 1}. */
    public static int[][] stretches(long seed, int n, int q) {
        if (n < 1 || q < 0) {
            throw new IllegalArgumentException("need n >= 1 and q >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] out = new int[q][2];
        for (int[] x : out) {
            int a = r.nextInt(n);
            int b = r.nextInt(n);
            x[0] = Math.min(a, b);
            x[1] = Math.max(a, b);
        }
        return out;
    }

    /** Distinct kinds in each inclusive stretch, in query order. */
    public static int[] distinctInRanges(int[] ore, int[][] queries) {
        int n = ore.length;
        int[] sorted = ore.clone();
        Arrays.sort(sorted);
        int[] comp = new int[n];
        for (int i = 0; i < n; i++) {
            comp[i] = Arrays.binarySearch(sorted, ore[i]);
        }
        for (int[] q : queries) {
            if (q[0] < 0 || q[1] >= n || q[0] > q[1]) {
                throw new IllegalArgumentException("bad stretch " + Arrays.toString(q));
            }
        }
        int block = Math.max(1, (int) Math.sqrt(n));
        Integer[] order = new Integer[queries.length];
        for (int i = 0; i < order.length; i++) {
            order[i] = i;
        }
        Arrays.sort(order, (a, b) -> {
            int ba = queries[a][0] / block;
            int bb = queries[b][0] / block;
            if (ba != bb) {
                return Integer.compare(ba, bb);
            }
            return (ba & 1) == 0 ? Integer.compare(queries[a][1], queries[b][1])
                    : Integer.compare(queries[b][1], queries[a][1]);
        });
        int[] count = new int[n];
        int distinct = 0;
        int lo = 0;
        int hi = -1;
        int[] ans = new int[queries.length];
        for (int qi : order) {
            int l = queries[qi][0];
            int r = queries[qi][1];
            while (hi < r) {
                if (count[comp[++hi]]++ == 0) {
                    distinct++;
                }
            }
            while (lo > l) {
                if (count[comp[--lo]]++ == 0) {
                    distinct++;
                }
            }
            while (hi > r) {
                if (--count[comp[hi--]] == 0) {
                    distinct--;
                }
            }
            while (lo < l) {
                if (--count[comp[lo++]] == 0) {
                    distinct--;
                }
            }
            ans[qi] = distinct;
        }
        return ans;
    }

    /** CHARTED only if every claimed count is right. */
    public static Grade grade(int[] ore, int[][] queries, int[] claimed) {
        return Arrays.equals(distinctInRanges(ore, queries), claimed) ? Grade.CHARTED : Grade.MISCHARTED;
    }

    /** The Forgemaster's line for a survey. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case CHARTED -> "Forgemaster: every stretch charted true. The miners will dig where you point.";
            case MISCHARTED -> "Forgemaster: your chart sends men into barren rock. Walk the shaft again.";
        };
    }
}
