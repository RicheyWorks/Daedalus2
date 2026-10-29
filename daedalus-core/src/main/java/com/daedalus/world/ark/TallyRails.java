// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G394 The Tally Rails: the purser shades cells on an n x n rail board, n 1..6 (Kakurasu). A
 * shaded cell in column c (1-based) adds c to its row tally, and a shaded cell in row r (1-based)
 * adds r to its column tally. Every row and column tally must match its clue. Boards use 1 for
 * shaded and 0 for open.
 */
public final class TallyRails {

    public static final String QUEST_ID = "q_tally_rails";

    private TallyRails() { }

    private static void checkClues(int[] rowClues, int[] colClues) {
        int n = rowClues.length;
        if (n < 1 || n > 6 || colClues.length != n) {
            throw new IllegalArgumentException("n 1..6, matching clue lengths");
        }
        int max = n * (n + 1) / 2;
        for (int i = 0; i < n; i++) {
            if (rowClues[i] < 0 || rowClues[i] > max || colClues[i] < 0 || colClues[i] > max) {
                throw new IllegalArgumentException("clue 0..n(n+1)/2");
            }
        }
    }

    /** True when the board is n x n of 0/1 and every tally matches its clue. */
    public static boolean isValid(int[] rowClues, int[] colClues, int[][] board) {
        checkClues(rowClues, colClues);
        int n = rowClues.length;
        if (board.length != n) {
            return false;
        }
        int[] col = new int[n];
        for (int r = 0; r < n; r++) {
            if (board[r].length != n) {
                return false;
            }
            int row = 0;
            for (int c = 0; c < n; c++) {
                int v = board[r][c];
                if (v != 0 && v != 1) {
                    return false;
                }
                row += v * (c + 1);
                col[c] += v * (r + 1);
            }
            if (row != rowClues[r]) {
                return false;
            }
        }
        for (int c = 0; c < n; c++) {
            if (col[c] != colClues[c]) {
                return false;
            }
        }
        return true;
    }

    private static final class Search {
        final int[] rowClues;
        final int[] colClues;
        final int n;
        final int[] masks;
        final int[] col;
        final long limit;
        long count;
        int[][] first = new int[0][];

        Search(int[] rowClues, int[] colClues, long limit) {
            this.rowClues = rowClues;
            this.colClues = colClues;
            this.n = rowClues.length;
            this.masks = new int[n];
            this.col = new int[n];
            this.limit = limit;
        }

        void run(int r) {
            if (count >= limit) {
                return;
            }
            if (r == n) {
                for (int c = 0; c < n; c++) {
                    if (col[c] != colClues[c]) {
                        return;
                    }
                }
                if (count == 0) {
                    first = new int[n][n];
                    for (int i = 0; i < n; i++) {
                        for (int c = 0; c < n; c++) {
                            first[i][c] = masks[i] >> c & 1;
                        }
                    }
                }
                count++;
                return;
            }
            for (int m = 0; m < (1 << n); m++) {
                int sum = 0;
                boolean ok = true;
                for (int c = 0; c < n; c++) {
                    if ((m >> c & 1) != 0) {
                        sum += c + 1;
                        if (col[c] + r + 1 > colClues[c]) {
                            ok = false;
                        }
                    }
                }
                if (!ok || sum != rowClues[r]) {
                    continue;
                }
                for (int c = 0; c < n; c++) {
                    col[c] += (m >> c & 1) * (r + 1);
                }
                masks[r] = m;
                run(r + 1);
                for (int c = 0; c < n; c++) {
                    col[c] -= (m >> c & 1) * (r + 1);
                }
            }
        }
    }

    /** Number of boards meeting every clue, stopping at limit. */
    public static long count(int[] rowClues, int[] colClues, long limit) {
        checkClues(rowClues, colClues);
        Search s = new Search(rowClues, colClues, limit);
        s.run(0);
        return s.count;
    }

    /** First board meeting every clue, or an empty array when none exists. */
    public static int[][] solve(int[] rowClues, int[] colClues) {
        checkClues(rowClues, colClues);
        Search s = new Search(rowClues, colClues, 1);
        s.run(0);
        return s.first;
    }

    /** Quest hook: the player's board must meet every clue. */
    public static boolean quest(int[] rowClues, int[] colClues, int[][] answer) {
        return isValid(rowClues, colClues, answer);
    }
}