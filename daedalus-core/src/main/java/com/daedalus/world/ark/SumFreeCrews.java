// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G344 The Sum-Free Crews: berths 1..n are shared out among k crews, and the bosun forbids any crew
 * from holding berths x, y and x + y (x = y allowed), a Schur partition. A backtracking finder
 * assigns berths in order, opening a new crew only when needed, and the largest n that can be
 * split is the Schur number (1, 4, 13, 44, ...).
 */
public final class SumFreeCrews {

    public static final String QUEST_ID = "q_sum_free_crews";

    private SumFreeCrews() { }

    /** True when crew[i] (for berth i + 1) is in 0..k-1 and no crew holds x, y and x + y. */
    public static boolean isValid(int[] crew, int k) {
        int n = crew.length;
        for (int c : crew) {
            if (c < 0 || c >= k) {
                return false;
            }
        }
        for (int x = 1; x <= n; x++) {
            for (int y = x; x + y <= n; y++) {
                if (crew[x - 1] == crew[y - 1] && crew[x - 1] == crew[x + y - 1]) {
                    return false;
                }
            }
        }
        return true;
    }

    /** A valid split of 1..n into k crews, or an empty array when none exists (n up to 60, k up to 4; with 4 crews n up to 44). */
    public static int[] split(int n, int k) {
        if (n < 1 || n > 60 || k < 1 || k > 4 || (k == 4 && n > 44)) {
            throw new IllegalArgumentException("n 1..60 and k 1..4 (n up to 44 for k 4)");
        }
        int[] crew = new int[n];
        return place(crew, 1, k, 0) ? crew : new int[0];
    }

    private static boolean place(int[] crew, int berth, int k, int used) {
        if (berth > crew.length) {
            return true;
        }
        int limit = Math.min(k, used + 1);
        for (int c = 0; c < limit; c++) {
            if (fits(crew, berth, c)) {
                crew[berth - 1] = c;
                if (place(crew, berth + 1, k, Math.max(used, c + 1))) {
                    return true;
                }
            }
        }
        return false;
    }

    private static boolean fits(int[] crew, int berth, int c) {
        for (int x = 1; x <= berth / 2; x++) {
            if (crew[x - 1] == c && crew[berth - x - 1] == c) {
                return false;
            }
        }
        return true;
    }

    /** Largest n that k crews can split (the Schur number), for k up to 3. */
    public static int largest(int k) {
        if (k < 1 || k > 3) {
            throw new IllegalArgumentException("k 1..3");
        }
        int n = 1;
        while (split(n + 1, k).length > 0) {
            n++;
        }
        return n;
    }

    /** Quest q_sum_free_crews: hand in a valid split of 1..n into k crews. */
    public static boolean quest(int n, int k, int[] answer) {
        return answer.length == n && isValid(answer, k);
    }
}