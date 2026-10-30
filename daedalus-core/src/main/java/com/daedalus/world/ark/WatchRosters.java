// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.Arrays;

/**
 * G302 The Watch Rosters: the bosun splits n crew into watches. Rosters with exactly k unlabeled
 * watches are Stirling numbers of the second kind S(n, k), rosters with any number of watches are
 * Bell numbers, and seatings of n crew round exactly k mess tables are unsigned Stirling numbers of
 * the first kind. A roster is written as a restricted growth string (crew i joins watch a[i], a[0]
 * = 0, each a[i] at most one more than every earlier entry) and ranked lexicographically.
 */
public final class WatchRosters {

    public static final String QUEST_ID = "q_watch_rosters";
    public static final int MAX_CREW = 300;

    private WatchRosters() { }

    private static void checkCrew(int n) {
        if (n < 0 || n > MAX_CREW) {
            throw new IllegalArgumentException("crew out of range: " + n);
        }
    }

    /** S(n, k): rosters of n crew into exactly k non-empty watches. */
    public static BigInteger stirling2(int n, int k) {
        checkCrew(n);
        if (k < 0 || k > n) {
            return BigInteger.ZERO;
        }
        BigInteger[] row = new BigInteger[n + 1];
        Arrays.fill(row, BigInteger.ZERO);
        row[0] = BigInteger.ONE;
        for (int i = 1; i <= n; i++) {
            for (int j = i; j >= 1; j--) {
                row[j] = row[j - 1].add(BigInteger.valueOf(j).multiply(row[j]));
            }
            row[0] = BigInteger.ZERO;
        }
        return row[k];
    }

    /** Bell(n): rosters of n crew into any number of watches. */
    public static BigInteger bell(int n) {
        checkCrew(n);
        BigInteger sum = n == 0 ? BigInteger.ONE : BigInteger.ZERO;
        for (int k = 1; k <= n; k++) {
            sum = sum.add(stirling2(n, k));
        }
        return sum;
    }

    /** Unsigned Stirling numbers of the first kind: seatings of n crew round exactly k tables. */
    public static BigInteger stirling1(int n, int k) {
        checkCrew(n);
        if (k < 0 || k > n) {
            return BigInteger.ZERO;
        }
        BigInteger[] row = new BigInteger[n + 1];
        Arrays.fill(row, BigInteger.ZERO);
        row[0] = BigInteger.ONE;
        for (int i = 1; i <= n; i++) {
            for (int j = i; j >= 1; j--) {
                row[j] = row[j - 1].add(BigInteger.valueOf(i - 1L).multiply(row[j]));
            }
            row[0] = BigInteger.ZERO;
        }
        return row[k];
    }

    /** f[r][m]: ways to finish r more crew when watches 0..m are already open. */
    private static BigInteger[][] tails(int n) {
        BigInteger[][] f = new BigInteger[n + 1][n + 2];
        for (BigInteger[] row : f) {
            Arrays.fill(row, BigInteger.ZERO);
        }
        Arrays.fill(f[0], BigInteger.ONE);
        for (int r = 1; r <= n; r++) {
            for (int m = 0; m <= n; m++) {
                f[r][m] = BigInteger.valueOf(m + 1L).multiply(f[r - 1][m]).add(f[r - 1][m + 1]);
            }
        }
        return f;
    }

    public static boolean isRoster(int[] a) {
        int max = -1;
        for (int v : a) {
            if (v < 0 || v > max + 1) {
                return false;
            }
            max = Math.max(max, v);
        }
        return true;
    }

    /** Lexicographic rank of a roster among all rosters of the same crew size. */
    public static BigInteger rank(int[] a) {
        if (!isRoster(a) || a.length > MAX_CREW) {
            throw new IllegalArgumentException("not a roster");
        }
        if (a.length == 0) {
            return BigInteger.ZERO;
        }
        BigInteger[][] f = tails(a.length);
        BigInteger rank = BigInteger.ZERO;
        int m = 0;
        for (int i = 1; i < a.length; i++) {
            int rem = a.length - i - 1;
            rank = rank.add(BigInteger.valueOf(a[i]).multiply(f[rem][m]));
            m = Math.max(m, a[i]);
        }
        return rank;
    }

    /** The roster of n crew with lexicographic rank k, 0 <= k < Bell(n). */
    public static int[] unrank(int n, BigInteger k) {
        checkCrew(n);
        if (k.signum() < 0 || k.compareTo(bell(n)) >= 0) {
            throw new IllegalArgumentException("rank out of range: " + k);
        }
        int[] a = new int[n];
        if (n == 0) {
            return a;
        }
        BigInteger[][] f = tails(n);
        BigInteger rem = k;
        int m = 0;
        for (int i = 1; i < n; i++) {
            BigInteger block = f[n - i - 1][m];
            int v = rem.divide(block).min(BigInteger.valueOf(m + 1L)).intValue();
            rem = rem.subtract(block.multiply(BigInteger.valueOf(v)));
            a[i] = v;
            m = Math.max(m, v);
        }
        return a;
    }

    /** Quest q_watch_rosters: a valid roster of the crew using exactly the asked number of watches. */
    public static boolean quest(int crew, int watches, int[] roster) {
        if (roster.length != crew || !isRoster(roster)) {
            return false;
        }
        int max = -1;
        for (int v : roster) {
            max = Math.max(max, v);
        }
        return max + 1 == watches;
    }
}