// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G345 The Beacon Weights: the lamplighter hangs weights on the beacon so that every pair (a weight
 * may pair with itself) balances at a different total, a Sidon set. The greedy Mian-Chowla rule
 * picks each next smallest weight that keeps the set Sidon, and a backtracking search finds the
 * largest Sidon set inside 1..n for small n.
 */
public final class BeaconWeights {

    public static final String QUEST_ID = "q_beacon_weights";

    private BeaconWeights() { }

    /** True when the weights are positive, distinct, and all sums a + b (a &lt;= b) differ. */
    public static boolean isSidon(int[] weights) {
        int[] w = weights.clone();
        Arrays.sort(w);
        if (w.length == 0 || w[0] < 1 || w[w.length - 1] > 1_000_000) {
            return w.length == 0;
        }
        boolean[] seen = new boolean[2 * w[w.length - 1] + 1];
        for (int i = 0; i < w.length; i++) {
            if (i > 0 && w[i] == w[i - 1]) {
                return false;
            }
            for (int j = i; j < w.length; j++) {
                int s = w[i] + w[j];
                if (seen[s]) {
                    return false;
                }
                seen[s] = true;
            }
        }
        return true;
    }

    /** First count terms of the Mian-Chowla sequence (count up to 200). */
    public static int[] mianChowla(int count) {
        if (count < 0 || count > 200) {
            throw new IllegalArgumentException("count 0..200");
        }
        int[] out = new int[count];
        boolean[] sums = new boolean[4_000_000];
        int n = 0;
        int cand = 1;
        while (n < count) {
            boolean ok = !sums[2 * cand];
            for (int i = 0; ok && i < n; i++) {
                ok = !sums[out[i] + cand];
            }
            if (ok) {
                out[n++] = cand;
                for (int i = 0; i < n; i++) {
                    sums[out[i] + cand] = true;
                }
            }
            cand++;
        }
        return out;
    }

    /** A largest Sidon subset of 1..n (n up to 40). */
    public static int[] largest(int n) {
        if (n < 1 || n > 40) {
            throw new IllegalArgumentException("n 1..40");
        }
        int[] best = new int[0];
        int[] cur = new int[n];
        boolean[] diff = new boolean[n + 1];
        return grow(n, 1, cur, 0, diff, best);
    }

    private static int[] grow(int n, int next, int[] cur, int size, boolean[] diff, int[] best) {
        int[] b = best;
        if (size > b.length) {
            b = Arrays.copyOf(cur, size);
        }
        for (int v = next; v <= n; v++) {
            if (size + (n - v + 1) <= b.length) {
                break;
            }
            boolean ok = true;
            for (int i = 0; ok && i < size; i++) {
                ok = !diff[v - cur[i]];
            }
            if (ok) {
                for (int i = 0; i < size; i++) {
                    diff[v - cur[i]] = true;
                }
                cur[size] = v;
                b = grow(n, v + 1, cur, size + 1, diff, b);
                for (int i = 0; i < size; i++) {
                    diff[v - cur[i]] = false;
                }
            }
        }
        return b;
    }

    /** Quest q_beacon_weights: hang k Sidon weights, none heavier than limit. */
    public static boolean quest(int k, int limit, int[] answer) {
        if (answer.length != k || !isSidon(answer)) {
            return false;
        }
        for (int w : answer) {
            if (w > limit) {
                return false;
            }
        }
        return true;
    }
}