// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.BitSet;

/**
 * Recaman Ramble: a courier walks the forge road by Recaman's rule. a(0) = 0; step n goes to a(n-1) - n when that
 * is non-negative and unvisited, otherwise to a(n-1) + n.
 *
 * <p>Reusable plain long API: {@link #terms}, {@link #firstHit}, {@link #distinct}.
 */
public final class RecamanRamble {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_recaman_ramble";

    /** Most terms produced in one call. */
    public static final int MAX_TERMS = 1 << 22;

    /** Grade band. */
    public enum Grade { ON_ROAD, LOST }

    private RecamanRamble() {
    }

    /** a(0..n-1). */
    public static long[] terms(int n) {
        check(n);
        long[] a = new long[n];
        walk(n, a, -1);
        return a;
    }

    /** First n below maxSteps with a(n) == v, or -1. */
    public static long firstHit(long v, int maxSteps) {
        check(maxSteps);
        if (v < 0) {
            return -1;
        }
        return walk(maxSteps, null, v);
    }

    /** Number of distinct milestones among a(0..n-1). */
    public static int distinct(int n) {
        check(n);
        long[] a = terms(n);
        BitSet seen = new BitSet();
        for (long x : a) {
            seen.set((int) x);
        }
        return seen.cardinality();
    }

    /** ON_ROAD when claimed is a(n). */
    public static Grade grade(int n, long claimed) {
        return terms(n + 1)[n] == claimed ? Grade.ON_ROAD : Grade.LOST;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case ON_ROAD -> "Forgemaster: back when you can, forward when you must. The courier is right on the road.";
            case LOST -> "Forgemaster: lost. Check whether that milestone was already walked before stepping back.";
        };
    }

    private static long walk(int n, long[] out, long target) {
        BitSet seen = new BitSet();
        long cur = 0;
        for (int i = 0; i < n; i++) {
            if (i > 0) {
                long back = cur - i;
                cur = back >= 0 && !seen.get((int) back) ? back : cur + i;
            }
            if (cur > Integer.MAX_VALUE) {
                throw new IllegalStateException("milestone overflow");
            }
            seen.set((int) cur);
            if (out != null) {
                out[i] = cur;
            }
            if (cur == target) {
                return i;
            }
        }
        return -1;
    }

    private static void check(int n) {
        if (n < 0 || n > MAX_TERMS) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
    }
}
