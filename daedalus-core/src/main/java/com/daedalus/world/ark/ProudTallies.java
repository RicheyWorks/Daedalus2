// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G343 The Proud Tallies: a tally is proud when it equals the sum of its digits, each raised to
 * the number of digits (153 = 1^3 + 5^3 + 3^3, a narcissistic number). Rather than scanning every
 * tally, the clerk walks each multiset of digits once, sums the powers, and keeps the sum when its
 * own digits are that same multiset with the right length.
 */
public final class ProudTallies {

    public static final String QUEST_ID = "q_proud_tallies";

    private ProudTallies() { }

    private static int digitCount(long v) {
        int n = 1;
        long x = v;
        while (x >= 10) {
            x /= 10;
            n++;
        }
        return n;
    }

    /** True when v (positive) is proud. */
    public static boolean isProud(long v) {
        if (v < 1) {
            return false;
        }
        int len = digitCount(v);
        long sum = 0;
        long x = v;
        while (x > 0) {
            long p = 1;
            long dgt = x % 10;
            for (int i = 0; i < len; i++) {
                p *= dgt;
            }
            sum += p;
            x /= 10;
        }
        return sum == v;
    }

    /** All proud tallies with exactly len digits (1..12), ascending. */
    public static long[] withDigits(int len) {
        if (len < 1 || len > 12) {
            throw new IllegalArgumentException("len must be 1..12: " + len);
        }
        long[] pow = new long[10];
        for (int dgt = 0; dgt < 10; dgt++) {
            long p = 1;
            for (int i = 0; i < len; i++) {
                p *= dgt;
            }
            pow[dgt] = p;
        }
        long[] found = new long[16];
        int[] count = new int[10];
        int n = walk(len, 0, 0, 0L, pow, count, found, 0);
        long[] out = Arrays.copyOf(found, n);
        Arrays.sort(out);
        return out;
    }

    private static int walk(int len, int placed, int minDigit, long sum, long[] pow, int[] count,
            long[] found, int n) {
        if (placed == len) {
            if (sum > 0 && digitCount(sum) == len) {
                int[] got = new int[10];
                long x = sum;
                while (x > 0) {
                    got[(int) (x % 10)]++;
                    x /= 10;
                }
                if (Arrays.equals(got, count)) {
                    found[n] = sum;
                    return n + 1;
                }
            }
            return n;
        }
        int k = n;
        for (int dgt = minDigit; dgt < 10; dgt++) {
            count[dgt]++;
            k = walk(len, placed + 1, dgt, sum + pow[dgt], pow, count, found, k);
            count[dgt]--;
        }
        return k;
    }

    /** Quest q_proud_tallies: name a proud tally with the asked number of digits. */
    public static boolean quest(int len, long answer) {
        return digitCount(answer) == len && isProud(answer);
    }
}