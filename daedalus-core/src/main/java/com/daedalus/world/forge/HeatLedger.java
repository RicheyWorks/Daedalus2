// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Heat Ledger (contest gap G241): through a shift the bellows add or bleed heat over spans of a row of forges, and the
 * ledger clerk must answer the total heat and the hottest forge on any span between blasts.
 *
 * <p>The tool is plain: a lazy-propagation segment tree over a {@code long[]} with range add, range sum and range max
 * in O(log n) each. Any project can use it for batched range updates with range queries.
 */
public final class HeatLedger {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_heat_ledger";

    /** How a clerk's answers went. */
    public enum Grade { BALANCED, SMUDGED }

    private final int n;
    private final long[] sum;
    private final long[] max;
    private final long[] lazy;

    /** Builds the ledger over a copy of the starting heats. */
    public HeatLedger(long[] start) {
        n = start.length;
        int size = Math.max(1, 4 * n);
        sum = new long[size];
        max = new long[size];
        lazy = new long[size];
        if (n > 0) {
            build(1, 0, n - 1, start);
        }
    }

    /** Seeded blasts: each row is {from, to, delta} with delta in -maxDelta..maxDelta. Same seed, same shift. */
    public static long[][] blasts(long seed, int n, int count, int maxDelta) {
        if (n < 1 || count < 0 || maxDelta < 0) {
            throw new IllegalArgumentException("need n >= 1, count >= 0, maxDelta >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[][] out = new long[count][];
        for (int i = 0; i < count; i++) {
            int a = r.nextInt(n);
            int b = r.nextInt(n);
            out[i] = new long[] {Math.min(a, b), Math.max(a, b), r.nextInt(2 * maxDelta + 1) - maxDelta};
        }
        return out;
    }

    private void build(int node, int lo, int hi, long[] a) {
        if (lo == hi) {
            sum[node] = a[lo];
            max[node] = a[lo];
            return;
        }
        int mid = (lo + hi) >>> 1;
        build(2 * node, lo, mid, a);
        build(2 * node + 1, mid + 1, hi, a);
        pull(node);
    }

    private void pull(int node) {
        sum[node] = sum[2 * node] + sum[2 * node + 1];
        max[node] = Math.max(max[2 * node], max[2 * node + 1]);
    }

    private void apply(int node, int lo, int hi, long d) {
        sum[node] += d * (hi - lo + 1);
        max[node] += d;
        lazy[node] += d;
    }

    private void push(int node, int lo, int hi) {
        if (lazy[node] != 0) {
            int mid = (lo + hi) >>> 1;
            apply(2 * node, lo, mid, lazy[node]);
            apply(2 * node + 1, mid + 1, hi, lazy[node]);
            lazy[node] = 0;
        }
    }

    private void check(int from, int to) {
        if (from < 0 || to >= n || from > to) {
            throw new IllegalArgumentException("bad span [" + from + ", " + to + "]");
        }
    }

    /** Adds {@code delta} heat to every forge in [from, to]. */
    public void add(int from, int to, long delta) {
        check(from, to);
        add(1, 0, n - 1, from, to, delta);
    }

    private void add(int node, int lo, int hi, int from, int to, long d) {
        if (to < lo || hi < from) {
            return;
        }
        if (from <= lo && hi <= to) {
            apply(node, lo, hi, d);
            return;
        }
        push(node, lo, hi);
        int mid = (lo + hi) >>> 1;
        add(2 * node, lo, mid, from, to, d);
        add(2 * node + 1, mid + 1, hi, from, to, d);
        pull(node);
    }

    /** Total heat in [from, to]. */
    public long sum(int from, int to) {
        check(from, to);
        return sum(1, 0, n - 1, from, to);
    }

    private long sum(int node, int lo, int hi, int from, int to) {
        if (to < lo || hi < from) {
            return 0;
        }
        if (from <= lo && hi <= to) {
            return sum[node];
        }
        push(node, lo, hi);
        int mid = (lo + hi) >>> 1;
        return sum(2 * node, lo, mid, from, to) + sum(2 * node + 1, mid + 1, hi, from, to);
    }

    /** Hottest forge's heat in [from, to]. */
    public long max(int from, int to) {
        check(from, to);
        return max(1, 0, n - 1, from, to);
    }

    private long max(int node, int lo, int hi, int from, int to) {
        if (to < lo || hi < from) {
            return Long.MIN_VALUE;
        }
        if (from <= lo && hi <= to) {
            return max[node];
        }
        push(node, lo, hi);
        int mid = (lo + hi) >>> 1;
        return Math.max(max(2 * node, lo, mid, from, to), max(2 * node + 1, mid + 1, hi, from, to));
    }

    /** BALANCED only if the clerk's total for [from, to] is right. */
    public Grade grade(int from, int to, long claimedTotal) {
        return sum(from, to) == claimedTotal ? Grade.BALANCED : Grade.SMUDGED;
    }

    /** The Forgemaster's line for a ledger page. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case BALANCED -> "Forgemaster: every blast entered, every total true. The guild trusts your ledger.";
            case SMUDGED -> "Forgemaster: the heat on the page is not the heat in the forge. Tally it again.";
        };
    }
}
