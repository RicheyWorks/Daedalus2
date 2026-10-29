// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G528 The Shoeing Shed (Studio horse lane): one farrier shoes the waiting horses one after
 * another. Horse {@code h} needs {@code time[h]} minutes, frets with weight {@code fret[h]} and is
 * called to the show ring at minute {@code due[h]}. A horse finished after its call is late by the
 * difference, and the stable's penalty is the sum of fret times lateness. {@link #best} orders the
 * queue with an exact dynamic program over subsets of horses (the last horse of a subset finishes
 * at the subset's total time); {@link #smith} (shoe by fret per minute, Smith's rule, which ignores
 * the calls) is the habit that leaves an early-called horse waiting. Plain int[] API, at most 16
 * horses.
 */
public final class ShoeingShed {

    public static final String QUEST_ID = "q_sound_hooves";
    public static final int MAX_HORSES = 16;

    /** A shoeing order: total weighted lateness and the horses in shoeing order. */
    public record Queue(long penalty, int[] order) {
        public Queue {
            order = order.clone();
        }

        @Override
        public int[] order() {
            return order.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Queue q && q.penalty == penalty && Arrays.equals(q.order, order);
        }

        @Override
        public int hashCode() {
            return 31 * Long.hashCode(penalty) + Arrays.hashCode(order);
        }

        @Override
        public String toString() {
            return "Queue[" + penalty + ", " + Arrays.toString(order) + "]";
        }
    }

    private ShoeingShed() { }

    /** Seeded horses: index 0 = time in [1, 9], 1 = fret in [1, 5], 2 = due in [0, 4n]. */
    public static int[][] horses(long seed, int n) {
        if (n < 0 || n > MAX_HORSES) {
            throw new IllegalArgumentException("bad shed");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] time = new int[n];
        int[] fret = new int[n];
        int[] due = new int[n];
        for (int h = 0; h < n; h++) {
            time[h] = 1 + rnd.nextInt(9);
            fret[h] = 1 + rnd.nextInt(5);
            due[h] = rnd.nextInt(4 * n + 1);
        }
        return new int[][] {time, fret, due};
    }

    /** Smallest total weighted lateness over all shoeing orders. */
    public static Queue best(int[] time, int[] fret, int[] due) {
        check(time, fret, due);
        int n = time.length;
        int states = 1 << n;
        long[] cost = new long[states];
        int[] last = new int[states];
        long[] span = new long[states];
        for (int s = 1; s < states; s++) {
            int low = Integer.numberOfTrailingZeros(s);
            span[s] = span[s & (s - 1)] + time[low];
            cost[s] = Long.MAX_VALUE;
            for (int h = 0; h < n; h++) {
                if ((s & (1 << h)) == 0) {
                    continue;
                }
                long late = Math.max(0, span[s] - due[h]);
                long c = cost[s ^ (1 << h)] + fret[h] * late;
                if (c < cost[s]) {
                    cost[s] = c;
                    last[s] = h;
                }
            }
        }
        int[] order = new int[n];
        int s = states - 1;
        for (int k = n - 1; k >= 0; k--) {
            order[k] = last[s];
            s ^= 1 << last[s];
        }
        return new Queue(cost[states - 1], order);
    }

    /** Naive Smith's rule: highest fret per minute first (ties by index), deadlines ignored. */
    public static Queue smith(int[] time, int[] fret, int[] due) {
        check(time, fret, due);
        int n = time.length;
        Integer[] idx = new Integer[n];
        for (int i = 0; i < n; i++) {
            idx[i] = i;
        }
        Arrays.sort(idx, (a, b) -> {
            int c = Long.compare((long) fret[b] * time[a], (long) fret[a] * time[b]);
            return c != 0 ? c : Integer.compare(a, b);
        });
        int[] order = new int[n];
        for (int i = 0; i < n; i++) {
            order[i] = idx[i];
        }
        return new Queue(penalty(time, fret, due, order), order);
    }

    /** Total weighted lateness of an order, or -1 when it is not a permutation of the horses. */
    public static long penalty(int[] time, int[] fret, int[] due, int[] order) {
        check(time, fret, due);
        if (order.length != time.length) {
            return -1;
        }
        boolean[] seen = new boolean[time.length];
        long clock = 0;
        long total = 0;
        for (int h : order) {
            if (h < 0 || h >= time.length || seen[h]) {
                return -1;
            }
            seen[h] = true;
            clock += time[h];
            total += fret[h] * Math.max(0, clock - due[h]);
        }
        return total;
    }

    /** Quest q_sound_hooves: the farrier's order is a full queue with the least possible penalty. */
    public static boolean quest(int[] time, int[] fret, int[] due, int[] order) {
        long got = penalty(time, fret, due, order);
        return got >= 0 && got == best(time, fret, due).penalty();
    }

    private static void check(int[] time, int[] fret, int[] due) {
        if (time.length != fret.length || time.length != due.length || time.length > MAX_HORSES) {
            throw new IllegalArgumentException("bad shed");
        }
        for (int h = 0; h < time.length; h++) {
            if (time[h] <= 0 || fret[h] < 0 || due[h] < 0) {
                throw new IllegalArgumentException("bad horse " + h);
            }
        }
    }
}
