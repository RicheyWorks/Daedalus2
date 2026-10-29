// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G389 The Cable Pairs: the rigger joins each pair of matching sockets on an R x C panel (sides
 * 1..4) with a cable of cells, cables never share a cell, and every cell is used (Numberlink,
 * full-fill rule). Sockets are labels 1..K (K at most 4), each appearing exactly twice; 0 is a
 * blank cell. A filled panel is valid when each socket has one same-label neighbour, every other
 * cell has two, and each label's cells are connected, so each label forms one simple path.
 */
public final class CablePairs {

    public static final String QUEST_ID = "q_cable_pairs";

    private CablePairs() { }

    private static int checkSockets(int[][] sockets) {
        int rows = sockets.length;
        if (rows < 1 || rows > 4) {
            throw new IllegalArgumentException("rows 1..4");
        }
        int cols = sockets[0].length;
        if (cols < 1 || cols > 4) {
            throw new IllegalArgumentException("cols 1..4");
        }
        int[] seen = new int[5];
        int k = 0;
        for (int[] row : sockets) {
            if (row.length != cols) {
                throw new IllegalArgumentException("ragged");
            }
            for (int v : row) {
                if (v < 0 || v > 4) {
                    throw new IllegalArgumentException("label 0..4");
                }
                seen[v]++;
                k = Math.max(k, v);
            }
        }
        for (int i = 1; i <= k; i++) {
            if (seen[i] != 2) {
                throw new IllegalArgumentException("label " + i + " must appear twice");
            }
        }
        return k;
    }

    private static int sameNeighbours(int[][] g, int r, int c) {
        int rows = g.length;
        int cols = g[0].length;
        int v = g[r][c];
        int n = 0;
        if (r > 0 && g[r - 1][c] == v) {
            n++;
        }
        if (r + 1 < rows && g[r + 1][c] == v) {
            n++;
        }
        if (c > 0 && g[r][c - 1] == v) {
            n++;
        }
        if (c + 1 < cols && g[r][c + 1] == v) {
            n++;
        }
        return n;
    }

    private static boolean cellOk(int[][] sockets, int[][] g, int r, int c) {
        int need = sockets[r][c] > 0 ? 1 : 2;
        return sameNeighbours(g, r, c) == need;
    }

    /** True when the filled panel joins every pair under the rules. */
    public static boolean isValid(int[][] sockets, int[][] filled) {
        int k = checkSockets(sockets);
        int rows = sockets.length;
        int cols = sockets[0].length;
        if (filled.length != rows) {
            return false;
        }
        for (int r = 0; r < rows; r++) {
            if (filled[r].length != cols) {
                return false;
            }
            for (int c = 0; c < cols; c++) {
                int v = filled[r][c];
                if (v < 1 || v > k || sockets[r][c] > 0 && sockets[r][c] != v) {
                    return false;
                }
            }
        }
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (!cellOk(sockets, filled, r, c)) {
                    return false;
                }
            }
        }
        boolean[] seen = new boolean[rows * cols];
        int[] stack = new int[rows * cols];
        for (int label = 1; label <= k; label++) {
            int start = -1;
            int total = 0;
            for (int i = 0; i < rows * cols; i++) {
                if (filled[i / cols][i % cols] == label) {
                    total++;
                    start = i;
                }
            }
            int top = 0;
            int reached = 0;
            stack[top++] = start;
            seen[start] = true;
            while (top > 0) {
                int x = stack[--top];
                reached++;
                int xr = x / cols;
                int xc = x % cols;
                int[] nb = {xr > 0 ? x - cols : -1, xr + 1 < rows ? x + cols : -1,
                    xc > 0 ? x - 1 : -1, xc + 1 < cols ? x + 1 : -1};
                for (int y : nb) {
                    if (y >= 0 && !seen[y] && filled[y / cols][y % cols] == label) {
                        seen[y] = true;
                        stack[top++] = y;
                    }
                }
            }
            if (reached != total) {
                return false;
            }
        }
        return true;
    }

    private static final class Search {
        final int[][] sockets;
        final int[][] g;
        final int rows;
        final int cols;
        final int k;
        final long limit;
        long count;
        int[][] first = new int[0][];

        Search(int[][] sockets, int k, long limit) {
            this.sockets = sockets;
            this.rows = sockets.length;
            this.cols = sockets[0].length;
            this.g = new int[rows][cols];
            this.k = k;
            this.limit = limit;
        }

        void run(int cell) {
            if (count >= limit) {
                return;
            }
            if (cell == rows * cols) {
                if (isValid(sockets, g)) {
                    if (count == 0) {
                        first = new int[rows][];
                        for (int r = 0; r < rows; r++) {
                            first[r] = g[r].clone();
                        }
                    }
                    count++;
                }
                return;
            }
            int r = cell / cols;
            int c = cell % cols;
            int lo = sockets[r][c] > 0 ? sockets[r][c] : 1;
            int hi = sockets[r][c] > 0 ? sockets[r][c] : k;
            for (int v = lo; v <= hi; v++) {
                g[r][c] = v;
                if (r > 0 && !cellOk(sockets, g, r - 1, c)) {
                    continue;
                }
                if (r == rows - 1 && c > 0 && !cellOk(sockets, g, r, c - 1)) {
                    continue;
                }
                run(cell + 1);
            }
            g[r][c] = 0;
        }
    }

    /** Number of valid fillings, stopping at limit. */
    public static long count(int[][] sockets, long limit) {
        int k = checkSockets(sockets);
        if (k == 0) {
            return 0;
        }
        Search s = new Search(sockets, k, limit);
        s.run(0);
        return s.count;
    }

    /** First valid filling, or an empty array when none exists. */
    public static int[][] solve(int[][] sockets) {
        int k = checkSockets(sockets);
        if (k == 0) {
            return new int[0][];
        }
        Search s = new Search(sockets, k, 1);
        s.run(0);
        return s.first;
    }

    /** Quest hook: the player's filled panel must join every pair. */
    public static boolean quest(int[][] sockets, int[][] answer) {
        return checkSockets(sockets) > 0 && isValid(sockets, answer);
    }
}