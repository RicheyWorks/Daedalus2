// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.Arrays;

/**
 * G280 The Rigging Ladder: a topman climbs n rungs up the rigging and n back down, one rung per
 * bell, never dropping below the deck. A climb plan is a string of 'U' and 'D'; the plans are
 * Dyck paths and there are Catalan(n) of them. Counts plans exactly and modulo m, ranks and
 * unranks plans in lexicographic order ('D' before 'U'), and checks a submitted plan.
 */
public final class RiggingLadder {

    public static final String QUEST_ID = "q_rigging_ladder";
    /** Largest n for rank/unrank tables. */
    public static final int MAX_RANK_RUNGS = 200;
    /** Largest n for counting modulo m. */
    public static final int MAX_MOD_RUNGS = 3000;

    private RiggingLadder() { }

    /** Catalan(n) = C(2n, n) / (n + 1). */
    public static BigInteger count(int n) {
        if (n < 0 || n > 100_000) {
            throw new IllegalArgumentException("rungs out of range: " + n);
        }
        BigInteger c = BigInteger.ONE;
        for (int k = 0; k < n; k++) {
            c = c.multiply(BigInteger.valueOf(2L * (2 * k + 1))).divide(BigInteger.valueOf(k + 2L));
        }
        return c;
    }

    /** Catalan(n) mod m by the height DP, so m need not be prime. */
    public static long countMod(int n, long m) {
        if (n < 0 || n > MAX_MOD_RUNGS) {
            throw new IllegalArgumentException("rungs out of range: " + n);
        }
        if (m < 1 || m > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("modulus out of range: " + m);
        }
        long[] cur = new long[n + 2];
        cur[0] = 1 % m;
        for (int step = 0; step < 2 * n; step++) {
            long[] nxt = new long[n + 2];
            for (int h = 0; h <= n; h++) {
                if (cur[h] != 0) {
                    nxt[h + 1] = (nxt[h + 1] + cur[h]) % m;
                    if (h > 0) {
                        nxt[h - 1] = (nxt[h - 1] + cur[h]) % m;
                    }
                }
            }
            nxt[n + 1] = 0;
            cur = nxt;
        }
        return cur[0];
    }

    /** t[r][h]: ways to finish from height h in r bells, landing on deck, never below it. */
    private static BigInteger[][] table(int n) {
        BigInteger[][] t = new BigInteger[2 * n + 1][n + 2];
        for (BigInteger[] row : t) {
            Arrays.fill(row, BigInteger.ZERO);
        }
        t[0][0] = BigInteger.ONE;
        for (int r = 1; r <= 2 * n; r++) {
            for (int h = 0; h <= n; h++) {
                BigInteger v = t[r - 1][h + 1];
                if (h > 0) {
                    v = v.add(t[r - 1][h - 1]);
                }
                t[r][h] = v;
            }
        }
        return t;
    }

    public static boolean isPlan(String plan) {
        if (plan.length() % 2 != 0) {
            return false;
        }
        int h = 0;
        for (int i = 0; i < plan.length(); i++) {
            char ch = plan.charAt(i);
            if (ch == 'U') {
                h++;
            } else if (ch == 'D') {
                h--;
            } else {
                return false;
            }
            if (h < 0) {
                return false;
            }
        }
        return h == 0;
    }

    /** Lexicographic rank of a valid plan among all plans with the same number of rungs. */
    public static BigInteger rank(String plan) {
        if (!isPlan(plan) || plan.length() / 2 > MAX_RANK_RUNGS) {
            throw new IllegalArgumentException("not a climb plan");
        }
        int n = plan.length() / 2;
        BigInteger[][] t = table(n);
        BigInteger rank = BigInteger.ZERO;
        int h = 0;
        for (int i = 0; i < plan.length(); i++) {
            int r = plan.length() - i - 1;
            if (plan.charAt(i) == 'U') {
                if (h > 0) {
                    rank = rank.add(t[r][h - 1]);
                }
                h++;
            } else {
                h--;
            }
        }
        return rank;
    }

    /** The plan with the given lexicographic rank, 0 <= k < Catalan(n). */
    public static String unrank(int n, BigInteger k) {
        if (n < 0 || n > MAX_RANK_RUNGS) {
            throw new IllegalArgumentException("rungs out of range: " + n);
        }
        if (k.signum() < 0 || k.compareTo(count(n)) >= 0) {
            throw new IllegalArgumentException("rank out of range: " + k);
        }
        BigInteger[][] t = table(n);
        StringBuilder sb = new StringBuilder(2 * n);
        BigInteger rem = k;
        int h = 0;
        for (int i = 0; i < 2 * n; i++) {
            int r = 2 * n - i - 1;
            BigInteger down = h > 0 ? t[r][h - 1] : BigInteger.ZERO;
            if (rem.compareTo(down) < 0) {
                sb.append('D');
                h--;
            } else {
                rem = rem.subtract(down);
                sb.append('U');
                h++;
            }
        }
        return sb.toString();
    }

    /** Quest q_rigging_ladder: a valid climb of exactly the given rungs. */
    public static boolean quest(int rungs, String plan) {
        return plan.length() == 2 * rungs && isPlan(plan);
    }
}