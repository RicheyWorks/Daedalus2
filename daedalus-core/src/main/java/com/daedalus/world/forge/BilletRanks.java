// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Billet Ranks (contest gap G326): billets arrive and leave the cooling rack, and the quartermaster asks for the k-th
 * lightest billet or how many weigh less than a given weight.
 *
 * <p>The tool is plain: an order-statistic treap stored in parallel arrays (node 0 is the empty sentinel), with seeded
 * priorities, split/merge and subtree sizes, so add, remove, kth and rank are O(log n) expected. It is a multiset of
 * {@code long} keys. Any project can use it for leaderboards, percentiles or sliding order statistics.
 */
public final class BilletRanks {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_billet_ranks";

    /** How a shift went. */
    public enum Grade { RACKED, JUMBLED }

    private long[] key = new long[16];
    private long[] pri = new long[16];
    private int[] left = new int[16];
    private int[] right = new int[16];
    private int[] size = new int[16];
    private int used = 1;
    private int root;
    private final SplittableRandom rng;

    /** An empty rack; same seed, same tree shapes. */
    public BilletRanks(long seed) {
        this.rng = new SplittableRandom(seed);
    }

    /** Number of billets on the rack. */
    public int size() {
        return size[root];
    }

    private int node(long k) {
        if (used == key.length) {
            int n = used * 2;
            key = Arrays.copyOf(key, n);
            pri = Arrays.copyOf(pri, n);
            left = Arrays.copyOf(left, n);
            right = Arrays.copyOf(right, n);
            size = Arrays.copyOf(size, n);
        }
        key[used] = k;
        pri[used] = rng.nextLong();
        size[used] = 1;
        return used++;
    }

    private void pull(int t) {
        size[t] = 1 + size[left[t]] + size[right[t]];
    }

    /** Split t into keys < k (out[0]) and keys >= k (out[1]). */
    private void split(int t, long k, int[] out) {
        if (t == 0) {
            out[0] = 0;
            out[1] = 0;
            return;
        }
        if (key[t] < k) {
            split(right[t], k, out);
            right[t] = out[0];
            pull(t);
            out[0] = t;
        } else {
            split(left[t], k, out);
            left[t] = out[1];
            pull(t);
            out[1] = t;
        }
    }

    private int merge(int a, int b) {
        if (a == 0) {
            return b;
        }
        if (b == 0) {
            return a;
        }
        if (pri[a] > pri[b]) {
            right[a] = merge(right[a], b);
            pull(a);
            return a;
        }
        left[b] = merge(a, left[b]);
        pull(b);
        return b;
    }

    /** Put a billet of weight k on the rack. */
    public void add(long k) {
        int[] p = new int[2];
        split(root, k, p);
        root = merge(merge(p[0], node(k)), p[1]);
    }

    /** Take one billet of weight k off the rack; false if none. */
    public boolean remove(long k) {
        int[] p = new int[2];
        split(root, k, p);
        int[] q = new int[2];
        split(p[1], k + 1, q);
        boolean had = q[0] != 0;
        if (had) {
            q[0] = merge(left[q[0]], right[q[0]]);
        }
        root = merge(p[0], merge(q[0], q[1]));
        return had;
    }

    /** Number of billets lighter than k. */
    public int rank(long k) {
        int r = 0;
        int t = root;
        while (t != 0) {
            if (key[t] < k) {
                r += size[left[t]] + 1;
                t = right[t];
            } else {
                t = left[t];
            }
        }
        return r;
    }

    /** The k-th lightest billet, 0-based. */
    public long kth(int k) {
        if (k < 0 || k >= size()) {
            throw new IndexOutOfBoundsException("no billet at rank " + k);
        }
        int t = root;
        int i = k;
        while (true) {
            int ls = size[left[t]];
            if (i < ls) {
                t = left[t];
            } else if (i == ls) {
                return key[t];
            } else {
                i -= ls + 1;
                t = right[t];
            }
        }
    }

    /** A seeded script: positive entries add that weight, negative entries remove its absolute value. */
    public static long[] script(long seed, int n, int maxWeight) {
        if (n < 0 || maxWeight < 1) {
            throw new IllegalArgumentException("need n >= 0 and maxWeight >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[] s = new long[n];
        for (int i = 0; i < n; i++) {
            long w = 1 + r.nextInt(maxWeight);
            s[i] = r.nextInt(3) == 0 ? -w : w;
        }
        return s;
    }

    /** RACKED only if the claimed k-th weight is right. */
    public Grade grade(int k, long claimed) {
        return k >= 0 && k < size() && kth(k) == claimed ? Grade.RACKED : Grade.JUMBLED;
    }

    /** The Forgemaster's line for a shift. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case RACKED -> "Forgemaster: you knew every billet's place without lifting one. A true quartermaster.";
            case JUMBLED -> "Forgemaster: that is not the billet I asked for. Recount the rack.";
        };
    }
}
