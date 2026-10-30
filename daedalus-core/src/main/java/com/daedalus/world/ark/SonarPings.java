// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G358 The Sonar Pings: the sonar mate sends n pings in n time slots at n pitches, one per slot and
 * one per pitch, so that every pair of pings has a different (time gap, pitch gap) vector and echoes
 * never alias (a Costas array). A backtracking counter checks only vectors to the newest ping, and
 * the Welch construction gives one of size p - 1 for any prime p from a primitive root.
 */
public final class SonarPings {

    public static final String QUEST_ID = "q_sonar_pings";

    private SonarPings() { }

    /** True when perm is a permutation of 0..n-1 with all displacement vectors distinct. */
    public static boolean isCostas(int[] perm) {
        int n = perm.length;
        boolean[] used = new boolean[n];
        for (int v : perm) {
            if (v < 0 || v >= n || used[v]) {
                return false;
            }
            used[v] = true;
        }
        for (int gap = 1; gap < n; gap++) {
            boolean[] seen = new boolean[2 * n];
            for (int i = 0; i + gap < n; i++) {
                int d = perm[i + gap] - perm[i] + n;
                if (seen[d]) {
                    return false;
                }
                seen[d] = true;
            }
        }
        return true;
    }

    /** Number of Costas arrays of order n (0..10). */
    public static long count(int n) {
        if (n < 0 || n > 10) {
            throw new IllegalArgumentException("n 0..10");
        }
        return grow(new int[n], 0, new boolean[n], new boolean[n][2 * n]);
    }

    private static long grow(int[] perm, int i, boolean[] used, boolean[][] seen) {
        int n = perm.length;
        if (i == n) {
            return 1;
        }
        long total = 0;
        for (int v = 0; v < n; v++) {
            if (used[v]) {
                continue;
            }
            boolean ok = true;
            int g = 1;
            for (; g <= i && ok; g++) {
                ok = !seen[g][v - perm[i - g] + n];
            }
            if (!ok) {
                continue;
            }
            for (int h = 1; h <= i; h++) {
                seen[h][v - perm[i - h] + n] = true;
            }
            used[v] = true;
            perm[i] = v;
            total += grow(perm, i + 1, used, seen);
            used[v] = false;
            for (int h = 1; h <= i; h++) {
                seen[h][v - perm[i - h] + n] = false;
            }
        }
        return total;
    }

    private static boolean isPrime(int p) {
        if (p < 2) {
            return false;
        }
        for (int d = 2; d * d <= p; d++) {
            if (p % d == 0) {
                return false;
            }
        }
        return true;
    }

    /** Welch Costas array of order p - 1 for a prime p up to 10007. */
    public static int[] welch(int p) {
        if (p > 10_007 || !isPrime(p)) {
            throw new IllegalArgumentException("p must be a prime up to 10007: " + p);
        }
        for (int g = 1; g < p; g++) {
            int[] perm = new int[p - 1];
            boolean[] hit = new boolean[p];
            long x = 1;
            boolean primitive = true;
            for (int i = 0; i < p - 1 && primitive; i++) {
                x = x * g % p;
                primitive = !hit[(int) x];
                hit[(int) x] = true;
                perm[i] = (int) x - 1;
            }
            if (primitive) {
                return perm;
            }
        }
        throw new IllegalStateException("no primitive root");
    }

    /** Quest q_sonar_pings: hand in a ping schedule of order n that never aliases. */
    public static boolean quest(int n, int[] answer) {
        return answer.length == n && isCostas(answer);
    }
}