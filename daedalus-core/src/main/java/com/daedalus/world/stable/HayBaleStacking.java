// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G542 Hay Bale Stacking (Studio horse lane): build the tallest stack from seeded hay bales. Each
 * bale has a footprint (two sides, and it may be turned), a height, a weight and a strength. A bale
 * may sit on another only when it is strictly smaller on both footprint sides, and the total weight
 * of all bales above a bale may not exceed its strength (box stacking with load limits).
 * {@link #best} is exact: bales are only ever stacked in footprint order, so a DP over (bottom bale,
 * weight of the stack) finds the tallest legal stack. {@link #biggestFirst} (lay the biggest
 * footprint first and add any bale that still fits on top) can crush itself early. Plain int[] API,
 * at most 16 bales with weights up to {@code MAX_WEIGHT}; small and pure so it ports to C++ for Unreal.
 */
public final class HayBaleStacking {

    public static final String QUEST_ID = "q_tall_stack";
    public static final int MAX_BALES = 16;
    public static final int MAX_WEIGHT = 9;
    public static final int INVALID = -1;

    /** Bales: footprint sides a and b, height, weight and strength per bale. */
    public record Bales(int[] a, int[] b, int[] height, int[] weight, int[] strength) {
        public Bales {
            a = a.clone();
            b = b.clone();
            height = height.clone();
            weight = weight.clone();
            strength = strength.clone();
            int n = a.length;
            if (n > MAX_BALES || b.length != n || height.length != n || weight.length != n || strength.length != n) {
                throw new IllegalArgumentException("bad bales");
            }
            for (int i = 0; i < n; i++) {
                if (a[i] < 1 || b[i] < 1 || height[i] < 1 || weight[i] < 1 || weight[i] > MAX_WEIGHT || strength[i] < 0) {
                    throw new IllegalArgumentException("bad bale " + i);
                }
            }
        }

        @Override
        public int[] a() {
            return a.clone();
        }

        @Override
        public int[] b() {
            return b.clone();
        }

        @Override
        public int[] height() {
            return height.clone();
        }

        @Override
        public int[] weight() {
            return weight.clone();
        }

        @Override
        public int[] strength() {
            return strength.clone();
        }

        /** Number of bales. */
        public int size() {
            return a.length;
        }

        /** True when bale {@code top} may sit directly on bale {@code bottom} (turning either as needed). */
        public boolean fitsOn(int top, int bottom) {
            int ts = Math.min(a[top], b[top]);
            int tl = Math.max(a[top], b[top]);
            int bs = Math.min(a[bottom], b[bottom]);
            int bl = Math.max(a[bottom], b[bottom]);
            return ts < bs && tl < bl;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Bales x && Arrays.equals(x.a, a) && Arrays.equals(x.b, b) && Arrays.equals(x.height, height)
                    && Arrays.equals(x.weight, weight) && Arrays.equals(x.strength, strength);
        }

        @Override
        public int hashCode() {
            return Arrays.hashCode(new int[] {Arrays.hashCode(a), Arrays.hashCode(b), Arrays.hashCode(height),
                Arrays.hashCode(weight), Arrays.hashCode(strength)});
        }

        @Override
        public String toString() {
            return "Bales[a=" + Arrays.toString(a) + ", b=" + Arrays.toString(b) + ", h=" + Arrays.toString(height)
                    + ", w=" + Arrays.toString(weight) + ", s=" + Arrays.toString(strength) + "]";
        }
    }

    /** A stack: total height and bale ids from bottom to top. */
    public record Stack(int height, int[] bottomUp) {
        public Stack {
            bottomUp = bottomUp.clone();
        }

        @Override
        public int[] bottomUp() {
            return bottomUp.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Stack s && s.height == height && Arrays.equals(s.bottomUp, bottomUp);
        }

        @Override
        public int hashCode() {
            return 31 * height + Arrays.hashCode(bottomUp);
        }

        @Override
        public String toString() {
            return "Stack[" + height + ", " + Arrays.toString(bottomUp) + "]";
        }
    }

    private HayBaleStacking() { }

    /** Seeded bales: sides in [1, 12], height in [1, 9], weight in [1, 5], strength in [0, 10]. */
    public static Bales bales(long seed, int n) {
        if (n < 0 || n > MAX_BALES) {
            throw new IllegalArgumentException("bad bale count");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] a = new int[n];
        int[] b = new int[n];
        int[] h = new int[n];
        int[] w = new int[n];
        int[] s = new int[n];
        for (int i = 0; i < n; i++) {
            a[i] = 1 + rnd.nextInt(12);
            b[i] = 1 + rnd.nextInt(12);
            h[i] = 1 + rnd.nextInt(9);
            w[i] = 1 + rnd.nextInt(5);
            s[i] = rnd.nextInt(11);
        }
        return new Bales(a, b, h, w, s);
    }

    /** Tallest legal stack (exact DP over bottom bale and stack weight). */
    public static Stack best(Bales bales) {
        int n = bales.size();
        int cap = n * MAX_WEIGHT;
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        Arrays.sort(order, (x, y) -> Integer.compare(area(bales, x), area(bales, y)));
        // tall[i][w]: tallest stack with bottom bale i weighing exactly w in total, or -1; next[i][w] = bale on i.
        int[][] tall = new int[n][cap + 1];
        int[][] next = new int[n][cap + 1];
        for (int[] row : tall) {
            Arrays.fill(row, -1);
        }
        for (int oi = 0; oi < n; oi++) {
            int i = order[oi];
            int wi = bales.weight[i];
            tall[i][wi] = bales.height[i];
            next[i][wi] = -1;
            for (int oj = 0; oj < oi; oj++) {
                int j = order[oj];
                if (!bales.fitsOn(j, i)) {
                    continue;
                }
                for (int w = 1; w <= Math.min(cap - wi, bales.strength[i]); w++) {
                    if (tall[j][w] >= 0 && tall[j][w] + bales.height[i] > tall[i][w + wi]) {
                        tall[i][w + wi] = tall[j][w] + bales.height[i];
                        next[i][w + wi] = j;
                    }
                }
            }
        }
        int bh = 0;
        int bi = -1;
        int bw = 0;
        for (int i = 0; i < n; i++) {
            for (int w = 0; w <= cap; w++) {
                if (tall[i][w] > bh) {
                    bh = tall[i][w];
                    bi = i;
                    bw = w;
                }
            }
        }
        int[] chain = new int[n];
        int len = 0;
        while (bi >= 0) {
            chain[len++] = bi;
            int j = next[bi][bw];
            bw -= bales.weight[bi];
            bi = j;
        }
        return new Stack(bh, Arrays.copyOf(chain, len));
    }

    private static int area(Bales bales, int i) {
        return bales.a[i] * bales.b[i];
    }

    /** Naive habit: lay bales biggest footprint first, keeping each one that still fits and is carried. */
    public static Stack biggestFirst(Bales bales) {
        int n = bales.size();
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        Arrays.sort(order, (x, y) -> area(bales, y) != area(bales, x) ? Integer.compare(area(bales, y), area(bales, x))
                : Integer.compare(x, y));
        int[] chain = new int[n];
        int len = 0;
        for (int i : order) {
            chain[len] = i;
            if (stack(bales, Arrays.copyOf(chain, len + 1)) != INVALID) {
                len++;
            }
        }
        int[] picked = Arrays.copyOf(chain, len);
        return new Stack(stack(bales, picked), picked);
    }

    /** Height of a bottom-up stack, or INVALID when a bale does not fit, is overloaded or repeats. */
    public static int stack(Bales bales, int[] bottomUp) {
        int n = bales.size();
        boolean[] used = new boolean[n];
        int height = 0;
        for (int k = 0; k < bottomUp.length; k++) {
            int i = bottomUp[k];
            if (i < 0 || i >= n || used[i] || (k > 0 && !bales.fitsOn(i, bottomUp[k - 1]))) {
                return INVALID;
            }
            used[i] = true;
            height += bales.height[i];
        }
        int above = 0;
        for (int k = bottomUp.length - 1; k >= 0; k--) {
            int i = bottomUp[k];
            if (above > bales.strength[i]) {
                return INVALID;
            }
            above += bales.weight[i];
        }
        return height;
    }

    /** Quest q_tall_stack: the stable hand's stack stands and is as tall as possible. */
    public static boolean quest(Bales bales, int[] bottomUp) {
        int got = stack(bales, bottomUp);
        return got != INVALID && got == best(bales).height();
    }
}
