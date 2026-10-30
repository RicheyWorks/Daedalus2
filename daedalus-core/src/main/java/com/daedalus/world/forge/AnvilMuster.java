// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Anvil Muster (contest gap G287): smiths live at spots along the shore road, each with a number of apprentices. Place
 * the new muster anvil so the total walk, weighted by apprentices, is least, and name the k-th nearest spot on demand.
 *
 * <p>The tool is plain: {@link #kth} is expected O(n) quickselect on a copy of a {@code long[]} with seeded pivots, and
 * {@link #weightedMedian} the spot minimising the weighted sum of distances. Any project can use it for order
 * statistics and 1D facility placement.
 */
public final class AnvilMuster {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_anvil_muster";

    /** How a placement went. */
    public enum Grade { CENTRED, ASKEW }

    private AnvilMuster() {
    }

    /** {@code n} seeded spots in 0..roadLength. Same seed, same road. */
    public static long[] spots(long seed, int n, int roadLength) {
        if (n < 0 || roadLength < 0) {
            throw new IllegalArgumentException("need n >= 0 and roadLength >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[] s = new long[n];
        for (int i = 0; i < n; i++) {
            s[i] = r.nextInt(roadLength + 1);
        }
        return s;
    }

    /** The k-th smallest value (0-based), via quickselect on a copy. */
    public static long kth(long[] a, int k) {
        if (k < 0 || k >= a.length) {
            throw new IllegalArgumentException("k out of range");
        }
        long[] b = a.clone();
        SplittableRandom r = new SplittableRandom(0x9E3779B97F4A7C15L ^ a.length);
        int lo = 0;
        int hi = b.length - 1;
        while (lo < hi) {
            long pivot = b[lo + r.nextInt(hi - lo + 1)];
            int lt = lo;
            int gt = hi;
            int i = lo;
            while (i <= gt) {
                if (b[i] < pivot) {
                    swap(b, lt++, i++);
                } else if (b[i] > pivot) {
                    swap(b, i, gt--);
                } else {
                    i++;
                }
            }
            if (k < lt) {
                hi = lt - 1;
            } else if (k > gt) {
                lo = gt + 1;
            } else {
                return pivot;
            }
        }
        return b[lo];
    }

    private static void swap(long[] a, int i, int j) {
        long t = a[i];
        a[i] = a[j];
        a[j] = t;
    }

    /** Total walk if the anvil stands at {@code at}. */
    public static long walk(long[] spots, long[] weights, long at) {
        check(spots, weights);
        long t = 0;
        for (int i = 0; i < spots.length; i++) {
            t += weights[i] * Math.abs(spots[i] - at);
        }
        return t;
    }

    private static void check(long[] spots, long[] weights) {
        if (spots.length != weights.length) {
            throw new IllegalArgumentException("one weight per spot");
        }
        for (long w : weights) {
            if (w < 0) {
                throw new IllegalArgumentException("weights must be >= 0");
            }
        }
    }

    /** Smallest spot minimising the weighted walk (a weighted median); needs a positive total weight. */
    public static long weightedMedian(long[] spots, long[] weights) {
        check(spots, weights);
        int n = spots.length;
        Integer[] order = new Integer[n];
        long total = 0;
        for (int i = 0; i < n; i++) {
            order[i] = i;
            total += weights[i];
        }
        if (total <= 0) {
            throw new IllegalArgumentException("need a positive total weight");
        }
        Arrays.sort(order, (x, y) -> Long.compare(spots[x], spots[y]));
        long acc = 0;
        for (int idx : order) {
            acc += weights[idx];
            if (2 * acc >= total) {
                return spots[idx];
            }
        }
        return spots[order[n - 1]];
    }

    /** CENTRED only if the anvil's walk is as small as the best spot's. */
    public static Grade grade(long[] spots, long[] weights, long at) {
        return walk(spots, weights, at) == walk(spots, weights, weightedMedian(spots, weights))
                ? Grade.CENTRED : Grade.ASKEW;
    }

    /** The Forgemaster's line for a placement. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case CENTRED -> "Forgemaster: no apprentice walks a step more than needed. The muster gathers fast.";
            case ASKEW -> "Forgemaster: half the island is grumbling about the walk. Move the anvil.";
        };
    }
}
