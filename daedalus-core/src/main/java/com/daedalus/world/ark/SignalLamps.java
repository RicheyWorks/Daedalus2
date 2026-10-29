// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G228 The Signal Lamps: the ark signals with {@code n} mast lamps (bit {@code j} = lamp
 * {@code j} lit). On each bell the lamplighter flips exactly one lamp, and the watch must see
 * every one of the {@code 2^n} patterns once before the mast goes dark again. The reflected
 * Gray code {@code g(i) = i ^ (i >> 1)} is such a tour; {@link #rank} inverts it and
 * {@link #flipAt} names the lamp to flip on each bell.
 */
public final class SignalLamps {

    public static final String QUEST_ID = "q_signal_lamps";

    /** Largest mast that {@link #tour} will list in full. */
    public static final int MAX_TOUR_LAMPS = 20;

    private SignalLamps() { }

    private static void checkLamps(int n, int max) {
        if (n < 1 || n > max) {
            throw new IllegalArgumentException("lamps must be in 1.." + max);
        }
    }

    /** Pattern shown on bell {@code i}. */
    public static int pattern(int i) {
        if (i < 0) {
            throw new IllegalArgumentException("negative bell");
        }
        return i ^ (i >>> 1);
    }

    /** Bell on which {@code pattern} is shown. */
    public static int rank(int pattern) {
        if (pattern < 0) {
            throw new IllegalArgumentException("negative pattern");
        }
        int b = pattern;
        for (int s = 1; s < 32; s <<= 1) {
            b ^= b >>> s;
        }
        return b;
    }

    /** Lamp to flip after bell {@code i} on an {@code n}-lamp mast (last bell returns to dark). */
    public static int flipAt(int n, int i) {
        checkLamps(n, 30);
        int size = 1 << n;
        if (i < 0 || i >= size) {
            throw new IllegalArgumentException("bell out of range");
        }
        return i == size - 1 ? n - 1 : Integer.numberOfTrailingZeros(i + 1);
    }

    /** Every pattern in tour order, starting dark. */
    public static int[] tour(int n) {
        checkLamps(n, MAX_TOUR_LAMPS);
        int[] t = new int[1 << n];
        for (int i = 0; i < t.length; i++) {
            t[i] = pattern(i);
        }
        return t;
    }

    /** True when {@code watched} is a full single-flip tour of an {@code n}-lamp mast. */
    public static boolean validTour(int n, int[] watched) {
        checkLamps(n, MAX_TOUR_LAMPS);
        int size = 1 << n;
        if (watched.length != size || watched[0] != 0) {
            return false;
        }
        boolean[] seen = new boolean[size];
        for (int i = 0; i < size; i++) {
            int p = watched[i];
            if (p < 0 || p >= size || seen[p]) {
                return false;
            }
            seen[p] = true;
            int next = watched[(i + 1) % size];
            if (Integer.bitCount(p ^ next) != 1) {
                return false;
            }
        }
        return true;
    }

    /** Quest q_signal_lamps: the lamplighter's log must be a valid tour. */
    public static boolean quest(int n, int[] watched) {
        return validTour(n, watched);
    }
}
