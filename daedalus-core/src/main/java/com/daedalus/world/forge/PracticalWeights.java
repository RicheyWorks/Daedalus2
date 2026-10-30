// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;

/**
 * Practical Weights: the smith's weight set for a stamp n is the set of divisors of n. The set is practical when every
 * load 1..n-1 can be balanced by a sum of distinct divisors (a practical number, e.g. 12: 1,2,3,4,6 cover 1..11).
 *
 * <p>Reusable plain long API: {@link #isPractical} via the Stewart-Sierpinski prime criterion for 1 &lt;= n &lt;=
 * {@link #MAX_N}, {@link #smallestUnweighable} via a greedy reach over sorted divisors, and {@link #countPractical}
 * for racks N &lt;= {@link #MAX_RACK}.
 */
public final class PracticalWeights {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_practical_weights";
    /** Largest supported single stamp. */
    public static final long MAX_N = 1_000_000_000_000L;
    /** Largest supported rack for counting. */
    public static final int MAX_RACK = 1_000_000;

    /** Grade band. */
    public enum Grade { WEIGHED, SHORT }

    private PracticalWeights() {
    }

    private static void check(long n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("stamp out of range: " + n);
        }
    }

    /** True when every load 1..n-1 is a sum of distinct divisors of n. */
    public static boolean isPractical(long n) {
        check(n);
        if (n == 1) {
            return true;
        }
        if ((n & 1L) != 0) {
            return false;
        }
        long m = n;
        long sigmaPrefix = 1;
        for (long p = 2; p * p <= m; p++) {
            if (m % p != 0) {
                continue;
            }
            if (p > sigmaPrefix + 1) {
                return false;
            }
            long pk = 1;
            long sum = 1;
            while (m % p == 0) {
                m /= p;
                pk *= p;
                sum += pk;
            }
            sigmaPrefix *= sum;
        }
        return m == 1 || m <= sigmaPrefix + 1;
    }

    /** Divisors of n in ascending order. */
    public static List<Long> divisors(long n) {
        check(n);
        List<Long> low = new ArrayList<>();
        List<Long> high = new ArrayList<>();
        for (long d = 1; d * d <= n; d++) {
            if (n % d == 0) {
                low.add(d);
                if (d != n / d) {
                    high.add(n / d);
                }
            }
        }
        for (int i = high.size() - 1; i >= 0; i--) {
            low.add(high.get(i));
        }
        return low;
    }

    /** Smallest positive load that no sum of distinct divisors of n balances (sigma(n) + 1 if none is missing). */
    public static long smallestUnweighable(long n) {
        long reach = 0;
        for (long d : divisors(n)) {
            if (d > reach + 1) {
                break;
            }
            reach += d;
        }
        return reach + 1;
    }

    /** Number of practical n in 1..N. */
    public static long countPractical(int bigN) {
        if (bigN < 0 || bigN > MAX_RACK) {
            throw new IllegalArgumentException("rack out of range: " + bigN);
        }
        long c = bigN >= 1 ? 1 : 0;
        for (int n = 2; n <= bigN; n += 2) {
            if (isPractical(n)) {
                c++;
            }
        }
        return c;
    }

    /** Grade a claim that stamp n's divisors are (or are not) a practical weight set. */
    public static Grade grade(long n, boolean claimedPractical) {
        return isPractical(n) == claimedPractical ? Grade.WEIGHED : Grade.SHORT;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case WEIGHED -> "Forgemaster: the weights answer every load. A true smith's set.";
            case SHORT -> "Forgemaster: a load slipped through. Each new prime must not outgrow the weights before it.";
        };
    }
}
