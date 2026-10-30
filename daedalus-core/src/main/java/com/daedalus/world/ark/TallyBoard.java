// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G279 The Tally Board: the purser keeps the ark's stores, bin by bin, on a Fenwick (binary
 * indexed) tree. Adding to a bin and summing any run of bins both cost O(log n), and the purser
 * can find the first bin where the running total reaches a target in O(log n) as well. Bins are
 * 0-based; counts are non-negative longs.
 */
public final class TallyBoard {

    public static final String QUEST_ID = "q_tally_board";

    private final long[] tree;
    private final long[] bins;

    public TallyBoard(int n) {
        if (n < 1) {
            throw new IllegalArgumentException("need at least one bin: " + n);
        }
        tree = new long[n + 1];
        bins = new long[n];
    }

    /** Builds a board from starting counts in O(n). */
    public static TallyBoard of(long[] counts) {
        TallyBoard b = new TallyBoard(counts.length);
        for (int i = 0; i < counts.length; i++) {
            if (counts[i] < 0) {
                throw new IllegalArgumentException("negative count at bin " + i);
            }
            b.bins[i] = counts[i];
            b.tree[i + 1] += counts[i];
            int parent = i + 1 + ((i + 1) & -(i + 1));
            if (parent <= counts.length) {
                b.tree[parent] += b.tree[i + 1];
            }
        }
        return b;
    }

    public int size() {
        return bins.length;
    }

    public long get(int bin) {
        check(bin);
        return bins[bin];
    }

    private void check(int bin) {
        if (bin < 0 || bin >= bins.length) {
            throw new IllegalArgumentException("bin out of range: " + bin);
        }
    }

    /** Adds delta to a bin; the bin may not go negative. */
    public void add(int bin, long delta) {
        check(bin);
        if (bins[bin] + delta < 0) {
            throw new IllegalArgumentException("bin " + bin + " would go negative");
        }
        bins[bin] += delta;
        for (int i = bin + 1; i < tree.length; i += i & -i) {
            tree[i] += delta;
        }
    }

    /** Sum of bins 0..bin-1 (bin may equal size()). */
    public long prefix(int bin) {
        if (bin < 0 || bin > bins.length) {
            throw new IllegalArgumentException("prefix out of range: " + bin);
        }
        long s = 0;
        for (int i = bin; i > 0; i -= i & -i) {
            s += tree[i];
        }
        return s;
    }

    /** Sum of bins from..to-1. */
    public long range(int from, int to) {
        if (from > to) {
            throw new IllegalArgumentException("from > to");
        }
        return prefix(to) - prefix(from);
    }

    public long total() {
        return prefix(bins.length);
    }

    /** Smallest bin b with prefix(b + 1) >= target, or -1 when the total falls short. */
    public int firstReaching(long target) {
        if (target <= 0) {
            return 0;
        }
        int pos = 0;
        long rem = target;
        int step = Integer.highestOneBit(bins.length);
        for (; step > 0; step >>= 1) {
            int next = pos + step;
            if (next <= bins.length && tree[next] < rem) {
                pos = next;
                rem -= tree[next];
            }
        }
        return pos < bins.length ? pos : -1;
    }

    /** Quest q_tally_board: name the first bin where the running stores reach the target. */
    public static boolean quest(long[] counts, long target, int answer) {
        return of(counts).firstReaching(target) == answer;
    }
}