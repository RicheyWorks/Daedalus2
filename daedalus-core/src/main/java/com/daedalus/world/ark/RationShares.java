// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * G299 The Ration Shares: the cook must hand out a ration fraction a/b of a cask as distinct unit
 * shares 1/d (an Egyptian fraction). The greedy split (Fibonacci-Sylvester) always ends, in
 * BigInteger; the shortest split with every denominator up to a cap is found by iterative
 * deepening, smallest denominators first (overflow throws ArithmeticException, never wraps).
 */
public final class RationShares {

    public static final String QUEST_ID = "q_ration_shares";

    private RationShares() { }

    private static void check(long a, long b) {
        if (a < 1 || b < 1 || a >= b) {
            throw new IllegalArgumentException("need 0 < a < b");
        }
    }

    /** Greedy denominators, ascending, whose unit fractions sum to a/b. */
    public static List<BigInteger> greedy(long a, long b) {
        check(a, b);
        List<BigInteger> out = new ArrayList<>();
        BigInteger num = BigInteger.valueOf(a);
        BigInteger den = BigInteger.valueOf(b);
        while (num.signum() > 0) {
            BigInteger d = den.add(num).subtract(BigInteger.ONE).divide(num);
            out.add(d);
            num = num.multiply(d).subtract(den);
            den = den.multiply(d);
            BigInteger g = num.gcd(den);
            if (g.signum() > 0) {
                num = num.divide(g);
                den = den.divide(g);
            }
        }
        return out;
    }

    /** Fewest distinct unit shares (each denominator at most maxDen, at most maxTerms); empty if none. */
    public static List<Long> shortest(long a, long b, int maxTerms, long maxDen) {
        check(a, b);
        if (maxTerms < 1 || maxTerms > 6 || maxDen < 2 || maxDen > 100_000) {
            throw new IllegalArgumentException("search bounds out of range");
        }
        long[] pick = new long[maxTerms];
        for (int terms = 1; terms <= maxTerms; terms++) {
            if (search(a, b, terms, 0, 2, maxDen, pick)) {
                List<Long> out = new ArrayList<>();
                for (int i = 0; i < terms; i++) {
                    out.add(pick[i]);
                }
                return out;
            }
        }
        return List.of();
    }

    private static boolean search(long a, long b, int left, int at, long minDen, long maxDen, long[] pick) {
        if (left == 1) {
            if (b % a == 0 && b / a >= minDen && b / a <= maxDen) {
                pick[at] = b / a;
                return true;
            }
            return false;
        }
        long lo = Math.max(minDen, (b + a - 1) / a);
        long hi = Math.min(maxDen, Math.multiplyExact((long) left, b) / a);
        for (long d = lo; d <= hi; d++) {
            long na = Math.multiplyExact(a, d) - b;
            long nb = Math.multiplyExact(b, d);
            if (na <= 0) {
                continue;
            }
            long g = gcd(na, nb);
            pick[at] = d;
            if (search(na / g, nb / g, left - 1, at + 1, d + 1, maxDen, pick)) {
                return true;
            }
        }
        return false;
    }

    static long gcd(long x, long y) {
        long p = x;
        long q = y;
        while (q != 0) {
            long t = p % q;
            p = q;
            q = t;
        }
        return p;
    }

    /** Quest q_ration_shares: distinct positive denominators whose unit shares sum to a/b. */
    public static boolean quest(long a, long b, List<Long> dens) {
        check(a, b);
        Set<Long> seen = new HashSet<>();
        BigInteger num = BigInteger.ZERO;
        BigInteger den = BigInteger.ONE;
        for (long d : dens) {
            if (d < 1 || !seen.add(d)) {
                return false;
            }
            BigInteger bd = BigInteger.valueOf(d);
            num = num.multiply(bd).add(den);
            den = den.multiply(bd);
        }
        return num.multiply(BigInteger.valueOf(b)).equals(den.multiply(BigInteger.valueOf(a)));
    }
}