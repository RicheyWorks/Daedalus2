// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G396 The Deck Lights: the lamplighter hangs lamps on the open deck cells of a board up to 7x7
 * (Akari / Light Up). A lamp lights its row and column until a wall. No lamp may light another
 * lamp, every open cell must be lit, and a numbered wall 0..4 needs exactly that many lamps on its
 * four sides. Grid cells: {@link #OPEN}, {@link #WALL} or a wall number 0..4. Lamp boards use 1 for
 * a lamp and 0 for none.
 */
public final class DeckLights {

    public static final String QUEST_ID = "q_deck_lights";
    public static final int OPEN = -2;
    public static final int WALL = -1;

    private static final int[] DR = {-1, 1, 0, 0};
    private static final int[] DC = {0, 0, -1, 1};

    private DeckLights() { }

    private static void checkGrid(int[][] grid) {
        int h = grid.length;
        if (h < 1 || h > 7) {
            throw new IllegalArgumentException("rows 1..7");
        }
        int w = grid[0].length;
        if (w < 1 || w > 7) {
            throw new IllegalArgumentException("cols 1..7");
        }
        for (int[] row : grid) {
            if (row.length != w) {
                throw new IllegalArgumentException("rectangular");
            }
            for (int v : row) {
                if (v < OPEN || v > 4) {
                    throw new IllegalArgumentException("cell OPEN, WALL or 0..4");
                }
            }
        }
    }

    private static boolean inside(int[][] g, int r, int c) {
        return r >= 0 && r < g.length && c >= 0 && c < g[0].length;
    }

    /** True when the lamp board meets every rule on the grid. */
    public static boolean isValid(int[][] grid, int[][] lamps) {
        checkGrid(grid);
        int h = grid.length;
        int w = grid[0].length;
        if (lamps.length != h) {
            return false;
        }
        for (int r = 0; r < h; r++) {
            if (lamps[r].length != w) {
                return false;
            }
            for (int c = 0; c < w; c++) {
                int v = lamps[r][c];
                if (v != 0 && v != 1 || v == 1 && grid[r][c] != OPEN) {
                    return false;
                }
            }
        }
        for (int r = 0; r < h; r++) {
            for (int c = 0; c < w; c++) {
                if (grid[r][c] == OPEN) {
                    int seen = lamps[r][c];
                    for (int k = 0; k < 4; k++) {
                        int rr = r + DR[k];
                        int cc = c + DC[k];
                        while (inside(grid, rr, cc) && grid[rr][cc] == OPEN) {
                            seen += lamps[rr][cc];
                            rr += DR[k];
                            cc += DC[k];
                        }
                    }
                    if (seen == 0 || lamps[r][c] == 1 && seen > 1) {
                        return false;
                    }
                } else if (grid[r][c] >= 0) {
                    int around = 0;
                    for (int k = 0; k < 4; k++) {
                        int rr = r + DR[k];
                        int cc = c + DC[k];
                        if (inside(grid, rr, cc)) {
                            around += lamps[rr][cc];
                        }
                    }
                    if (around != grid[r][c]) {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    private static final class Search {
        final int[][] grid;
        final int h;
        final int w;
        final int[][] b;
        final long limit;
        long count;
        int[][] first = new int[0][];

        Search(int[][] grid, long limit) {
            this.grid = grid;
            this.h = grid.length;
            this.w = grid[0].length;
            this.b = new int[h][w];
            this.limit = limit;
        }

        boolean canPlace(int r, int c) {
            for (int k = 0; k < 4; k++) {
                int rr = r + DR[k];
                int cc = c + DC[k];
                while (inside(grid, rr, cc) && grid[rr][cc] == OPEN) {
                    if (b[rr][cc] == 1) {
                        return false;
                    }
                    rr += DR[k];
                    cc += DC[k];
                }
            }
            for (int k = 0; k < 4; k++) {
                int rr = r + DR[k];
                int cc = c + DC[k];
                if (inside(grid, rr, cc) && grid[rr][cc] >= 0) {
                    int around = 0;
                    for (int j = 0; j < 4; j++) {
                        int r2 = rr + DR[j];
                        int c2 = cc + DC[j];
                        if (inside(grid, r2, c2)) {
                            around += b[r2][c2];
                        }
                    }
                    if (around >= grid[rr][cc]) {
                        return false;
                    }
                }
            }
            return true;
        }

        void run(int cell) {
            if (count >= limit) {
                return;
            }
            if (cell == h * w) {
                if (isValid(grid, b)) {
                    if (count == 0) {
                        first = new int[h][];
                        for (int r = 0; r < h; r++) {
                            first[r] = b[r].clone();
                        }
                    }
                    count++;
                }
                return;
            }
            int r = cell / w;
            int c = cell % w;
            if (grid[r][c] == OPEN && canPlace(r, c)) {
                b[r][c] = 1;
                run(cell + 1);
                b[r][c] = 0;
            }
            run(cell + 1);
        }
    }

    /** Number of valid lamp boards, stopping at limit. */
    public static long count(int[][] grid, long limit) {
        checkGrid(grid);
        Search s = new Search(grid, limit);
        s.run(0);
        return s.count;
    }

    /** First valid lamp board, or an empty array when none exists. */
    public static int[][] solve(int[][] grid) {
        checkGrid(grid);
        Search s = new Search(grid, 1);
        s.run(0);
        return s.first;
    }

    /** Quest hook: the player's lamp board must meet every rule. */
    public static boolean quest(int[][] grid, int[][] answer) {
        return isValid(grid, answer);
    }
}