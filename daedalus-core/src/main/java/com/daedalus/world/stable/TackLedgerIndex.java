// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G545 Tack Ledger Index (Studio horse lane): the tack room keeps one ledger card per horse, in
 * name order (card i for horse i), filed as a binary search tree; a lookup starts at the root card
 * and flips left or right until it reaches the wanted card. Each horse's card is asked for with a
 * seeded frequency. File the cards so the total flips (frequency times depth, root depth 1) is
 * least: the optimal binary search tree. {@link #best} is Knuth's exact interval DP;
 * {@link #mostAskedRoot} (put the most-asked card at the root, then recurse on each side) often
 * files a lopsided ledger. A filing is given as an insertion order (pre-order of the tree), since
 * inserting cards in that order rebuilds the tree. Plain int[] API; small and pure so it ports to C++.
 */
public final class TackLedgerIndex {

    public static final String QUEST_ID = "q_quick_ledger";
    public static final int INVALID = -1;

    /** A filing: total flips and the card insertion order (pre-order of the search tree). */
    public record Filing(long flips, int[] order) {
        public Filing {
            order = order.clone();
        }

        @Override
        public int[] order() {
            return order.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Filing f && f.flips == flips && Arrays.equals(f.order, order);
        }

        @Override
        public int hashCode() {
            return 31 * Long.hashCode(flips) + Arrays.hashCode(order);
        }

        @Override
        public String toString() {
            return "Filing[" + flips + ", " + Arrays.toString(order) + "]";
        }
    }

    private TackLedgerIndex() { }

    /** Seeded lookup frequencies in [1, maxFreq]. */
    public static int[] frequencies(long seed, int n, int maxFreq) {
        if (n < 0 || n > 512 || maxFreq < 1) {
            throw new IllegalArgumentException("bad ledger");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] f = new int[n];
        for (int i = 0; i < n; i++) {
            f[i] = 1 + rnd.nextInt(maxFreq);
        }
        return f;
    }

    /** Least total flips over all binary search trees (Knuth DP with root monotonicity). */
    public static Filing best(int[] freq) {
        check(freq);
        int n = freq.length;
        long[] prefix = new long[n + 1];
        for (int i = 0; i < n; i++) {
            prefix[i + 1] = prefix[i] + freq[i];
        }
        // cost[i][j], root[i][j] over cards i..j-1 (half-open), 0 <= i <= j <= n.
        long[][] cost = new long[n + 1][n + 1];
        int[][] root = new int[n + 1][n + 1];
        for (int i = 0; i < n; i++) {
            cost[i][i + 1] = freq[i];
            root[i][i + 1] = i;
        }
        for (int len = 2; len <= n; len++) {
            for (int i = 0; i + len <= n; i++) {
                int j = i + len;
                long bestCost = Long.MAX_VALUE;
                int bestRoot = -1;
                for (int r = root[i][j - 1]; r <= root[i + 1][j]; r++) {
                    long c = cost[i][r] + cost[r + 1][j];
                    if (c < bestCost) {
                        bestCost = c;
                        bestRoot = r;
                    }
                }
                cost[i][j] = bestCost + prefix[j] - prefix[i];
                root[i][j] = bestRoot;
            }
        }
        int[] order = new int[n];
        int[] at = {0};
        preorder(root, 0, n, order, at);
        return new Filing(cost[0][n], order);
    }

    private static void preorder(int[][] root, int i, int j, int[] order, int[] at) {
        if (i >= j) {
            return;
        }
        int r = root[i][j];
        order[at[0]++] = r;
        preorder(root, i, r, order, at);
        preorder(root, r + 1, j, order, at);
    }

    /** Naive habit: most-asked card at the root of each range (ties to the lower card). */
    public static Filing mostAskedRoot(int[] freq) {
        check(freq);
        int n = freq.length;
        int[] order = new int[n];
        int[] at = {0};
        greedy(freq, 0, n, order, at);
        return new Filing(flips(freq, order), order);
    }

    private static void greedy(int[] freq, int i, int j, int[] order, int[] at) {
        if (i >= j) {
            return;
        }
        int r = i;
        for (int k = i + 1; k < j; k++) {
            if (freq[k] > freq[r]) {
                r = k;
            }
        }
        order[at[0]++] = r;
        greedy(freq, i, r, order, at);
        greedy(freq, r + 1, j, order, at);
    }

    /** Total flips when cards are inserted in {@code order}, or INVALID unless it is a permutation of 0..n-1. */
    public static long flips(int[] freq, int[] order) {
        check(freq);
        int n = freq.length;
        if (order.length != n) {
            return INVALID;
        }
        boolean[] seen = new boolean[n];
        int[] left = new int[n];
        int[] right = new int[n];
        Arrays.fill(left, -1);
        Arrays.fill(right, -1);
        long total = 0;
        for (int k = 0; k < n; k++) {
            int c = order[k];
            if (c < 0 || c >= n || seen[c]) {
                return INVALID;
            }
            seen[c] = true;
            int depth = 1;
            if (k > 0) {
                int v = order[0];
                while (true) {
                    depth++;
                    if (c < v) {
                        if (left[v] < 0) {
                            left[v] = c;
                            break;
                        }
                        v = left[v];
                    } else {
                        if (right[v] < 0) {
                            right[v] = c;
                            break;
                        }
                        v = right[v];
                    }
                }
            }
            total += (long) depth * freq[c];
        }
        return total;
    }

    /** Quest q_quick_ledger: the filing holds every card once and needs the fewest flips. */
    public static boolean quest(int[] freq, int[] order) {
        long got = flips(freq, order);
        return got != INVALID && got == best(freq).flips();
    }

    private static void check(int[] freq) {
        for (int f : freq) {
            if (f < 0) {
                throw new IllegalArgumentException("negative frequency");
            }
        }
    }
}
