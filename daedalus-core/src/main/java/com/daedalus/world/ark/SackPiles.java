// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * G430 The Sack Piles: the quartermaster keeps n grain sacks in piles and each bell takes one sack
 * from every pile to start a new pile (Bulgarian solitaire). A layout is a partition of n, pile
 * sizes in non-increasing order. Every layout falls into a cycle; for triangular n = k(k+1)/2 the
 * cycle is the single staircase (k, k-1, ..., 1). Gives a step, the tail (bells before the cycle),
 * the cycle and the worst tail over all partitions of n.
 */
public final class SackPiles {

    public static final String QUEST_ID = "q_sack_piles";
    public static final int MAX_SACKS = 60;
    public static final int MAX_WORST = 30;

    private SackPiles() { }

    private static int check(int[] p) {
        if (p == null || p.length == 0) {
            throw new IllegalArgumentException("need at least one pile");
        }
        int n = 0;
        for (int i = 0; i < p.length; i++) {
            if (p[i] < 1 || (i > 0 && p[i] > p[i - 1])) {
                throw new IllegalArgumentException("piles must be positive and non-increasing");
            }
            n += p[i];
        }
        if (n > MAX_SACKS) {
            throw new IllegalArgumentException("at most " + MAX_SACKS + " sacks");
        }
        return n;
    }

    /** One bell: every pile gives a sack to a new pile. */
    public static int[] step(int[] p) {
        check(p);
        int[] out = new int[p.length + 1];
        out[0] = p.length;
        int m = 1;
        for (int v : p) {
            if (v > 1) {
                out[m++] = v - 1;
            }
        }
        int[] r = Arrays.copyOf(out, m);
        Arrays.sort(r);
        for (int i = 0, j = m - 1; i < j; i++, j--) {
            int t = r[i];
            r[i] = r[j];
            r[j] = t;
        }
        return r;
    }

    private static int[] rho(int[] p) {
        check(p);
        Map<String, Integer> seen = new HashMap<>();
        int[] cur = p.clone();
        int t = 0;
        while (!seen.containsKey(Arrays.toString(cur))) {
            seen.put(Arrays.toString(cur), t++);
            cur = step(cur);
        }
        int first = seen.get(Arrays.toString(cur));
        return new int[] {first, t - first};
    }

    /** Bells before the layout first enters its cycle. */
    public static int tail(int[] p) {
        return rho(p)[0];
    }

    /** Length of the cycle the layout falls into. */
    public static int cycleLength(int[] p) {
        return rho(p)[1];
    }

    /** The cycle's layouts in order, starting where the walk first enters it. */
    public static int[][] cycle(int[] p) {
        int[] r = rho(p);
        int[] cur = p.clone();
        for (int i = 0; i < r[0]; i++) {
            cur = step(cur);
        }
        int[][] out = new int[r[1]][];
        for (int i = 0; i < r[1]; i++) {
            out[i] = cur;
            cur = step(cur);
        }
        return out;
    }

    /** Every partition of n, each non-increasing. */
    public static List<int[]> partitions(int n) {
        if (n < 1 || n > MAX_WORST) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        List<int[]> out = new ArrayList<>();
        grow(n, n, new int[n], 0, out);
        return List.copyOf(out);
    }

    private static void grow(int left, int cap, int[] buf, int len, List<int[]> out) {
        if (left == 0) {
            out.add(Arrays.copyOf(buf, len));
            return;
        }
        for (int v = Math.min(left, cap); v >= 1; v--) {
            buf[len] = v;
            grow(left - v, v, buf, len + 1, out);
        }
    }

    /** Longest tail over all partitions of n (n up to 30). */
    public static int worstTail(int n) {
        int best = 0;
        for (int[] p : partitions(n)) {
            best = Math.max(best, tail(p));
        }
        return best;
    }

    /** Quest q_sack_piles: the quartermaster names the bells before this layout settles into its cycle. */
    public static boolean quest(int[] piles, int answer) {
        return tail(piles) == answer;
    }
}