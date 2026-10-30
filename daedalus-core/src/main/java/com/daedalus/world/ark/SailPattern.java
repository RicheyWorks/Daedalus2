// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * G367 The Sail Pattern: the sailmaker's chart gives, for each row and column of a sail grid, the
 * lengths of the painted runs in order (a nonogram). The solver tries every painting of each row
 * that fits its clue, and after each row checks every column's runs so far against its clue.
 */
public final class SailPattern {

    public static final String QUEST_ID = "q_sail_pattern";

    private SailPattern() { }

    private static int[] runs(int[] cells) {
        List<Integer> out = new ArrayList<>();
        int run = 0;
        for (int v : cells) {
            if (v == 1) {
                run++;
            } else if (v == 0) {
                if (run > 0) {
                    out.add(run);
                }
                run = 0;
            } else {
                throw new IllegalArgumentException("cells are 0 or 1");
            }
        }
        if (run > 0) {
            out.add(run);
        }
        return out.stream().mapToInt(Integer::intValue).toArray();
    }

    /** Row clues of a 0/1 grid. */
    public static int[][] rowClues(int[][] grid) {
        int[][] out = new int[grid.length][];
        for (int r = 0; r < grid.length; r++) {
            out[r] = runs(grid[r]);
        }
        return out;
    }

    /** Column clues of a rectangular 0/1 grid. */
    public static int[][] colClues(int[][] grid) {
        int w = grid.length == 0 ? 0 : grid[0].length;
        int[][] out = new int[w][];
        for (int c = 0; c < w; c++) {
            int[] col = new int[grid.length];
            for (int r = 0; r < grid.length; r++) {
                col[r] = grid[r][c];
            }
            out[c] = runs(col);
        }
        return out;
    }

    /** Number of paintings matching the clues, stopping at limit (grids up to 8 x 8). */
    public static int count(int[][] rows, int[][] cols, int limit) {
        return search(rows, cols, limit, new int[rows.length][]);
    }

    /** One painting matching the clues, or an empty array when none exists. */
    public static int[][] solve(int[][] rows, int[][] cols) {
        int[][] out = new int[rows.length][];
        return search(rows, cols, 1, out) > 0 ? out : new int[0][];
    }

    private static int search(int[][] rows, int[][] cols, int limit, int[][] out) {
        int h = rows.length;
        int w = cols.length;
        if (h < 1 || w < 1 || h > 8 || w > 8 || limit < 1) {
            throw new IllegalArgumentException("grid 1..8 x 1..8, limit >= 1");
        }
        List<List<int[]>> options = new ArrayList<>();
        for (int[] clue : rows) {
            List<int[]> fits = new ArrayList<>();
            for (int mask = 0; mask < (1 << w); mask++) {
                int[] cells = new int[w];
                for (int c = 0; c < w; c++) {
                    cells[c] = mask >> c & 1;
                }
                if (Arrays.equals(runs(cells), clue)) {
                    fits.add(cells);
                }
            }
            options.add(fits);
        }
        int[][] grid = new int[h][];
        int[] found = new int[1];
        place(0, options, cols, grid, limit, found, out);
        return found[0];
    }

    private static void place(int r, List<List<int[]>> options, int[][] cols, int[][] grid, int limit,
            int[] found, int[][] out) {
        if (found[0] >= limit) {
            return;
        }
        int h = grid.length;
        if (r == h) {
            found[0]++;
            if (found[0] == 1) {
                for (int i = 0; i < h; i++) {
                    out[i] = grid[i].clone();
                }
            }
            return;
        }
        for (int[] row : options.get(r)) {
            grid[r] = row;
            if (columnsFit(grid, r + 1, cols)) {
                place(r + 1, options, cols, grid, limit, found, out);
            }
        }
    }

    private static boolean columnsFit(int[][] grid, int filled, int[][] cols) {
        boolean done = filled == grid.length;
        for (int c = 0; c < cols.length; c++) {
            int[] col = new int[filled];
            for (int r = 0; r < filled; r++) {
                col[r] = grid[r][c];
            }
            int[] got = runs(col);
            int[] want = cols[c];
            if (done) {
                if (!Arrays.equals(got, want)) {
                    return false;
                }
                continue;
            }
            if (got.length > want.length) {
                return false;
            }
            boolean open = filled > 0 && col[filled - 1] == 1;
            for (int i = 0; i < got.length; i++) {
                boolean last = i == got.length - 1;
                if (last && open ? got[i] > want[i] : got[i] != want[i]) {
                    return false;
                }
            }
        }
        return true;
    }

    /** Quest q_sail_pattern: paint a grid that matches the chart's clues. */
    public static boolean quest(int[][] rows, int[][] cols, int[][] answer) {
        if (answer.length != rows.length) {
            return false;
        }
        for (int[] row : answer) {
            if (row.length != cols.length) {
                return false;
            }
        }
        return Arrays.deepEquals(rowClues(answer), rows) && Arrays.deepEquals(colClues(answer), cols);
    }
}