// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G350 The Mess Table: every pair of n sailors at the mess are either shipmates or strangers. The
 * purser wants a seating with no s mutual shipmates and no t mutual strangers. A backtracking
 * finder decides each pair in turn and only checks groups that contain the newest pair; the first
 * n with no such table is the Ramsey number R(s, t).
 */
public final class MessTable {

    public static final String QUEST_ID = "q_mess_table";

    private static final int MAX_N = 16;

    private MessTable() { }

    private static boolean hasClique(int candidates, int need, int[] adj) {
        if (need == 0) {
            return true;
        }
        if (Integer.bitCount(candidates) < need) {
            return false;
        }
        int c = candidates;
        while (c != 0) {
            int v = Integer.numberOfTrailingZeros(c);
            c &= c - 1;
            if (hasClique(c & adj[v], need - 1, adj)) {
                return true;
            }
        }
        return false;
    }

    private static int[] masks(boolean[][] mates, boolean colour) {
        int n = mates.length;
        int[] adj = new int[n];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (i != j && mates[i][j] == colour) {
                    adj[i] |= 1 << j;
                }
            }
        }
        return adj;
    }

    /** True when the symmetric table has no s mutual shipmates (true) and no t mutual strangers. */
    public static boolean isPeaceful(boolean[][] mates, int s, int t) {
        int n = mates.length;
        if (n > MAX_N || s < 2 || t < 2) {
            throw new IllegalArgumentException("n up to 16, s and t at least 2");
        }
        for (int i = 0; i < n; i++) {
            if (mates[i].length != n) {
                return false;
            }
            for (int j = 0; j < n; j++) {
                if (i != j && mates[i][j] != mates[j][i]) {
                    return false;
                }
            }
        }
        int all = n == 0 ? 0 : (1 << n) - 1;
        return !hasClique(all, s, masks(mates, true)) && !hasClique(all, t, masks(mates, false));
    }

    /** A peaceful table for n sailors, or an empty array when none exists (n up to 10, s, t up to 4). */
    public static boolean[][] find(int n, int s, int t) {
        if (n < 0 || n > 10 || s < 2 || t < 2 || s > 4 || t > 4) {
            throw new IllegalArgumentException("n 0..10, s and t 2..4");
        }
        int[] mate = new int[n];
        int[] stranger = new int[n];
        if (!place(n, 1, 0, s, t, mate, stranger)) {
            return new boolean[0][];
        }
        boolean[][] out = new boolean[n][n];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                out[i][j] = (mate[i] >> j & 1) != 0;
            }
        }
        return out;
    }

    private static boolean place(int n, int j, int i, int s, int t, int[] mate, int[] stranger) {
        if (j >= n) {
            return true;
        }
        int nj = i + 1 < j ? j : j + 1;
        int ni = i + 1 < j ? i + 1 : 0;
        int below = (1 << j) - 1;
        mate[i] |= 1 << j;
        mate[j] |= 1 << i;
        if (!hasClique(mate[i] & mate[j] & below, s - 2, mate) && place(n, nj, ni, s, t, mate, stranger)) {
            return true;
        }
        mate[i] &= ~(1 << j);
        mate[j] &= ~(1 << i);
        stranger[i] |= 1 << j;
        stranger[j] |= 1 << i;
        if (!hasClique(stranger[i] & stranger[j] & below, t - 2, stranger)
                && place(n, nj, ni, s, t, mate, stranger)) {
            return true;
        }
        stranger[i] &= ~(1 << j);
        stranger[j] &= ~(1 << i);
        return false;
    }

    /** Ramsey number R(s, t) for small s, t (only when it is at most 10). */
    public static int ramsey(int s, int t) {
        int n = 1;
        while (n <= 10 && find(n, s, t).length == n) {
            n++;
        }
        if (n > 10) {
            throw new IllegalArgumentException("R(" + s + ", " + t + ") is above 10");
        }
        return n;
    }

    /** Quest q_mess_table: seat n sailors with no 3 mutual shipmates and no 3 mutual strangers. */
    public static boolean quest(int n, boolean[][] answer) {
        return answer.length == n && isPeaceful(answer, 3, 3);
    }
}