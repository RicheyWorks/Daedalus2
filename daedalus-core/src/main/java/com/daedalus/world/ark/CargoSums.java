// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G370 The Cargo Sums: the hold is a Kakuro grid. Each run of cells must hold distinct digits 1..9
 * that add up to the run's clue. The clerk lists every digit set that fits a clue, the digits
 * every such set shares, and solves a grid given as runs over numbered cells by backtracking with
 * per-run sum bounds.
 */
public final class CargoSums {

    public static final String QUEST_ID = "q_cargo_sums";

    private CargoSums() { }

    /** Every digit set (bit d set for digit d, 1..9) of the given size adding to sum. */
    public static int[] combos(int sum, int cells) {
        if (cells < 1 || cells > 9) {
            throw new IllegalArgumentException("cells 1..9");
        }
        int[] out = new int[512];
        int n = 0;
        for (int mask = 2; mask < 1024; mask += 2) {
            if (Integer.bitCount(mask) != cells) {
                continue;
            }
            int s = 0;
            for (int dgt = 1; dgt <= 9; dgt++) {
                if ((mask >> dgt & 1) != 0) {
                    s += dgt;
                }
            }
            if (s == sum) {
                out[n++] = mask;
            }
        }
        return Arrays.copyOf(out, n);
    }

    /** Digits in every fitting set (a bit mask), 0 when none or no set fits. */
    public static int forced(int sum, int cells) {
        int[] cs = combos(sum, cells);
        if (cs.length == 0) {
            return 0;
        }
        int and = cs[0];
        for (int c : cs) {
            and &= c;
        }
        return and;
    }

    private static void checkRuns(int cellCount, int[][] runs, int[] sums) {
        if (cellCount < 1 || cellCount > 40 || runs.length != sums.length) {
            throw new IllegalArgumentException("1..40 cells and one sum per run");
        }
        for (int[] run : runs) {
            if (run.length < 1 || run.length > 9) {
                throw new IllegalArgumentException("runs hold 1..9 cells");
            }
            for (int c : run) {
                if (c < 0 || c >= cellCount) {
                    throw new IllegalArgumentException("cell out of range");
                }
            }
        }
    }

    /** Number of fillings (up to limit). */
    public static int count(int cellCount, int[][] runs, int[] sums, int limit) {
        checkRuns(cellCount, runs, sums);
        int[] found = new int[1];
        fill(0, new int[cellCount], runs, sums, limit, found, new int[0], cellIndex(cellCount, runs));
        return found[0];
    }

    /** One filling (digits per cell), or an empty array when none exists. */
    public static int[] solve(int cellCount, int[][] runs, int[] sums) {
        checkRuns(cellCount, runs, sums);
        int[] out = new int[cellCount];
        int[] found = new int[1];
        fill(0, new int[cellCount], runs, sums, 1, found, out, cellIndex(cellCount, runs));
        return found[0] > 0 ? out : new int[0];
    }

    private static int[][] cellIndex(int cellCount, int[][] runs) {
        int[] k = new int[cellCount];
        for (int[] run : runs) {
            for (int c : run) {
                k[c]++;
            }
        }
        int[][] idx = new int[cellCount][];
        for (int c = 0; c < cellCount; c++) {
            idx[c] = new int[k[c]];
            k[c] = 0;
        }
        for (int r = 0; r < runs.length; r++) {
            for (int c : runs[r]) {
                idx[c][k[c]++] = r;
            }
        }
        return idx;
    }

    private static void fill(int cell, int[] digits, int[][] runs, int[] sums, int limit, int[] found,
            int[] out, int[][] runsOf) {
        if (found[0] >= limit) {
            return;
        }
        if (cell == digits.length) {
            found[0]++;
            if (found[0] == 1 && out.length == digits.length) {
                System.arraycopy(digits, 0, out, 0, digits.length);
            }
            return;
        }
        for (int v = 1; v <= 9; v++) {
            digits[cell] = v;
            if (runsOk(cell, digits, runs, sums, runsOf[cell])) {
                fill(cell + 1, digits, runs, sums, limit, found, out, runsOf);
            }
        }
        digits[cell] = 0;
    }

    private static boolean runsOk(int cell, int[] digits, int[][] runs, int[] sums, int[] mine) {
        for (int r : mine) {
            int sum = 0;
            int empty = 0;
            int used = 0;
            for (int c : runs[r]) {
                int v = c <= cell ? digits[c] : 0;
                if (v == 0) {
                    empty++;
                } else {
                    if ((used >> v & 1) != 0) {
                        return false;
                    }
                    used |= 1 << v;
                    sum += v;
                }
            }
            int lo = empty * (empty + 1) / 2;
            int hi = empty * (19 - empty) / 2;
            if (sum + lo > sums[r] || sum + hi < sums[r]) {
                return false;
            }
        }
        return true;
    }

    /** True when the filling uses 1..9 and every run is distinct and adds to its clue. */
    public static boolean isFilled(int[][] runs, int[] sums, int[] digits) {
        for (int v : digits) {
            if (v < 1 || v > 9) {
                return false;
            }
        }
        for (int r = 0; r < runs.length; r++) {
            int used = 0;
            int sum = 0;
            for (int c : runs[r]) {
                if (c < 0 || c >= digits.length || (used >> digits[c] & 1) != 0) {
                    return false;
                }
                used |= 1 << digits[c];
                sum += digits[c];
            }
            if (sum != sums[r]) {
                return false;
            }
        }
        return true;
    }

    /** Quest q_cargo_sums: fill the hold so every run adds to its clue. */
    public static boolean quest(int[][] runs, int[] sums, int[] answer) {
        return isFilled(runs, sums, answer);
    }
}