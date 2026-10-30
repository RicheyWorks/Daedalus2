// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * G291 The Twin Ledgers: the purser files each ledger number n under the sum of its proper
 * divisors s(n). A ledger equal to its own sum is perfect, above it is deficient, below it is
 * abundant; two different ledgers that each sum to the other are amicable twins. Following
 * n, s(n), s(s(n)), ... gives the aliquot chain, which may end at 0, fall into a loop, or run on.
 */
public final class TwinLedgers {

    public static final String QUEST_ID = "q_twin_ledgers";
    public static final int MAX_SIEVE = 10_000_000;
    public static final long MAX_TRIAL = 1_000_000_000_000L;

    public enum Grade { DEFICIENT, PERFECT, ABUNDANT }

    /** An aliquot chain: the terms walked, and where a loop started (-1 when none was found). */
    public static final class Chain {
        private final long[] walked;
        private final int loopStart;

        Chain(List<Long> terms, int loopStart) {
            this.walked = new long[terms.size()];
            for (int i = 0; i < walked.length; i++) {
                walked[i] = terms.get(i);
            }
            this.loopStart = loopStart;
        }

        /** A fresh copy of the walked terms. */
        public List<Long> terms() {
            List<Long> out = new ArrayList<>(walked.length);
            for (long v : walked) {
                out.add(v);
            }
            return out;
        }

        public int loopStart() {
            return loopStart;
        }
    }

    private TwinLedgers() { }

    /** s[n] = sum of proper divisors of n for 0 <= n < limit (s[0] = s[1] = 0). */
    public static long[] sieve(int limit) {
        if (limit < 2 || limit > MAX_SIEVE) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        long[] s = new long[limit];
        for (int d = 1; d <= (limit - 1) / 2; d++) {
            for (int k = 2 * d; k < limit; k += d) {
                s[k] += d;
            }
        }
        return s;
    }

    /** Sum of proper divisors of n by trial division, 1 <= n <= MAX_TRIAL. */
    public static long properSum(long n) {
        if (n < 1 || n > MAX_TRIAL) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        if (n == 1) {
            return 0;
        }
        long sum = 1;
        for (long d = 2; d * d <= n; d++) {
            if (n % d == 0) {
                sum += d;
                long e = n / d;
                if (e != d) {
                    sum += e;
                }
            }
        }
        return sum;
    }

    public static Grade grade(long n) {
        long s = properSum(n);
        return s == n ? Grade.PERFECT : s > n ? Grade.ABUNDANT : Grade.DEFICIENT;
    }

    /** Amicable twins (a, b) with a < b < limit, ascending by a. */
    public static List<long[]> twins(int limit) {
        long[] s = sieve(limit);
        List<long[]> out = new ArrayList<>();
        for (int a = 2; a < limit; a++) {
            long b = s[a];
            if (b > a && b < limit && s[(int) b] == a) {
                out.add(new long[] {a, b});
            }
        }
        return out;
    }

    /** Walks at most maxSteps terms; stops at 0, or when a term repeats (loopStart = its first index). */
    public static Chain chain(long start, int maxSteps) {
        if (maxSteps < 1) {
            throw new IllegalArgumentException("maxSteps must be positive");
        }
        List<Long> terms = new ArrayList<>();
        Map<Long, Integer> seen = new HashMap<>();
        long x = start;
        for (int i = 0; i < maxSteps; i++) {
            Integer at = seen.get(x);
            if (at != null) {
                return new Chain(terms, at);
            }
            seen.put(x, i);
            terms.add(x);
            if (x == 0) {
                break;
            }
            if (x > MAX_TRIAL) {
                break;
            }
            x = properSum(x);
        }
        return new Chain(terms, -1);
    }

    /** Quest q_twin_ledgers: the purser names the amicable twin of a ledger (or 0 if it has none). */
    public static boolean quest(long ledger, long answer) {
        long b = properSum(ledger);
        long twin = b != ledger && b >= 1 && properSum(b) == ledger ? b : 0;
        return twin == answer;
    }
}