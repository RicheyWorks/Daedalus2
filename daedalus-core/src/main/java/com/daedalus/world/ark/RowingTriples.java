// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G355 The Rowing Triples: the cox seats n rowers in boats of three so every pair of rowers shares
 * exactly one boat (a Steiner triple system). One exists exactly when n mod 6 is 1 or 3. The
 * builder repeatedly takes the first pair not yet in a boat and tries each third rower that is
 * free with both, backtracking on a dead end.
 */
public final class RowingTriples {

    public static final String QUEST_ID = "q_rowing_triples";

    private RowingTriples() { }

    public static boolean exists(int n) {
        if (n < 1) {
            throw new IllegalArgumentException("n " + n);
        }
        return n % 6 == 1 || n % 6 == 3;
    }

    /** True when every pair of rowers 0..n-1 shares exactly one of the boats. */
    public static boolean isSystem(int n, int[][] boats) {
        if (n < 1) {
            return false;
        }
        boolean[][] met = new boolean[n][n];
        int pairs = 0;
        for (int[] b : boats) {
            if (b.length != 3) {
                return false;
            }
            for (int i = 0; i < 3; i++) {
                if (b[i] < 0 || b[i] >= n) {
                    return false;
                }
            }
            for (int i = 0; i < 3; i++) {
                for (int j = i + 1; j < 3; j++) {
                    int x = b[i];
                    int y = b[j];
                    if (x == y || met[x][y]) {
                        return false;
                    }
                    met[x][y] = true;
                    met[y][x] = true;
                    pairs++;
                }
            }
        }
        return pairs == n * (n - 1) / 2;
    }

    /** A triple system on n rowers (n up to 15), or an empty array when none exists. */
    public static int[][] build(int n) {
        if (n < 1 || n > 15) {
            throw new IllegalArgumentException("n 1..15");
        }
        if (!exists(n)) {
            return new int[0][];
        }
        int[][] boats = new int[n * (n - 1) / 6][];
        boolean[][] met = new boolean[n][n];
        place(n, met, boats, 0);
        return boats;
    }

    private static boolean place(int n, boolean[][] met, int[][] boats, int count) {
        if (count == boats.length) {
            return true;
        }
        int a = -1;
        int b = -1;
        for (int i = 0; i < n && a < 0; i++) {
            for (int j = i + 1; j < n; j++) {
                if (!met[i][j]) {
                    a = i;
                    b = j;
                    break;
                }
            }
        }
        for (int c = b + 1; c < n; c++) {
            if (!met[a][c] && !met[b][c]) {
                set(met, a, b, c, true);
                boats[count] = new int[] {a, b, c};
                if (place(n, met, boats, count + 1)) {
                    return true;
                }
                set(met, a, b, c, false);
            }
        }
        return false;
    }

    private static void set(boolean[][] met, int a, int b, int c, boolean v) {
        met[a][b] = v;
        met[b][a] = v;
        met[a][c] = v;
        met[c][a] = v;
        met[b][c] = v;
        met[c][b] = v;
    }

    /** Quest q_rowing_triples: seat n rowers so every pair shares exactly one boat. */
    public static boolean quest(int n, int[][] answer) {
        return isSystem(n, answer);
    }
}