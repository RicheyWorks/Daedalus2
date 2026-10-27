// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;

/**
 * Keith Kindling: a d-digit ember n (d &gt;= 2) is lit when the chain seeded with its digits, each next term the sum
 * of the previous d terms, reaches n exactly (a Keith number: 14 = 1, 4, 5, 9, 14).
 *
 * <p>Reusable plain long API: {@link #isKeith} and {@link #trail} for 1 &lt;= n &lt;= {@link #MAX_N} (ring buffer of
 * the last d terms), and {@link #keithUpTo} for limits up to {@link #MAX_LIST}.
 */
public final class KeithKindling {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_keith_kindling";
    /** Largest supported ember. */
    public static final long MAX_N = 1_000_000_000_000_000L;
    /** Largest supported listing limit. */
    public static final int MAX_LIST = 2_000_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private KeithKindling() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("ember out of range: " + n);
        }
    }

    private static long[] digits(long n) {
        String s = Long.toString(n);
        long[] d = new long[s.length()];
        for (int i = 0; i < d.length; i++) {
            d[i] = s.charAt(i) - '0';
        }
        return d;
    }

    /** The chain seeded with n's digits, up to and including the first term &gt;= n. */
    public static List<Long> trail(long n) {
        check(n);
        long[] ring = digits(n);
        int d = ring.length;
        List<Long> out = new ArrayList<>();
        long sum = 0;
        for (long x : ring) {
            out.add(x);
            sum += x;
        }
        if (d == 1) {
            return out;
        }
        int head = 0;
        long last = ring[d - 1];
        while (last < n) {
            last = sum;
            out.add(last);
            sum += last - ring[head];
            ring[head] = last;
            head = head + 1 == d ? 0 : head + 1;
        }
        return out;
    }

    /** True when n has at least two digits and its digit chain reaches n exactly. */
    public static boolean isKeith(long n) {
        check(n);
        if (n < 10) {
            return false;
        }
        List<Long> t = trail(n);
        return t.get(t.size() - 1) == n;
    }

    /** All Keith numbers in 1..limit, ascending (limit between 0 and {@link #MAX_LIST}). */
    public static List<Long> keithUpTo(int limit) {
        if (limit < 0 || limit > MAX_LIST) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        List<Long> out = new ArrayList<>();
        for (long n = 10; n <= limit; n++) {
            if (isKeith(n)) {
                out.add(n);
            }
        }
        return out;
    }

    /** Grade a claim that ember n is (or is not) lit. */
    public static Grade grade(long n, boolean claimedKeith) {
        return isKeith(n) == claimedKeith ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: you fed the chain its own digits and read the flame true.";
            case SLIPPED -> "Forgemaster: the kindling slipped. Sum the last d links, one link per digit.";
        };
    }
}
