// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G403 The Cargo Bays: the stevedore numbers every cell of a deck up to 5x5 (Fillomino). Each
 * orthogonally connected patch of equal numbers must have exactly that many cells, so two
 * same-size bays never touch along an edge. Givens use 0 for blank; numbers run 1..rows*cols.
 */
public final class CargoBays {

    public static final String QUEST_ID = "q_cargo_bays";

    private CargoBays() { }

    private static void checkGivens(int[][] givens) {
        int h = givens.length;
        if (h < 1 || h > 5) {
            throw new IllegalArgumentException("rows 1..5");
        }
        int w = givens[0].length;
        if (w < 1 || w > 5) {
            throw new IllegalArgumentException("cols 1..5");
        }
        for (int[] row : givens) {
            if (row.length != w) {
                throw new IllegalArgumentException("rectangular");
            }
            for (int v : row) {
                if (v < 0 || v > h * w) {
                    throw new IllegalArgumentException("given 0..rows*cols");
                }
            }
        }
    }

    /**
     * Flood the patch of equal numbers at (r, c) over cells with index up to maxIndex; returns
     * size, negative when the patch still touches a cell past maxIndex.
     */
    private static int patch(int[][] b, int r, int c, int maxIndex) {
        int h = b.length;
        int w = b[0].length;
        int v = b[r][c];
        int[] stack = new int[h * w];
        boolean[] seen = new boolean[h * w];
        int top = 0;
        int size = 0;
        boolean open = false;
        stack[top++] = r * w + c;
        seen[r * w + c] = true;
        int[] dr = {-1, 1, 0, 0};
        int[] dc = {0, 0, -1, 1};
        while (top > 0) {
            int x = stack[--top];
            size++;
            for (int k = 0; k < 4; k++) {
                int rr = x / w + dr[k];
                int cc = x % w + dc[k];
                if (rr < 0 || rr >= h || cc < 0 || cc >= w) {
                    continue;
                }
                int y = rr * w + cc;
                if (y > maxIndex) {
                    open = true;
                } else if (!seen[y] && b[rr][cc] == v) {
                    seen[y] = true;
                    stack[top++] = y;
                }
            }
        }
        return open ? -size : size;
    }

    /** True when every cell is numbered, every patch has its own size, and givens hold. */
    public static boolean isValid(int[][] givens, int[][] board) {
        checkGivens(givens);
        int h = givens.length;
        int w = givens[0].length;
        if (board.length != h) {
            return false;
        }
        for (int r = 0; r < h; r++) {
            if (board[r].length != w) {
                return false;
            }
            for (int c = 0; c < w; c++) {
                int v = board[r][c];
                if (v < 1 || v > h * w || givens[r][c] != 0 && givens[r][c] != v) {
                    return false;
                }
            }
        }
        for (int r = 0; r < h; r++) {
            for (int c = 0; c < w; c++) {
                if (patch(board, r, c, h * w - 1) != board[r][c]) {
                    return false;
                }
            }
        }
        return true;
    }

    private static final class Search {
        final int[][] givens;
        final int h;
        final int w;
        final int[][] b;
        final long limit;
        long count;
        int[][] first = new int[0][];

        Search(int[][] givens, long limit) {
            this.givens = givens;
            this.h = givens.length;
            this.w = givens[0].length;
            this.b = new int[h][w];
            this.limit = limit;
        }

        boolean ok(int r, int c, int cell) {
            int[] dr = {0, -1, 0, 1, 0};
            int[] dc = {0, 0, -1, 0, 1};
            for (int k = 0; k < 5; k++) {
                int rr = r + dr[k];
                int cc = c + dc[k];
                if (rr < 0 || rr >= h || cc < 0 || cc >= w || rr * w + cc > cell) {
                    continue;
                }
                int s = patch(b, rr, cc, cell);
                int v = b[rr][cc];
                if (s > 0 && s != v || s < 0 && -s > v) {
                    return false;
                }
            }
            return true;
        }

        void run(int cell) {
            if (count >= limit) {
                return;
            }
            if (cell == h * w) {
                if (count == 0) {
                    first = new int[h][];
                    for (int r = 0; r < h; r++) {
                        first[r] = b[r].clone();
                    }
                }
                count++;
                return;
            }
            int r = cell / w;
            int c = cell % w;
            int lo = givens[r][c] == 0 ? 1 : givens[r][c];
            int hi = givens[r][c] == 0 ? h * w : givens[r][c];
            for (int v = lo; v <= hi; v++) {
                b[r][c] = v;
                if (ok(r, c, cell)) {
                    run(cell + 1);
                }
            }
            b[r][c] = 0;
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