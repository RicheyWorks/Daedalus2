// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G392 The Signal Flags: the signaller sets an n x n board of red (0) and white (1) flags, n even
 * and 2..6, so every row and column has equal reds and whites, no three equal flags sit in a
 * line, and no two rows or two columns repeat (Binairo / Takuzu). Givens use -1 for blank.
 */
public final class SignalFlags {

    public static final String QUEST_ID = "q_signal_flags";

    private SignalFlags() { }

    private static void checkGivens(int[][] givens) {
        int n = givens.length;
        if (n < 2 || n > 6 || (n & 1) != 0) {
            throw new IllegalArgumentException("n even 2..6");
        }
        for (int[] row : givens) {
            if (row.length != n) {
                throw new IllegalArgumentException("square");
            }
            for (int v : row) {
                if (v < -1 || v > 1) {
                    throw new IllegalArgumentException("cell -1..1");
                }
            }
        }
    }

    private static boolean lineOk(int[] line) {
        int ones = 0;
        for (int i = 0; i < line.length; i++) {
            if (line[i] != 0 && line[i] != 1) {
                return false;
            }
            ones += line[i];
            if (i >= 2 && line[i] == line[i - 1] && line[i] == line[i - 2]) {
                return false;
            }
        }
        return ones * 2 == line.length;
    }

    /** True when the full board meets every rule and every given. */
    public static boolean isValid(int[][] givens, int[][] board) {
        checkGivens(givens);
        int n = givens.length;
        if (board.length != n) {
            return false;
        }
        int[] rowCode = new int[n];
        int[] colCode = new int[n];
        for (int r = 0; r < n; r++) {
            if (board[r].length != n || !lineOk(board[r])) {
                return false;
            }
            int[] col = new int[n];
            for (int c = 0; c < n; c++) {
                col[c] = board[c][r];
                if (givens[r][c] >= 0 && givens[r][c] != board[r][c]) {
                    return false;
                }
            }
            if (!lineOk(col)) {
                return false;
            }
            for (int c = 0; c < n; c++) {
                rowCode[r] = rowCode[r] * 2 + board[r][c];
                colCode[r] = colCode[r] * 2 + col[c];
            }
        }
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (rowCode[i] == rowCode[j] || colCode[i] == colCode[j]) {
                    return false;
                }
            }
        }
        return true;
    }

    private static final class Search {
        final int[][] givens;
        final int n;
        final int[][] b;
        final int[] rowOnes;
        final int[] colOnes;
        final long limit;
        long count;
        int[][] first = new int[0][];

        Search(int[][] givens, long limit) {
            this.givens = givens;
            this.n = givens.length;
            this.b = new int[n][n];
            this.rowOnes = new int[n];
            this.colOnes = new int[n];
            this.limit = limit;
        }

        void run(int cell) {
            if (count >= limit) {
                return;
            }
            if (cell == n * n) {
                if (isValid(givens, b)) {
                    if (count == 0) {
                        first = new int[n][];
                        for (int r = 0; r < n; r++) {
                            first[r] = b[r].clone();
                        }
                    }
                    count++;
                }
                return;
            }
            int r = cell / n;
            int c = cell % n;
            int half = n / 2;
            for (int v = 0; v <= 1; v++) {
                if (givens[r][c] >= 0 && givens[r][c] != v) {
                    continue;
                }
                if (c >= 2 && b[r][c - 1] == v && b[r][c - 2] == v
                    || r >= 2 && b[r - 1][c] == v && b[r - 2][c] == v) {
                    continue;
                }
                int ro = rowOnes[r] + v;
                int co = colOnes[c] + v;
                if (ro > half || c + 1 - ro > half || co > half || r + 1 - co > half) {
                    continue;
                }
                b[r][c] = v;
                rowOnes[r] = ro;
                colOnes[c] = co;
                run(cell + 1);
                rowOnes[r] -= v;
                colOnes[c] -= v;
                b[r][c] = 0;
            }
        }
    }

    /** Number of valid boards, stopping at limit. */
    public static long count(int[][] givens, long limit) {
        checkGivens(givens);
        Search s = new Search(givens, limit);
        s.run(0);
        return s.count;
    }

    /** First valid board, or an empty array when none exists. */
    public static int[][] solve(int[][] givens) {
        checkGivens(givens);
        Search s = new Search(givens, 1);
        s.run(0);
        return s.first;
    }

    /** Quest hook: the player's board must meet every rule and given. */
    public static boolean quest(int[][] givens, int[][] answer) {
        return isValid(givens, answer);
    }
}