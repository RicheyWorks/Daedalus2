// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G381 The Loop Lines: the rope-walker lays one closed rope along the deck seams of an R x C
 * cell grid (R, C 1..4) so that each numbered cell has exactly that many rope sides, the rope
 * never branches or crosses, and it forms a single loop (Slitherlink). Clue -1 means no clue.
 * Edges: horizontal (r 0..R, c 0..C-1) at r*C+c, then vertical (r 0..R-1, c 0..C) at
 * H + r*(C+1)+c where H = (R+1)*C.
 */
public final class LoopLines {

    public static final String QUEST_ID = "q_loop_lines";

    private LoopLines() { }

    private static final class Board {
        final int rows;
        final int cols;
        final int edges;
        final int[] clue;
        final int[][] edgeVerts;
        final int[][] edgeCells;
        final int[] vertLast;
        final int[] cellLast;

        Board(int[][] clues) {
            rows = clues.length;
            if (rows < 1 || rows > 4) {
                throw new IllegalArgumentException("rows 1..4");
            }
            cols = clues[0].length;
            if (cols < 1 || cols > 4) {
                throw new IllegalArgumentException("cols 1..4");
            }
            clue = new int[rows * cols];
            for (int r = 0; r < rows; r++) {
                if (clues[r].length != cols) {
                    throw new IllegalArgumentException("ragged");
                }
                for (int c = 0; c < cols; c++) {
                    int k = clues[r][c];
                    if (k < -1 || k > 3) {
                        throw new IllegalArgumentException("clue -1..3");
                    }
                    clue[r * cols + c] = k;
                }
            }
            int h = (rows + 1) * cols;
            edges = h + rows * (cols + 1);
            edgeVerts = new int[edges][];
            edgeCells = new int[edges][];
            int vw = cols + 1;
            for (int r = 0; r <= rows; r++) {
                for (int c = 0; c < cols; c++) {
                    int e = r * cols + c;
                    edgeVerts[e] = new int[] {r * vw + c, r * vw + c + 1};
                    edgeCells[e] = cellsOf(r - 1, c, r, c);
                }
            }
            for (int r = 0; r < rows; r++) {
                for (int c = 0; c <= cols; c++) {
                    int e = h + r * vw + c;
                    edgeVerts[e] = new int[] {r * vw + c, (r + 1) * vw + c};
                    edgeCells[e] = cellsOf(r, c - 1, r, c);
                }
            }
            vertLast = new int[(rows + 1) * vw];
            cellLast = new int[rows * cols];
            for (int e = 0; e < edges; e++) {
                for (int v : edgeVerts[e]) {
                    vertLast[v] = e;
                }
                for (int x : edgeCells[e]) {
                    cellLast[x] = e;
                }
            }
        }

        private int[] cellsOf(int r1, int c1, int r2, int c2) {
            boolean a = r1 >= 0 && r1 < rows && c1 >= 0 && c1 < cols;
            boolean b = r2 >= 0 && r2 < rows && c2 >= 0 && c2 < cols;
            if (a && b) {
                return new int[] {r1 * cols + c1, r2 * cols + c2};
            }
            if (a) {
                return new int[] {r1 * cols + c1};
            }
            return b ? new int[] {r2 * cols + c2} : new int[0];
        }

        boolean singleLoop(boolean[] on) {
            int nv = vertLast.length;
            int[] deg = new int[nv];
            int used = 0;
            int start = -1;
            for (int e = 0; e < edges; e++) {
                if (on[e]) {
                    used++;
                    deg[edgeVerts[e][0]]++;
                    deg[edgeVerts[e][1]]++;
                    start = edgeVerts[e][0];
                }
            }
            if (used == 0) {
                return false;
            }
            for (int d : deg) {
                if (d != 0 && d != 2) {
                    return false;
                }
            }
            boolean[] seenE = new boolean[edges];
            int prevV = -1;
            int v = start;
            int walked = 0;
            do {
                int next = -1;
                for (int e = 0; e < edges && next < 0; e++) {
                    if (on[e] && !seenE[e] && (edgeVerts[e][0] == v || edgeVerts[e][1] == v)) {
                        seenE[e] = true;
                        next = edgeVerts[e][0] == v ? edgeVerts[e][1] : edgeVerts[e][0];
                    }
                }
                if (next < 0) {
                    break;
                }
                prevV = v;
                v = next;
                walked++;
            } while (v != start);
            return prevV >= 0 && v == start && walked == used;
        }

        boolean cluesMet(boolean[] on) {
            int[] cnt = new int[clue.length];
            for (int e = 0; e < edges; e++) {
                if (on[e]) {
                    for (int x : edgeCells[e]) {
                        cnt[x]++;
                    }
                }
            }
            for (int i = 0; i < clue.length; i++) {
                if (clue[i] >= 0 && cnt[i] != clue[i]) {
                    return false;
                }
            }
            return true;
        }
    }

    /** True when the edge set is one loop meeting every clue. */
    public static boolean isValid(int[][] clues, boolean[] edgesOn) {
        Board b = new Board(clues);
        return edgesOn.length == b.edges && b.cluesMet(edgesOn) && b.singleLoop(edgesOn);
    }

    /** Total edge count for an R x C board. */
    public static int edgeCount(int rows, int cols) {
        return (rows + 1) * cols + rows * (cols + 1);
    }

    private static final class Search {
        final Board b;
        final boolean[] on;
        final int[] deg;
        final int[] cnt;
        final long limit;
        long count;
        boolean[] first = new boolean[0];

        Search(Board b, long limit) {
            this.b = b;
            this.on = new boolean[b.edges];
            this.deg = new int[b.vertLast.length];
            this.cnt = new int[b.clue.length];
            this.limit = limit;
        }

        boolean ok(int e) {
            for (int v : b.edgeVerts[e]) {
                if (deg[v] > 2 || b.vertLast[v] == e && deg[v] == 1) {
                    return false;
                }
            }
            for (int x : b.edgeCells[e]) {
                int k = b.clue[x];
                if (k >= 0 && (cnt[x] > k || b.cellLast[x] == e && cnt[x] != k)) {
                    return false;
                }
            }
            return true;
        }

        void apply(int e, int d) {
            for (int v : b.edgeVerts[e]) {
                deg[v] += d;
            }
            for (int x : b.edgeCells[e]) {
                cnt[x] += d;
            }
        }

        void run(int e) {
            if (count >= limit) {
                return;
            }
            if (e == b.edges) {
                if (b.singleLoop(on)) {
                    if (count == 0) {
                        first = on.clone();
                    }
                    count++;
                }
                return;
            }
            if (ok(e)) {
                run(e + 1);
            }
            on[e] = true;
            apply(e, 1);
            if (ok(e)) {
                run(e + 1);
            }
            apply(e, -1);
            on[e] = false;
        }
    }

    /** Number of valid loops, stopping at limit. */
    public static long count(int[][] clues, long limit) {
        Search s = new Search(new Board(clues), limit);
        s.run(0);
        return s.count;
    }

    /** First valid loop as an edge mask, or an empty array when none exists. */
    public static boolean[] solve(int[][] clues) {
        Search s = new Search(new Board(clues), 1);
        s.run(0);
        return s.first.clone();
    }

    /** Quest hook: the player's rope must be a valid loop for the clues. */
    public static boolean quest(int[][] clues, boolean[] answer) {
        return isValid(clues, answer);
    }
}