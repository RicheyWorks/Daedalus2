// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Nesting Crucibles (contest gap G210): to ship spare crucibles ({@link CrucibleLoads}) on an ark, nest them. One fits
 * inside another only if it is strictly narrower and strictly shorter. Find the longest nest in a pile.
 *
 * <p>The tool is plain: {@link #lis} is the O(n log n) longest strictly increasing subsequence of an {@code int[]}
 * (patience piles with binary search, returning indices), and {@link #nest} reduces 2D nesting of {@code {w, h}} pairs
 * to it by sorting width ascending and height descending on ties. Any project can use it for upgrade paths or combo
 * chains.
 */
public final class NestingCrucibles {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_nesting_crucibles";

    /** How the player's nest went. */
    public enum Grade { NESTED, LOOSE, BROKEN }

    private NestingCrucibles() {
    }

    /** {@code n} seeded crucibles with width and height in [1, size]. Same seed, same pile. */
    public static int[][] pile(long seed, int n, int size) {
        if (n < 0 || size < 1) {
            throw new IllegalArgumentException("need n >= 0 and size >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] p = new int[n][];
        for (int i = 0; i < n; i++) {
            p[i] = new int[] {1 + r.nextInt(size), 1 + r.nextInt(size)};
        }
        return p;
    }

    /** Indices of one longest strictly increasing subsequence of {@code a}, in order. */
    public static List<Integer> lis(int[] a) {
        int n = a.length;
        int[] tailIdx = new int[n];
        int[] prev = new int[n];
        int len = 0;
        for (int i = 0; i < n; i++) {
            int lo = 0;
            int hi = len;
            while (lo < hi) {
                int mid = (lo + hi) >>> 1;
                if (a[tailIdx[mid]] < a[i]) {
                    lo = mid + 1;
                } else {
                    hi = mid;
                }
            }
            prev[i] = lo > 0 ? tailIdx[lo - 1] : -1;
            tailIdx[lo] = i;
            if (lo == len) {
                len++;
            }
        }
        Integer[] out = new Integer[len];
        for (int k = len - 1, i = len > 0 ? tailIdx[len - 1] : -1; k >= 0; k--, i = prev[i]) {
            out[k] = i;
        }
        return Arrays.asList(out);
    }

    /** True if crucible {@code a} fits strictly inside crucible {@code b}. */
    public static boolean fits(int[] a, int[] b) {
        return a[0] < b[0] && a[1] < b[1];
    }

    /** Indices of one longest nest, innermost first. */
    public static List<Integer> nest(int[][] pile) {
        Integer[] ord = new Integer[pile.length];
        for (int i = 0; i < ord.length; i++) {
            if (pile[i].length != 2) {
                throw new IllegalArgumentException("a crucible is {width, height}");
            }
            ord[i] = i;
        }
        Arrays.sort(ord, (x, y) -> pile[x][0] != pile[y][0] ? Integer.compare(pile[x][0], pile[y][0])
                : pile[x][1] != pile[y][1] ? Integer.compare(pile[y][1], pile[x][1]) : Integer.compare(x, y));
        int[] h = new int[ord.length];
        for (int k = 0; k < ord.length; k++) {
            h[k] = pile[ord[k]][1];
        }
        List<Integer> out = new ArrayList<>();
        for (int k : lis(h)) {
            out.add(ord[k]);
        }
        return out;
    }

    /** NESTED if every step fits and the nest is longest, LOOSE if it fits but is shorter, BROKEN otherwise. */
    public static Grade grade(int[][] pile, List<Integer> chain) {
        for (int k = 1; k < chain.size(); k++) {
            if (!fits(pile[chain.get(k - 1)], pile[chain.get(k)])) {
                return Grade.BROKEN;
            }
        }
        return chain.size() == nest(pile).size() ? Grade.NESTED : Grade.LOOSE;
    }

    /** The Forgemaster's line for a nest. */
    public static String forgemasterLine(Grade g, int size) {
        return switch (g) {
            case NESTED -> "Forgemaster: " + size + " deep. Not a hand's breadth of hold wasted.";
            case LOOSE -> "Forgemaster: " + size + " deep. They fit, but more would have.";
            case BROKEN -> "Forgemaster: that one will not go in. You will crack the rim.";
        };
    }
}
