// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/**
 * G308 The Tumbler Digits: the strongroom tumbler takes a width-digit setting, sorts its digits
 * high-to-low and low-to-high and subtracts (Kaprekar's routine, leading zeros kept). Repeating
 * it falls into a fixed point or loop: 6174 for four decimal digits, 495 for three. Also walks
 * happy numbers (sum of squared digits until 1 or a loop).
 */
public final class TumblerDigits {

    public static final String QUEST_ID = "q_tumbler_digits";

    private TumblerDigits() { }

    private static long limit(int width, int base) {
        if (base < 2 || base > 36 || width < 1) {
            throw new IllegalArgumentException("need 2 <= base <= 36 and width >= 1");
        }
        long lim = 1;
        for (int i = 0; i < width; i++) {
            if (lim > Long.MAX_VALUE / 4 / base) {
                throw new IllegalArgumentException("width too large for base");
            }
            lim *= base;
        }
        return lim;
    }

    /** One turn of the tumbler: descending digits minus ascending digits. */
    public static long step(long x, int width, int base) {
        long lim = limit(width, base);
        if (x < 0 || x >= lim) {
            throw new IllegalArgumentException("setting out of range: " + x);
        }
        int[] d = new int[width];
        long v = x;
        for (int i = 0; i < width; i++) {
            d[i] = (int) (v % base);
            v /= base;
        }
        Arrays.sort(d);
        long asc = 0;
        long desc = 0;
        for (int i = 0; i < width; i++) {
            asc = asc * base + d[i];
            desc = desc * base + d[width - 1 - i];
        }
        return desc - asc;
    }

    /** Turns until the tumbler first lands on a setting inside its final loop. */
    public static int stepsToLoop(long x, int width, int base) {
        Map<Long, Integer> seen = new HashMap<>();
        long v = x;
        int i = 0;
        while (!seen.containsKey(v)) {
            seen.put(v, i++);
            v = step(v, width, base);
        }
        return seen.get(v);
    }

    /** The final loop reached from x, starting at its smallest setting. */
    public static long[] loop(long x, int width, int base) {
        long v = x;
        for (int i = stepsToLoop(x, width, base); i > 0; i--) {
            v = step(v, width, base);
        }
        long start = v;
        long min = v;
        int len = 0;
        do {
            min = Math.min(min, v);
            v = step(v, width, base);
            len++;
        } while (v != start);
        long[] out = new long[len];
        v = min;
        for (int i = 0; i < len; i++) {
            out[i] = v;
            v = step(v, width, base);
        }
        return out;
    }

    /** Sum of squared decimal digits, repeated: happy when it reaches 1. */
    public static boolean isHappy(long n) {
        if (n < 1) {
            throw new IllegalArgumentException("need n >= 1");
        }
        long slow = n;
        long fast = n;
        do {
            slow = squareSum(slow);
            fast = squareSum(squareSum(fast));
        } while (slow != fast);
        return slow == 1;
    }

    static long squareSum(long n) {
        long s = 0;
        for (long v = n; v > 0; v /= 10) {
            long d = v % 10;
            s += d * d;
        }
        return s;
    }

    /** Quest q_tumbler_digits: turns a four-digit decimal setting needs to reach its loop. */
    public static boolean quest(long setting, int answer) {
        return stepsToLoop(setting, 4, 10) == answer;
    }
}