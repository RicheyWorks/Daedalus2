// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;

/**
 * G260 The Ballast Splits: in how many ways can {@code n} identical ballast stones be split into
 * unordered piles? {@link #count} computes the partition number p(n) exactly with Euler's
 * pentagonal-number recurrence in O(n^1.5) big-integer additions; {@link #countAtMost} caps the
 * number of piles with a DP; {@link #list} spells the splits out for small n.
 */
public final class BallastSplits {

    public static final String QUEST_ID = "q_ballast_splits";
    public static final int MAX_N = 20_000;
    public static final int MAX_LIST = 40;

    private BallastSplits() { }

    /** p(n): splits of n stones into any number of piles. */
    public static BigInteger count(int n) {
        check(n, MAX_N);
        BigInteger[] p = new BigInteger[n + 1];
        p[0] = BigInteger.ONE;
        for (int m = 1; m <= n; m++) {
            BigInteger sum = BigInteger.ZERO;
            for (int k = 1; ; k++) {
                int g1 = k * (3 * k - 1) / 2;
                if (g1 > m) {
                    break;
                }
                int g2 = k * (3 * k + 1) / 2;
                BigInteger term = p[m - g1];
                if (g2 <= m) {
                    term = term.add(p[m - g2]);
                }
                sum = (k & 1) != 0 ? sum.add(term) : sum.subtract(term);
            }
            p[m] = sum;
        }
        return p[n];
    }

    /** Splits of n stones into at most k piles (equivalently, piles of size at most k). */
    public static BigInteger countAtMost(int n, int k) {
        check(n, MAX_N);
        if (k < 0) {
            throw new IllegalArgumentException("k < 0");
        }
        BigInteger[] ways = new BigInteger[n + 1];
        java.util.Arrays.fill(ways, BigInteger.ZERO);
        ways[0] = BigInteger.ONE;
        for (int size = 1; size <= Math.min(k, n); size++) {
            for (int s = size; s <= n; s++) {
                ways[s] = ways[s].add(ways[s - size]);
            }
        }
        return ways[n];
    }

    /** Every split of n, piles largest first, splits in reverse lexicographic order. */
    public static List<List<Integer>> list(int n) {
        check(n, MAX_LIST);
        List<List<Integer>> out = new ArrayList<>();
        build(n, n, new ArrayList<>(), out);
        return out;
    }

    private static void build(int left, int cap, List<Integer> cur, List<List<Integer>> out) {
        if (left == 0) {
            out.add(List.copyOf(cur));
            return;
        }
        for (int pile = Math.min(left, cap); pile >= 1; pile--) {
            cur.add(pile);
            build(left - pile, pile, cur, out);
            cur.remove(cur.size() - 1);
        }
    }

    private static void check(int n, int max) {
        if (n < 0 || n > max) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
    }

    /** Quest q_ballast_splits: the bosun must name p(n) exactly. */
    public static boolean quest(int n, String answer) {
        return count(n).toString().equals(answer);
    }
}
