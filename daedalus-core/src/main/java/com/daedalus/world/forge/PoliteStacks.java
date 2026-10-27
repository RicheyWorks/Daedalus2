// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;

/**
 * Polite Stacks: a stack of n bars is polite when it splits into a run of two or more consecutive positive bar
 * counts (9 = 4 + 5 = 2 + 3 + 4). Its politeness, the number of such runs, equals the number of odd divisors of n
 * minus 1, so exactly the powers of two are impolite.
 *
 * <p>Reusable plain long API for 1 &lt;= n &lt;= {@link #MAX_N}: {@link #politeness}, {@link #runs}, {@link #isPolite},
 * {@link #countPolite} and {@link #nthPolite}.
 */
public final class PoliteStacks {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_polite_stacks";
    /** Largest supported stack. */
    public static final long MAX_N = 1_000_000_000_000L;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    /** A run of {@code length} consecutive counts starting at {@code start}. */
    public record Run(long start, long length) {
    }

    private PoliteStacks() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("stack out of range: " + n);
        }
    }

    /** Number of ways to write n as a sum of two or more consecutive positive integers. */
    public static long politeness(long n) {
        check(n);
        long m = n;
        while ((m & 1L) == 0) {
            m >>= 1;
        }
        long d = 1;
        for (long p = 3; p * p <= m; p += 2) {
            int e = 0;
            while (m % p == 0) {
                m /= p;
                e++;
            }
            d *= e + 1;
        }
        if (m > 1) {
            d *= 2;
        }
        return d - 1;
    }

    /** All runs summing to n, by increasing length (length &gt;= 2). */
    public static List<Run> runs(long n) {
        check(n);
        List<Run> out = new ArrayList<>();
        for (long k = 2; k * (k + 1) / 2 <= n; k++) {
            long rest = n - k * (k - 1) / 2;
            if (rest % k == 0) {
                out.add(new Run(rest / k, k));
            }
        }
        return out;
    }

    /** True unless n is a power of two. */
    public static boolean isPolite(long n) {
        check(n);
        return (n & (n - 1)) != 0;
    }

    /** Number of polite stacks in 1..N (N between 0 and {@link #MAX_N}). */
    public static long countPolite(long bigN) {
        if (bigN < 0 || bigN > MAX_N) {
            throw new IllegalArgumentException("rack out of range: " + bigN);
        }
        if (bigN == 0) {
            return 0;
        }
        return bigN - (63 - Long.numberOfLeadingZeros(bigN)) - 1;
    }

    /** The k-th polite stack, k &gt;= 1 (the first is 3). */
    public static long nthPolite(long k) {
        if (k < 1 || k > countPolite(MAX_N)) {
            throw new IllegalArgumentException("rank out of range: " + k);
        }
        long lo = 1;
        long hi = MAX_N;
        while (lo < hi) {
            long mid = lo + (hi - lo) / 2;
            if (countPolite(mid) >= k) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        return lo;
    }

    /** Grade a claimed politeness for stack n. */
    public static Grade grade(long n, long claimedPoliteness) {
        return politeness(n) == claimedPoliteness ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: every run of bars counted. The stack's manners are known.";
            case SLIPPED -> "Forgemaster: the count slipped. Each odd divisor but one gives a run.";
        };
    }
}
