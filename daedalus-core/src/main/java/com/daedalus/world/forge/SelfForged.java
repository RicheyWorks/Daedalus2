// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Self Forged: blank m stamps the mark m + digitSum(m); mark n is self-forged when no blank stamps it (a self or
 * Colombian number: 1, 3, 5, 7, 9, 20, 31, ...).
 *
 * <p>Reusable plain long API: {@link #stamp}, {@link #generator} and {@link #isSelf} for 1 &lt;= n &lt;=
 * {@link #MAX_N} (only the at most 9 x 16 blanks just below n can stamp it), and {@link #countSelf} /
 * {@link #selfUpTo} by sieve for limits up to {@link #MAX_SIEVE}.
 */
public final class SelfForged {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_self_forged";
    /** Largest supported mark. */
    public static final long MAX_N = 1_000_000_000_000_000L;
    /** Largest supported sieve limit. */
    public static final int MAX_SIEVE = 10_000_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private SelfForged() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("mark out of range: " + n);
        }
    }

    /** Base-10 digit sum of m &gt;= 0. */
    public static int digitSum(long m) {
        if (m < 0) {
            throw new IllegalArgumentException("negative blank: " + m);
        }
        int s = 0;
        for (long x = m; x > 0; x /= 10) {
            s += (int) (x % 10);
        }
        return s;
    }

    /** The mark blank m stamps: m + digitSum(m). */
    public static long stamp(long m) {
        return m + digitSum(m);
    }

    /** Smallest blank m &gt;= 1 with stamp(m) = n, or -1 when n is self-forged. */
    public static long generator(long n) {
        check(n);
        for (long m = Math.max(1, n - 9L * 17); m < n; m++) {
            if (stamp(m) == n) {
                return m;
            }
        }
        return -1;
    }

    /** True when no blank stamps n. */
    public static boolean isSelf(long n) {
        return generator(n) < 0;
    }

    private static boolean[] stamped(int limit) {
        if (limit < 0 || limit > MAX_SIEVE) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        boolean[] hit = new boolean[limit + 1];
        int ds = 0;
        for (int m = 1; m <= limit; m++) {
            ds = m % 10 == 0 ? digitSum(m) : ds + 1;
            long v = (long) m + ds;
            if (v <= limit) {
                hit[(int) v] = true;
            }
        }
        return hit;
    }

    /** Number of self-forged marks in 1..limit. */
    public static long countSelf(int limit) {
        return countSelfIn(stamped(limit));
    }

    /** Self-forged marks in 1..limit, ascending. */
    public static long[] selfUpTo(int limit) {
        boolean[] hit = stamped(limit);
        long[] out = new long[(int) countSelfIn(hit)];
        int k = 0;
        for (int n = 1; n < hit.length; n++) {
            if (!hit[n]) {
                out[k++] = n;
            }
        }
        return out;
    }

    private static long countSelfIn(boolean[] hit) {
        long c = 0;
        for (int n = 1; n < hit.length; n++) {
            if (!hit[n]) {
                c++;
            }
        }
        return c;
    }

    /** Grade a claim that mark n is (or is not) self-forged. */
    public static Grade grade(long n, boolean claimedSelf) {
        return isSelf(n) == claimedSelf ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: you read the mark true. Some marks no blank can stamp.";
            case SLIPPED -> "Forgemaster: the mark slipped. Try each blank just below it, plus its digits.";
        };
    }
}
