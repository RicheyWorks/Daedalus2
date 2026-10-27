// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Ingot Rack Banner (contest gap G224): the forge stacks ingots from {@link IngotCuts} in columns against the wall, and
 * the guild hangs one rectangular banner flat against the stacks. It may not overhang an empty gap. Find the biggest
 * banner.
 *
 * <p>The tool is plain: {@link #largest} is the O(n) monotonic-stack largest rectangle in a histogram over an
 * {@code int[]}, and {@link #maximalRectangle} the largest all-solid rectangle in a {@code boolean[][]} grid (one
 * histogram per row). Any project can use it for the largest free area for building placement or UI packing.
 */
public final class IngotRackBanner {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_ingot_rack_banner";

    /** How a banner went. */
    public enum Grade { GRAND, MODEST, TORN }

    /** A banner over columns [from, to] (inclusive) up to {@code height}; area = width x height. */
    public record Banner(int from, int to, int height) {

        /** Banner area. */
        public long area() {
            return (long) (to - from + 1) * height;
        }
    }

    private IngotRackBanner() {
    }

    /** {@code n} seeded stacks of 0..maxHeight ingots. Same seed, same rack. */
    public static int[] stacks(long seed, int n, int maxHeight) {
        if (n < 0 || maxHeight < 0) {
            throw new IllegalArgumentException("need n >= 0 and maxHeight >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] h = new int[n];
        for (int i = 0; i < n; i++) {
            h[i] = r.nextInt(maxHeight + 1);
        }
        return h;
    }

    /** The largest banner (earliest on ties); a zero-area banner at column 0 for an empty or all-zero rack. */
    public static Banner largest(int[] h) {
        int n = h.length;
        int[] st = new int[n + 1];
        int top = 0;
        Banner best = new Banner(0, 0, 0);
        for (int i = 0; i <= n; i++) {
            int cur = i == n ? -1 : h[i];
            if (cur < -1 || (i < n && cur < 0)) {
                throw new IllegalArgumentException("negative stack at " + i);
            }
            while (top > 0 && h[st[top - 1]] > cur) {
                int height = h[st[--top]];
                int from = top == 0 ? 0 : st[top - 1] + 1;
                Banner b = new Banner(from, i - 1, height);
                if (b.area() > best.area() || (b.area() == best.area() && b.area() > 0 && from < best.from())) {
                    best = b;
                }
            }
            st[top++] = i;
        }
        return best;
    }

    /** Area of the largest all-solid rectangle in a grid. */
    public static long maximalRectangle(boolean[][] solid) {
        if (solid.length == 0) {
            return 0;
        }
        int cols = solid[0].length;
        int[] h = new int[cols];
        long best = 0;
        for (boolean[] row : solid) {
            if (row.length != cols) {
                throw new IllegalArgumentException("grid must be rectangular");
            }
            for (int j = 0; j < cols; j++) {
                h[j] = row[j] ? h[j] + 1 : 0;
            }
            best = Math.max(best, largest(h).area());
        }
        return best;
    }

    /** TORN if the banner overhangs a lower stack, GRAND at the largest area, MODEST at 75% or more, else TORN too. */
    public static Grade grade(int[] h, Banner b) {
        if (b.from() < 0 || b.to() >= h.length || b.from() > b.to() || b.height() < 0) {
            return Grade.TORN;
        }
        for (int i = b.from(); i <= b.to(); i++) {
            if (h[i] < b.height()) {
                return Grade.TORN;
            }
        }
        long best = largest(h).area();
        if (b.area() == best) {
            return Grade.GRAND;
        }
        return 4 * b.area() >= 3 * best ? Grade.MODEST : Grade.TORN;
    }

    /** The Forgemaster's line for a banner. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case GRAND -> "Forgemaster: the guild crest fills the wall. Every smith on the island will see it.";
            case MODEST -> "Forgemaster: it hangs true, but there is wall to spare.";
            case TORN -> "Forgemaster: it sags over a gap or barely covers a stack. Rehang it.";
        };
    }
}
