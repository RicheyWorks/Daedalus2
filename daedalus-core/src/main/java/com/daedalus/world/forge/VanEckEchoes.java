// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;

/**
 * Van Eck Echoes: the anvil echoes. Strike 0 rings 0; each next strike rings with how many strikes ago the previous
 * ring was last heard before, or 0 when that ring was new: 0, 0, 1, 0, 2, 0, 2, 2, 1, 6, 0, 5, ... (Van Eck).
 *
 * <p>Reusable plain API, linear time with a last-seen table, for prefixes up to {@link #MAX_LEN}:
 * {@link #sequence}, {@link #term}, {@link #firstOccurrence}, {@link #zeroCount}.
 */
public final class VanEckEchoes {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_van_eck_echoes";
    /** Largest supported prefix length. */
    public static final int MAX_LEN = 10_000_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private VanEckEchoes() {
    }

    /** The first len echoes a(0..len-1). */
    public static int[] sequence(int len) {
        if (len < 0 || len > MAX_LEN) {
            throw new IllegalArgumentException("length out of range: " + len);
        }
        int[] a = new int[len];
        if (len == 0) {
            return a;
        }
        int[] last = new int[len];
        Arrays.fill(last, -1);
        for (int n = 0; n + 1 < len; n++) {
            int v = a[n];
            int prev = last[v];
            a[n + 1] = prev < 0 ? 0 : n - prev;
            last[v] = n;
        }
        return a;
    }

    /** a(n). */
    public static int term(int n) {
        if (n < 0 || n >= MAX_LEN) {
            throw new IllegalArgumentException("index out of range: " + n);
        }
        return sequence(n + 1)[n];
    }

    /** First index n &lt; len with a(n) = v, or -1. */
    public static int firstOccurrence(int v, int len) {
        if (v < 0) {
            throw new IllegalArgumentException("value must be non-negative: " + v);
        }
        int[] a = sequence(len);
        for (int n = 0; n < a.length; n++) {
            if (a[n] == v) {
                return n;
            }
        }
        return -1;
    }

    /** Number of zero echoes among a(0..len-1). */
    public static int zeroCount(int len) {
        int c = 0;
        for (int v : sequence(len)) {
            if (v == 0) {
                c++;
            }
        }
        return c;
    }

    /** Grade a claimed value for a(n). */
    public static Grade grade(int n, int claimed) {
        return term(n) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: you heard the echo true. Count back to the last ring.";
            case SLIPPED -> "Forgemaster: the echo slipped. A new ring always answers zero.";
        };
    }
}
