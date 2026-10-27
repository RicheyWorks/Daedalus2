// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G225 The Watch Circle: the ark crew, numbered 1..n, stand in a circle and count off from
 * sailor 1; every k-th sailor leaves for the night watch and counting resumes with the next
 * sailor, until one is left to keep the log. {@link #survivor} uses the O(n) Josephus
 * recurrence {@code J(i) = (J(i-1) + k) mod i}; {@link #order} gives the full departure order in
 * O(n log n) with a Fenwick tree.
 */
public final class WatchCircle {

    public static final String QUEST_ID = "q_watch_circle";

    private WatchCircle() { }

    private static void check(int n, int k) {
        if (n < 1 || k < 1) {
            throw new IllegalArgumentException("need n >= 1 and k >= 1");
        }
    }

    /** Number (1-based) of the sailor left to keep the log. */
    public static int survivor(int n, int k) {
        check(n, k);
        long j = 0;
        for (int i = 2; i <= n; i++) {
            j = (j + k) % i;
        }
        return (int) j + 1;
    }

    /** Sailors in the order they leave; the last entry is the log-keeper. */
    public static int[] order(int n, int k) {
        check(n, k);
        int[] tree = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            tree[i] += 1;
            int p = i + (i & -i);
            if (p <= n) {
                tree[p] += tree[i];
            }
        }
        int top = Integer.highestOneBit(n);
        int[] out = new int[n];
        long idx = 0;
        for (int m = n; m >= 1; m--) {
            idx = (idx + k - 1) % m;
            int want = (int) idx + 1;
            int pos = 0;
            for (int step = top; step > 0; step >>= 1) {
                int nxt = pos + step;
                if (nxt <= n && tree[nxt] < want) {
                    pos = nxt;
                    want -= tree[nxt];
                }
            }
            int sailor = pos + 1;
            out[n - m] = sailor;
            for (int i = sailor; i <= n; i += i & -i) {
                tree[i] -= 1;
            }
        }
        return out;
    }

    /** Quest q_watch_circle: stand where the count leaves you as log-keeper. */
    public static boolean quest(int n, int k, int standAt) {
        return standAt == survivor(n, k);
    }
}
