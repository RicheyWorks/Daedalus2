// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.HashSet;
import java.util.Set;

/**
 * Achilles Rivets: a rivet count n is an Achilles rivet when it is powerful (every prime factor appears at least
 * squared) yet not a perfect power m^k with k &gt;= 2 (72 = 2^3 x 3^2, 108, 200, ...).
 *
 * <p>Reusable plain long API for 1 &lt;= n &lt;= {@link #MAX_N}: {@link #isPowerful}, {@link #isPerfectPower} (gcd of
 * prime exponents), {@link #isAchilles}, and counts {@link #countPowerful}, {@link #countPerfectPowers},
 * {@link #countAchilles} (powerful numbers are unique a^2 b^3 with b squarefree).
 */
public final class AchillesRivets {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_achilles_rivets";
    /** Largest supported rivet count. */
    public static final long MAX_N = 1_000_000_000_000L;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private AchillesRivets() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("rivet count out of range: " + n);
        }
    }

    /** Floor square root of n &gt;= 0. */
    static long isqrt(long n) {
        long r = (long) Math.sqrt((double) n);
        while (r * r > n) {
            r--;
        }
        while ((r + 1) * (r + 1) <= n) {
            r++;
        }
        return r;
    }

    private static long gcd(long a, long b) {
        return b == 0 ? a : gcd(b, a % b);
    }

    /** Returns {min exponent, gcd of exponents} over the prime factorization of n (both 0 for n = 1). */
    private static long[] exponents(long n) {
        long m = n;
        long min = Long.MAX_VALUE;
        long g = 0;
        for (long p = 2; p * p <= m; p++) {
            int e = 0;
            while (m % p == 0) {
                m /= p;
                e++;
            }
            if (e > 0) {
                min = Math.min(min, e);
                g = gcd(g, e);
            }
        }
        if (m > 1) {
            min = 1;
            g = 1;
        }
        return new long[] {min == Long.MAX_VALUE ? 0 : min, g};
    }

    /** True when every prime factor of n appears at least squared (1 counts as powerful). */
    public static boolean isPowerful(long n) {
        check(n);
        return n == 1 || exponents(n)[0] >= 2;
    }

    /** True when n = m^k for some k &gt;= 2 (1 = 1^2 counts). */
    public static boolean isPerfectPower(long n) {
        check(n);
        return n == 1 || exponents(n)[1] >= 2;
    }

    /** True when n is powerful but not a perfect power. */
    public static boolean isAchilles(long n) {
        check(n);
        if (n == 1) {
            return false;
        }
        long[] e = exponents(n);
        return e[0] >= 2 && e[1] == 1;
    }

    private static void checkRack(long bigN) {
        if (bigN < 0 || bigN > MAX_N) {
            throw new IllegalArgumentException("rack out of range: " + bigN);
        }
    }

    private static boolean squarefree(long b) {
        for (long p = 2; p * p <= b; p++) {
            if (b % (p * p) == 0) {
                return false;
            }
        }
        return true;
    }

    /** Number of powerful n in 1..N. */
    public static long countPowerful(long bigN) {
        checkRack(bigN);
        long c = 0;
        for (long b = 1; b * b * b <= bigN; b++) {
            if (squarefree(b)) {
                c += isqrt(bigN / (b * b * b));
            }
        }
        return c;
    }

    /** Number of perfect powers in 1..N (1 included when N &gt;= 1). */
    public static long countPerfectPowers(long bigN) {
        checkRack(bigN);
        if (bigN < 1) {
            return 0;
        }
        Set<Long> odd = new HashSet<>();
        for (long m = 2; m * m * m <= bigN; m++) {
            long v = m * m * m;
            while (true) {
                long r = isqrt(v);
                if (r * r != v) {
                    odd.add(v);
                }
                if (v > bigN / m) {
                    break;
                }
                v *= m;
            }
        }
        return isqrt(bigN) + odd.size();
    }

    /** Number of Achilles n in 1..N. */
    public static long countAchilles(long bigN) {
        return countPowerful(bigN) - countPerfectPowers(bigN);
    }

    /** Grade a claim that rivet count n is (or is not) an Achilles rivet. */
    public static Grade grade(long n, boolean claimedAchilles) {
        return isAchilles(n) == claimedAchilles ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: every prime doubled, yet no single root. An Achilles rivet.";
            case SLIPPED -> "Forgemaster: the rivet slipped. A lone prime breaks it, and so does a perfect root.";
        };
    }
}
