// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G411 The Skittle Row: deckhands bowl at rows of skittles. Each turn a player takes k skittles
 * from one row as the octal code allows, and the last player to move wins. Code digit k (k = 1 to
 * 4) is a bit set: 1 = may take a whole row of exactly k, 2 = may take k from one end leaving one
 * row, 4 = may take k from the middle leaving two rows. "0.77" is Kayles, "0.137" is Dawson's
 * chess. Gives the Grundy table by mex, the nim-sum of a set of rows and a winning move.
 */
public final class SkittleRow {

    public static final String QUEST_ID = "q_skittle_row";
    public static final String KAYLES = "0.77";
    public static final String DAWSON = "0.137";
    public static final int MAX_ROW = 100_000;

    private SkittleRow() { }

    private static int[] digits(String code) {
        if (code == null || !code.matches("0\\.[0-7]{1,4}")) {
            throw new IllegalArgumentException("octal code must look like 0.d with 1-4 digits 0-7");
        }
        int[] d = new int[code.length() - 1];
        for (int k = 1; k < d.length; k++) {
            d[k] = code.charAt(k + 1) - '0';
        }
        return d;
    }

    /** g[n] for 0 <= n <= max under the octal code. */
    public static int[] grundy(String code, int max) {
        int[] d = digits(code);
        if (max < 0 || max > MAX_ROW) {
            throw new IllegalArgumentException("max out of range: " + max);
        }
        int[] g = new int[max + 1];
        boolean[] seen = new boolean[64];
        for (int n = 1; n <= max; n++) {
            for (int k = 1; k < d.length && k <= n; k++) {
                int r = n - k;
                if (r == 0 && (d[k] & 1) != 0) {
                    seen[0] = true;
                }
                if (r > 0 && (d[k] & 2) != 0) {
                    mark(seen, g[r]);
                }
                if (r > 1 && (d[k] & 4) != 0) {
                    for (int a = 1; a <= r - a; a++) {
                        mark(seen, g[a] ^ g[r - a]);
                    }
                }
            }
            int v = 0;
            while (v < seen.length && seen[v]) {
                v++;
            }
            g[n] = v;
            Arrays.fill(seen, false);
        }
        return g;
    }

    private static void mark(boolean[] seen, int v) {
        if (v >= seen.length) {
            throw new IllegalStateException("grundy value too large: " + v);
        }
        seen[v] = true;
    }

    /** Nim-sum of the rows; non-zero means the player to move wins. */
    public static int nimSum(String code, int... rows) {
        int max = 0;
        for (int r : rows) {
            if (r < 0) {
                throw new IllegalArgumentException("negative row: " + r);
            }
            max = Math.max(max, r);
        }
        int[] g = grundy(code, max);
        int x = 0;
        for (int r : rows) {
            x ^= g[r];
        }
        return x;
    }

    /**
     * A winning move as {row index, skittles taken, left part, right part}, or an empty array when
     * the player to move loses.
     */
    public static int[] winningMove(String code, int... rows) {
        int[] d = digits(code);
        int x = nimSum(code, rows);
        if (x == 0) {
            return new int[0];
        }
        int max = Arrays.stream(rows).max().orElse(0);
        int[] g = grundy(code, max);
        for (int i = 0; i < rows.length; i++) {
            int n = rows[i];
            int want = x ^ g[n];
            for (int k = 1; k < d.length && k <= n; k++) {
                int r = n - k;
                if (r == 0 && (d[k] & 1) != 0 && want == 0) {
                    return new int[] {i, k, 0, 0};
                }
                if (r > 0 && (d[k] & 2) != 0 && g[r] == want) {
                    return new int[] {i, k, r, 0};
                }
                if (r > 1 && (d[k] & 4) != 0) {
                    for (int a = 1; a <= r - a; a++) {
                        if ((g[a] ^ g[r - a]) == want) {
                            return new int[] {i, k, a, r - a};
                        }
                    }
                }
            }
        }
        throw new IllegalStateException("Sprague-Grundy guarantees a winning move");
    }

    /** Quest q_skittle_row: the bosun says whether the first bowler wins at Kayles. */
    public static boolean quest(int[] rows, boolean firstWins) {
        return (nimSum(KAYLES, rows) != 0) == firstWins;
    }
}