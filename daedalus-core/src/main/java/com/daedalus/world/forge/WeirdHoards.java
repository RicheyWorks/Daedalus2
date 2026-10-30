// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Weird Hoards: a hoard of n coins is weird when its proper divisors sum past n (abundant) yet no subset of them
 * totals exactly n (not semiperfect): 70, 836, 4030, 5830, ...
 *
 * <p>Reusable plain long API for 1 &lt;= n &lt;= {@link #MAX_N}: {@link #properDivisors}, {@link #isAbundant},
 * {@link #isSemiperfect} (word-packed subset-sum bitset), {@link #isWeird}, and {@link #weirdUpTo} for limits up to
 * {@link #MAX_LIST}.
 */
public final class WeirdHoards {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_weird_hoards";
    /** Largest supported hoard. */
    public static final int MAX_N = 10_000_000;
    /** Largest supported listing limit. */
    public static final int MAX_LIST = 30_000;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private WeirdHoards() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("hoard out of range: " + n);
        }
    }

    /** Proper divisors of n (all divisors below n), ascending. */
    public static List<Long> properDivisors(long n) {
        check(n);
        List<Long> low = new ArrayList<>();
        List<Long> high = new ArrayList<>();
        for (long d = 1; d * d <= n; d++) {
            if (n % d == 0) {
                low.add(d);
                long q = n / d;
                if (q != d && q != n) {
                    high.add(q);
                }
            }
        }
        if (n == 1) {
            low.clear();
        }
        Collections.reverse(high);
        low.addAll(high);
        return low;
    }

    private static long sum(List<Long> xs) {
        long s = 0;
        for (long x : xs) {
            s += x;
        }
        return s;
    }

    /** True when the proper divisors of n sum to more than n. */
    public static boolean isAbundant(long n) {
        return sum(properDivisors(n)) > n;
    }

    /** True when some subset of the proper divisors of n sums to exactly n. */
    public static boolean isSemiperfect(long n) {
        List<Long> ds = properDivisors(n);
        if (sum(ds) < n) {
            return false;
        }
        int target = (int) n;
        long[] w = new long[target / 64 + 1];
        w[0] = 1L;
        for (int k = ds.size() - 1; k >= 0; k--) {
            int d = (int) (long) ds.get(k);
            int ws = d / 64;
            int bs = d % 64;
            for (int i = w.length - 1; i >= ws; i--) {
                long v = w[i - ws] << bs;
                if (bs != 0 && i - ws - 1 >= 0) {
                    v |= w[i - ws - 1] >>> (64 - bs);
                }
                w[i] |= v;
            }
            if ((w[target / 64] & (1L << (target % 64))) != 0) {
                return true;
            }
        }
        return false;
    }

    /** True when n is abundant but not semiperfect. */
    public static boolean isWeird(long n) {
        return isAbundant(n) && !isSemiperfect(n);
    }

    /** All weird hoards in 1..limit, ascending (limit between 0 and {@link #MAX_LIST}). */
    public static List<Long> weirdUpTo(int limit) {
        if (limit < 0 || limit > MAX_LIST) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        List<Long> out = new ArrayList<>();
        for (long n = 1; n <= limit; n++) {
            if (isWeird(n)) {
                out.add(n);
            }
        }
        return out;
    }

    /** Grade a claim that hoard n is (or is not) weird. */
    public static Grade grade(long n, boolean claimedWeird) {
        return isWeird(n) == claimedWeird ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: more than enough coin, yet no handful pays it exactly. A weird hoard.";
            case SLIPPED -> "Forgemaster: the hoard slipped. First weigh the divisors, then seek an exact handful.";
        };
    }
}
