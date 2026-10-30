// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G385 The Reef Isles: the chart maker floods an R x C reef (sides 1..5, at most 20 cells) so
 * that every unflooded island holds exactly one marker equal to its size, all flooded water is
 * connected, and no 2x2 block is all water (Nurikabe). Clue 0 means no marker. The solver
 * decides cells in row-major order, never floods a marker or completes a 2x2 pool, and checks
 * the island and water rules at the end.
 */
public final class ReefIsles {

    public static final String QUEST_ID = "q_reef_isles";

    private ReefIsles() { }

    private static void checkClues(int[][] clues) {
        int r = clues.length;
        if (r < 1 || r > 5) {
            throw new IllegalArgumentException("rows 1..5");
        }
        int c = clues[0].length;
        if (c < 1 || c > 5 || r * c > 20) {
            throw new IllegalArgumentException("cols 1..5, at most 20 cells");
        }
        for (int[] row : clues) {
            if (row.length != c) {
                throw new IllegalArgumentException("ragged");
            }
            for (int v : row) {
                if (v < 0 || v > r * c) {
                    throw new IllegalArgumentException("clue range");
                }
            }
        }
    }

    /** True when water (true = flooded) satisfies every rule. */
    public static boolean isValid(int[][] clues, boolean[][] water) {
        checkClues(clues);
        int rows = clues.length;
        int cols = clues[0].length;
        if (water.length != rows) {
            return false;
        }
        for (boolean[] row : water) {
            if (row.length != cols) {
                return false;
            }
        }
        for (int r = 0; r + 1 < rows; r++) {
            for (int c = 0; c + 1 < cols; c++) {
                if (water[r][c] && water[r + 1][c] && water[r][c + 1] && water[r + 1][c + 1]) {
                    return false;
                }
            }
        }
        int n = rows * cols;
        int[] comp = new int[n];
        java.util.Arrays.fill(comp, -1);
        int[] queue = new int[n];
        int waterComps = 0;
        int id = 0;
        for (int s = 0; s < n; s++) {
            if (comp[s] >= 0) {
                continue;
            }
            boolean w = water[s / cols][s % cols];
            int head = 0;
            int tail = 0;
            queue[tail++] = s;
            comp[s] = id;
            int size = 0;
            int markers = 0;
            int markerVal = 0;
            while (head < tail) {
                int x = queue[head++];
                int xr = x / cols;
                int xc = x % cols;
                size++;
                if (clues[xr][xc] > 0) {
                    markers++;
                    markerVal = clues[xr][xc];
                }
                int[] nb = {xr > 0 ? x - cols : -1, xr + 1 < rows ? x + cols : -1,
                    xc > 0 ? x - 1 : -1, xc + 1 < cols ? x + 1 : -1};
                for (int y : nb) {
                    if (y >= 0 && comp[y] < 0 && water[y / cols][y % cols] == w) {
                        comp[y] = id;
                        queue[tail++] = y;
                    }
                }
            }
            id++;
            if (w) {
                if (markers > 0) {
                    return false;
                }
                waterComps++;
            } else if (markers != 1 || markerVal != size) {
                return false;
            }
        }
        return waterComps <= 1;
    }

    private static final class Search {
        final int[][] clues;
        final int rows;
        final int cols;
        final boolean[][] water;
        final long limit;
        long count;
        boolean[][] first = new boolean[0][];

        Search(int[][] clues, long limit) {
            this.clues = clues;
            this.rows = clues.length;
            this.cols = clues[0].length;
            this.water = new boolean[rows][cols];
            this.limit = limit;
        }

        void run(int cell) {
            if (count >= limit) {
                return;
            }
            if (cell == rows * cols) {
                if (isValid(clues, water)) {
                    if (count == 0) {
                        first = new boolean[rows][];
                        for (int r = 0; r < rows; r++) {
                            first[r] = water[r].clone();
                        }
                    }
                    count++;
                }
                return;
            }
            int r = cell / cols;
            int c = cell % cols;
            run(cell + 1);
            if (clues[r][c] > 0) {
                return;
            }
            water[r][c] = true;
            boolean pool = r > 0 && c > 0 && water[r - 1][c] && water[r][c - 1] && water[r - 1][c - 1];
            if (!pool) {
                run(cell + 1);
            }
            water[r][c] = false;
        }
    }

    /** Number of valid floodings, stopping at limit. */
    public static long count(int[][] clues, long limit) {
        checkClues(clues);
        Search s = new Search(clues, limit);
        s.run(0);
        return s.count;
    }

    /** First valid flooding, or an empty array when none exists. */
    public static boolean[][] solve(int[][] clues) {
        checkClues(clues);
        Search s = new Search(clues, 1);
        s.run(0);
        return s.first;
    }

    /** Quest hook: the player's flooding must satisfy the reef chart. */
    public static boolean quest(int[][] clues, boolean[][] answer) {
        return isValid(clues, answer);
    }
}