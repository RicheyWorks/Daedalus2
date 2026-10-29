// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;

/**
 * Padovan Plinths: triangular plinths spiral outward with sides from the Padovan sequence
 * P(0) = P(1) = P(2) = 1, P(n) = P(n-2) + P(n-3): 1, 1, 1, 2, 2, 3, 4, 5, 7, 9, 12, 16, ...
 *
 * <p>Reusable plain long API, exact for every n up to {@link #MAX_INDEX} (the last term that fits in a long):
 * {@link #padovan}, {@link #isPadovan}, {@link #indexOf}, {@link #runSum}.
 */
public final class PadovanPlinths {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_padovan_plinths";

    private static final long[] TABLE = build();
    /** Largest index whose term fits in a long. */
    public static final int MAX_INDEX = TABLE.length - 1;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private PadovanPlinths() {
    }

    private static long[] build() {
        long[] t = new long[400];
        t[0] = 1;
        t[1] = 1;
        t[2] = 1;
        int n = 3;
        while (true) {
            try {
                t[n] = Math.addExact(t[n - 2], t[n - 3]);
            } catch (ArithmeticException ex) {
                break;
            }
            n++;
        }
        return Arrays.copyOf(t, n);
    }

    /** P(n). */
    public static long padovan(int n) {
        if (n < 0 || n > MAX_INDEX) {
            throw new IllegalArgumentException("index out of range: " + n);
        }
        return TABLE[n];
    }

    /** Smallest n with P(n) = v, or -1. */
    public static int indexOf(long v) {
        int i = Arrays.binarySearch(TABLE, v);
        if (i < 0) {
            return -1;
        }
        while (i > 0 && TABLE[i - 1] == v) {
            i--;
        }
        return i;
    }

    /** True when v is a Padovan side. */
    public static boolean isPadovan(long v) {
        return indexOf(v) >= 0;
    }

    /** P(a) + ... + P(b), exact; throws ArithmeticException on overflow. */
    public static long runSum(int a, int b) {
        if (a < 0 || b < a || b > MAX_INDEX) {
            throw new IllegalArgumentException("bad run: " + a + ".." + b);
        }
        long s = 0;
        for (int i = a; i <= b; i++) {
            s = Math.addExact(s, TABLE[i]);
        }
        return s;
    }

    /** Grade a claimed side P(n). */
    public static Grade grade(int n, long claimed) {
        return padovan(n) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: the plinth fits the spiral. Skip one, add the two before.";
            case SLIPPED -> "Forgemaster: the plinth slipped. Each side is the sum two and three back.";
        };
    }
}
