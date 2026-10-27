// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.List;

/**
 * G298 The Scale Pans: the quartermaster owns one weight each of 1, 3, 9, 27, ... and may set a
 * weight on either pan of the scale. Every whole load balances in exactly one way, read off from
 * the load in balanced ternary (digits -1, 0, +1): +1 puts the weight on the far pan, -1 beside the
 * cargo. Converts both ways, lists the placement, and counts the weights used.
 */
public final class ScalePans {

    public static final String QUEST_ID = "q_scale_pans";
    public static final long MAX_LOAD = Long.MAX_VALUE / 4;

    private ScalePans() { }

    private static void check(long load) {
        if (load > MAX_LOAD || load < -MAX_LOAD) {
            throw new IllegalArgumentException("load out of range: " + load);
        }
    }

    /** Balanced ternary digits of load, least significant first; empty for 0. */
    public static int[] digits(long load) {
        check(load);
        List<Integer> out = new ArrayList<>();
        long n = load;
        while (n != 0) {
            int r = (int) Math.floorMod(n, 3L);
            int d = r == 2 ? -1 : r;
            out.add(d);
            n = (n - d) / 3;
        }
        int[] a = new int[out.size()];
        for (int i = 0; i < a.length; i++) {
            a[i] = out.get(i);
        }
        return a;
    }

    /** The load a digit plan balances; digits must each be -1, 0 or +1. */
    public static long fromDigits(int[] plan) {
        long v = 0;
        for (int i = plan.length - 1; i >= 0; i--) {
            if (plan[i] < -1 || plan[i] > 1) {
                throw new IllegalArgumentException("digit out of range at " + i);
            }
            v = Math.addExact(Math.multiplyExact(v, 3L), plan[i]);
        }
        return v;
    }

    /** Weights set on the far pan (digit +1) when sameSide is false, beside the cargo when true. */
    public static List<Long> weights(long load, boolean sameSide) {
        int[] d = digits(load);
        List<Long> out = new ArrayList<>();
        long w = 1;
        for (int i = 0; i < d.length; i++) {
            if (d[i] == (sameSide ? -1 : 1)) {
                out.add(w);
            }
            if (i + 1 < d.length) {
                w = Math.multiplyExact(w, 3L);
            }
        }
        return out;
    }

    public static int weightsUsed(long load) {
        int c = 0;
        for (int d : digits(load)) {
            if (d != 0) {
                c++;
            }
        }
        return c;
    }

    /** Quest q_scale_pans: does the quartermaster's digit plan balance the cargo? */
    public static boolean quest(long load, int[] plan) {
        for (int d : plan) {
            if (d < -1 || d > 1) {
                return false;
            }
        }
        return fromDigits(plan) == load;
    }
}