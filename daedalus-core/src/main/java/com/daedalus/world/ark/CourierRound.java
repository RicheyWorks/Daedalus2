// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G249 The Courier's Round: the ark's deck courier must visit every cell of an {@code n x n} deck
 * exactly once using only knight's jumps (a knight's tour). {@link #round} runs a backtracking
 * search that tries the Warnsdorff move first (the cell with the fewest onward jumps), which finds
 * a round almost immediately on decks that have one, and gives up after a step budget.
 * Routes are cell indices {@code row * n + col}.
 */
public final class CourierRound {

    public static final String QUEST_ID = "q_courier_round";
    public static final int MAX_DECK = 40;
    public static final long STEP_BUDGET = 2_000_000L;

    private static final int[] DR = {-2, -1, 1, 2, 2, 1, -1, -2};
    private static final int[] DC = {1, 2, 2, 1, -1, -2, -2, -1};

    private CourierRound() { }

    /** A full round from (row, col), or null if none is found within the step budget. */
    public static int[] round(int n, int row, int col) {
        if (n < 1 || n > MAX_DECK || row < 0 || col < 0 || row >= n || col >= n) {
            throw new IllegalArgumentException("bad deck or start");
        }
        int[] route = new int[n * n];
        boolean[] seen = new boolean[n * n];
        route[0] = row * n + col;
        seen[route[0]] = true;
        long[] steps = {0};
        return search(n, route, seen, 1, steps) ? route : null;
    }

    private static boolean search(int n, int[] route, boolean[] seen, int depth, long[] steps) {
        if (depth == n * n) {
            return true;
        }
        if (++steps[0] > STEP_BUDGET) {
            return false;
        }
        int at = route[depth - 1];
        int r = at / n;
        int c = at % n;
        int[] cand = new int[8];
        int[] deg = new int[8];
        int k = 0;
        for (int m = 0; m < 8; m++) {
            int nr = r + DR[m];
            int nc = c + DC[m];
            if (inside(n, nr, nc) && !seen[nr * n + nc]) {
                cand[k] = nr * n + nc;
                deg[k] = onward(n, seen, nr, nc);
                k++;
            }
        }
        for (int i = 1; i < k; i++) {
            for (int j = i; j > 0 && deg[j] < deg[j - 1]; j--) {
                int t = deg[j];
                deg[j] = deg[j - 1];
                deg[j - 1] = t;
                t = cand[j];
                cand[j] = cand[j - 1];
                cand[j - 1] = t;
            }
        }
        for (int i = 0; i < k; i++) {
            route[depth] = cand[i];
            seen[cand[i]] = true;
            if (search(n, route, seen, depth + 1, steps)) {
                return true;
            }
            seen[cand[i]] = false;
            if (steps[0] > STEP_BUDGET) {
                return false;
            }
        }
        return false;
    }

    private static int onward(int n, boolean[] seen, int r, int c) {
        int d = 0;
        for (int m = 0; m < 8; m++) {
            int nr = r + DR[m];
            int nc = c + DC[m];
            if (inside(n, nr, nc) && !seen[nr * n + nc]) {
                d++;
            }
        }
        return d;
    }

    private static boolean inside(int n, int r, int c) {
        return r >= 0 && c >= 0 && r < n && c < n;
    }

    /** True when {@code route} visits all n*n cells once, each step a knight's jump. */
    public static boolean valid(int n, int[] route) {
        if (n < 1 || route == null || route.length != n * n) {
            return false;
        }
        boolean[] seen = new boolean[n * n];
        for (int i = 0; i < route.length; i++) {
            int v = route[i];
            if (v < 0 || v >= n * n || seen[v]) {
                return false;
            }
            seen[v] = true;
            if (i > 0) {
                int dr = Math.abs(v / n - route[i - 1] / n);
                int dc = Math.abs(v % n - route[i - 1] % n);
                if (dr * dc != 2) {
                    return false;
                }
            }
        }
        return true;
    }

    /** Quest q_courier_round: the player's route must be a full round starting at the post. */
    public static boolean quest(int n, int row, int col, int[] route) {
        return valid(n, route) && route[0] == row * n + col;
    }
}
