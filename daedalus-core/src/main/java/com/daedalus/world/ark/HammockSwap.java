// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.SplittableRandom;

/**
 * G277 The Hammock Swap: after a storm the bosun reassigns the crew's hammocks so no sailor sleeps
 * in their own. Counts the swaps (derangements, the subfactorial !n) exactly and modulo m, counts
 * plans that leave exactly k sailors home, draws a uniform seeded swap, and checks a submitted plan.
 */
public final class HammockSwap {

    public static final String QUEST_ID = "q_hammock_swap";
    public static final int MAX_CREW = 5000;

    private HammockSwap() { }

    private static void checkCrew(int n) {
        if (n < 0 || n > MAX_CREW) {
            throw new IllegalArgumentException("crew out of range: " + n);
        }
    }

    /** !n via D(n) = (n - 1)(D(n - 1) + D(n - 2)), D(0) = 1, D(1) = 0. */
    public static BigInteger count(int n) {
        checkCrew(n);
        BigInteger a = BigInteger.ONE;
        BigInteger b = BigInteger.ZERO;
        if (n == 0) {
            return a;
        }
        for (int i = 2; i <= n; i++) {
            BigInteger c = a.add(b).multiply(BigInteger.valueOf(i - 1L));
            a = b;
            b = c;
        }
        return b;
    }

    /** !n mod m for 1 <= m < 2^31. */
    public static long countMod(int n, long m) {
        checkCrew(n);
        if (m < 1 || m > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("modulus out of range: " + m);
        }
        long a = 1 % m;
        long b = 0;
        if (n == 0) {
            return a;
        }
        for (int i = 2; i <= n; i++) {
            long c = (a + b) % m * ((i - 1L) % m) % m;
            a = b;
            b = c;
        }
        return b;
    }

    /** Plans of n hammocks leaving exactly k sailors in their own: C(n, k) * !(n - k). */
    public static BigInteger exactlyHome(int n, int k) {
        checkCrew(n);
        if (k < 0 || k > n) {
            return BigInteger.ZERO;
        }
        BigInteger binom = BigInteger.ONE;
        for (int i = 0; i < k; i++) {
            binom = binom.multiply(BigInteger.valueOf((long) n - i)).divide(BigInteger.valueOf(i + 1L));
        }
        return binom.multiply(count(n - k));
    }

    /** A uniformly random swap for n >= 2 crew: shuffle and reject until nobody is home. */
    public static int[] draw(int n, SplittableRandom rnd) {
        checkCrew(n);
        if (n == 1) {
            throw new IllegalArgumentException("one sailor cannot swap");
        }
        int[] p = new int[n];
        do {
            for (int i = 0; i < n; i++) {
                p[i] = i;
            }
            for (int i = n - 1; i > 0; i--) {
                int j = rnd.nextInt(i + 1);
                int t = p[i];
                p[i] = p[j];
                p[j] = t;
            }
        } while (!isSwap(p));
        return p;
    }

    /** True when plan is a permutation of 0..n-1 with no fixed point. */
    public static boolean isSwap(int[] plan) {
        boolean[] seen = new boolean[plan.length];
        for (int i = 0; i < plan.length; i++) {
            int v = plan[i];
            if (v < 0 || v >= plan.length || seen[v] || v == i) {
                return false;
            }
            seen[v] = true;
        }
        return true;
    }

    /** Quest q_hammock_swap: the bosun's plan must move every one of the crew. */
    public static boolean quest(int crew, int[] plan) {
        return plan.length == crew && isSwap(plan);
    }
}