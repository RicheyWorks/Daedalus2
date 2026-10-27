// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.List;

/**
 * G285 The Hailstone Drift: a storm-tossed buoy at mark n drifts to n / 2 when n is even and to
 * 3n + 1 when it is odd, until it reaches mark 1 (the Collatz map). Gives the drift length (total
 * stopping time) and peak mark of one buoy, a memoised table of drift lengths below a limit, the
 * longest drift below the limit and the record setters. Overflow is checked, never wrapped.
 */
public final class HailstoneDrift {

    public static final String QUEST_ID = "q_hailstone_drift";
    public static final int MAX_TABLE = 5_000_000;

    private HailstoneDrift() { }

    private static long next(long n) {
        return (n & 1) == 0 ? n >> 1 : Math.addExact(Math.multiplyExact(3, n), 1);
    }

    /** Steps from n down to 1; throws ArithmeticException if the drift leaves the long range. */
    public static int steps(long n) {
        if (n < 1) {
            throw new IllegalArgumentException("mark must be positive: " + n);
        }
        int s = 0;
        for (long x = n; x != 1; x = next(x)) {
            s++;
        }
        return s;
    }

    /** Highest mark reached on the drift from n (n itself counts). */
    public static long peak(long n) {
        if (n < 1) {
            throw new IllegalArgumentException("mark must be positive: " + n);
        }
        long p = n;
        for (long x = n; x != 1; x = next(x)) {
            p = Math.max(p, x);
        }
        return p;
    }

    /** t[n] = steps(n) for 1 <= n < limit (t[0] unused), reusing shorter drifts. */
    public static int[] table(int limit) {
        if (limit < 2 || limit > MAX_TABLE) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        int[] t = new int[limit];
        for (int n = 2; n < limit; n++) {
            long x = n;
            int s = 0;
            while (x >= n) {
                x = next(x);
                s++;
            }
            t[n] = s + t[(int) x];
        }
        return t;
    }

    /** Start below limit with the longest drift (smallest start on ties). */
    public static int longest(int limit) {
        int[] t = table(limit);
        int best = 1;
        for (int n = 2; n < limit; n++) {
            if (t[n] > t[best]) {
                best = n;
            }
        }
        return best;
    }

    /** Starts below limit whose drift is longer than every smaller start's. */
    public static List<Integer> records(int limit) {
        int[] t = table(limit);
        List<Integer> out = new ArrayList<>();
        int max = -1;
        for (int n = 1; n < limit; n++) {
            if (t[n] > max) {
                max = t[n];
                out.add(n);
            }
        }
        return List.copyOf(out);
    }

    /** Quest q_hailstone_drift: the navigator names how many bells the buoy drifts. */
    public static boolean quest(long start, int answer) {
        return steps(start) == answer;
    }
}