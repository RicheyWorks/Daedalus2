// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * G432 The Four Masts: n sails (0 = smallest) are furled on mast 0 and must move to the last
 * mast, one sail at a time, never a bigger sail on a smaller, with p masts in all (Tower of Hanoi
 * for 3 masts, Reve's puzzle for 4). Gives the Frame-Stewart move count, a Frame-Stewart plan of
 * {from, to} moves, a move checker and the exact fewest moves by breadth-first search for small
 * cases.
 */
public final class FourMasts {

    public static final String QUEST_ID = "q_four_masts";
    public static final int MAX_COUNT = 30;
    public static final int MAX_PLAN = 12;
    public static final int MAX_STATES = 1 << 20;

    private FourMasts() { }

    private static void check(int n, int p, int maxN) {
        if (n < 0 || n > maxN || p < 3 || p > 6) {
            throw new IllegalArgumentException("discs 0-" + maxN + ", masts 3-6");
        }
    }

    /** Frame-Stewart moves for n sails and p masts. */
    public static long frameStewart(int n, int p) {
        check(n, p, MAX_COUNT);
        return fs(n, p, split(n, p));
    }

    private static long[][] split(int n, int p) {
        long[][] f = new long[p + 1][n + 1];
        for (int q = 3; q <= p; q++) {
            for (int m = 1; m <= n; m++) {
                if (q == 3) {
                    f[q][m] = (1L << m) - 1;
                } else if (m == 1) {
                    f[q][m] = 1;
                } else {
                    long best = Long.MAX_VALUE;
                    for (int t = 1; t < m; t++) {
                        best = Math.min(best, 2 * f[q][t] + f[q - 1][m - t]);
                    }
                    f[q][m] = best;
                }
            }
        }
        return f;
    }

    private static long fs(int n, int p, long[][] f) {
        return f[p][n];
    }

    /** A Frame-Stewart plan of {from, to} moves taking every sail from mast 0 to mast p - 1. */
    public static int[][] plan(int n, int p) {
        check(n, p, MAX_PLAN);
        long[][] f = split(n, p);
        List<Integer> masts = new ArrayList<>();
        for (int i = 0; i < p; i++) {
            masts.add(i);
        }
        List<int[]> out = new ArrayList<>();
        build(n, 0, p - 1, masts, f, out);
        return out.toArray(new int[0][]);
    }

    private static void build(int n, int from, int to, List<Integer> masts, long[][] f, List<int[]> out) {
        if (n == 0) {
            return;
        }
        if (n == 1) {
            out.add(new int[] {from, to});
            return;
        }
        int q = masts.size();
        int spare = -1;
        for (int m : masts) {
            if (m != from && m != to) {
                spare = m;
                break;
            }
        }
        if (q == 3) {
            build(n - 1, from, spare, masts, f, out);
            out.add(new int[] {from, to});
            build(n - 1, spare, to, masts, f, out);
            return;
        }
        int bestT = 1;
        for (int t = 1; t < n; t++) {
            if (2 * f[q][t] + f[q - 1][n - t] < 2 * f[q][bestT] + f[q - 1][n - bestT]) {
                bestT = t;
            }
        }
        build(bestT, from, spare, masts, f, out);
        List<Integer> fewer = new ArrayList<>(masts);
        fewer.remove(Integer.valueOf(spare));
        build(n - bestT, from, to, fewer, f, out);
        build(bestT, spare, to, masts, f, out);
    }

    /** True when the moves are legal and end with every sail on the last mast. */
    public static boolean valid(int n, int p, int[][] moves) {
        check(n, p, MAX_PLAN);
        List<ArrayDeque<Integer>> st = new ArrayList<>();
        for (int i = 0; i < p; i++) {
            st.add(new ArrayDeque<>());
        }
        for (int d = n - 1; d >= 0; d--) {
            st.get(0).push(d);
        }
        for (int[] mv : moves) {
            if (mv == null || mv.length != 2 || mv[0] < 0 || mv[1] < 0 || mv[0] >= p || mv[1] >= p
                    || mv[0] == mv[1] || st.get(mv[0]).isEmpty()) {
                return false;
            }
            Integer top = st.get(mv[1]).peek();
            if (top != null && top < st.get(mv[0]).peek()) {
                return false;
            }
            st.get(mv[1]).push(st.get(mv[0]).pop());
        }
        return st.get(p - 1).size() == n;
    }

    /** Exact fewest moves by BFS over sail positions (p^n states, at most 2^20). */
    public static int fewest(int n, int p) {
        check(n, p, MAX_PLAN);
        long states = 1;
        for (int i = 0; i < n; i++) {
            states *= p;
        }
        if (states > MAX_STATES) {
            throw new IllegalArgumentException("too many states for exact search");
        }
        int s = (int) states;
        int[] dist = new int[s];
        Arrays.fill(dist, -1);
        int goal = s - 1;
        dist[0] = 0;
        ArrayDeque<Integer> q = new ArrayDeque<>();
        q.add(0);
        int[] pos = new int[n];
        int[] pow = new int[n];
        for (int i = 0; i < n; i++) {
            pow[i] = i == 0 ? 1 : pow[i - 1] * p;
        }
        while (!q.isEmpty()) {
            int cur = q.poll();
            if (cur == goal) {
                return dist[cur];
            }
            int x = cur;
            for (int i = 0; i < n; i++) {
                pos[i] = x % p;
                x /= p;
            }
            for (int from = 0; from < p; from++) {
                int top = -1;
                for (int i = 0; i < n && top < 0; i++) {
                    if (pos[i] == from) {
                        top = i;
                    }
                }
                if (top < 0) {
                    continue;
                }
                for (int to = 0; to < p; to++) {
                    boolean ok = to != from;
                    for (int i = 0; i < top && ok; i++) {
                        ok = pos[i] != to;
                    }
                    if (ok) {
                        int nx = cur + (to - from) * pow[top];
                        if (dist[nx] < 0) {
                            dist[nx] = dist[cur] + 1;
                            q.add(nx);
                        }
                    }
                }
            }
        }
        return dist[goal];
    }

    /** Quest q_four_masts: the bosun names the Frame-Stewart moves for n sails on four masts. */
    public static boolean quest(int n, long answer) {
        return frameStewart(n, 4) == answer;
    }
}