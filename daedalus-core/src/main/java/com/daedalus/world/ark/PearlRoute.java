// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G386 The Pearl Route: the diver swims one closed route through the centres of an R x C grid
 * (sides 1..5, at most 20 cells), visiting every pearl (Masyu). White pearl (1): go straight
 * through, turning in at least one neighbouring cell on the route. Black pearl (2): turn, and
 * go straight through both neighbouring cells on the route. Edges: horizontal (r, c)-(r, c+1)
 * at r*(C-1)+c, then vertical (r, c)-(r+1, c) at H + r*C + c where H = R*(C-1).
 */
public final class PearlRoute {

    public static final String QUEST_ID = "q_pearl_route";

    private PearlRoute() { }

    private static final class Board {
        final int rows;
        final int cols;
        final int horiz;
        final int edges;
        final int[][] pearls;
        final int[][] ends;
        final int[] cellLast;

        Board(int[][] p) {
            rows = p.length;
            if (rows < 1 || rows > 5) {
                throw new IllegalArgumentException("rows 1..5");
            }
            cols = p[0].length;
            if (cols < 1 || cols > 5 || rows * cols > 20) {
                throw new IllegalArgumentException("cols 1..5, at most 20 cells");
            }
            pearls = new int[rows][];
            for (int r = 0; r < rows; r++) {
                if (p[r].length != cols) {
                    throw new IllegalArgumentException("ragged");
                }
                for (int v : p[r]) {
                    if (v < 0 || v > 2) {
                        throw new IllegalArgumentException("pearl 0..2");
                    }
                }
                pearls[r] = p[r].clone();
            }
            horiz = rows * (cols - 1);
            edges = horiz + (rows - 1) * cols;
            ends = new int[edges][];
            for (int r = 0; r < rows; r++) {
                for (int c = 0; c + 1 < cols; c++) {
                    ends[r * (cols - 1) + c] = new int[] {r * cols + c, r * cols + c + 1};
                }
            }
            for (int r = 0; r + 1 < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    ends[horiz + r * cols + c] = new int[] {r * cols + c, (r + 1) * cols + c};
                }
            }
            cellLast = new int[rows * cols];
            java.util.Arrays.fill(cellLast, -1);
            for (int e = 0; e < edges; e++) {
                cellLast[ends[e][0]] = e;
                cellLast[ends[e][1]] = e;
            }
        }

        boolean right(boolean[] on, int r, int c) {
            return r >= 0 && r < rows && c >= 0 && c + 1 < cols && on[r * (cols - 1) + c];
        }

        boolean down(boolean[] on, int r, int c) {
            return r >= 0 && r + 1 < rows && c >= 0 && c < cols && on[horiz + r * cols + c];
        }

        boolean left(boolean[] on, int r, int c) {
            return right(on, r, c - 1);
        }

        boolean up(boolean[] on, int r, int c) {
            return down(on, r - 1, c);
        }

        boolean valid(boolean[] on) {
            int n = rows * cols;
            int[] deg = new int[n];
            int used = 0;
            int start = -1;
            for (int e = 0; e < edges; e++) {
                if (on[e]) {
                    used++;
                    deg[ends[e][0]]++;
                    deg[ends[e][1]]++;
                    start = ends[e][0];
                }
            }
            if (used == 0) {
                return false;
            }
            for (int i = 0; i < n; i++) {
                if (deg[i] != 0 && deg[i] != 2 || pearls[i / cols][i % cols] > 0 && deg[i] != 2) {
                    return false;
                }
            }
            for (int r = 0; r < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    if (!pearlOk(on, r, c)) {
                        return false;
                    }
                }
            }
            boolean[] seen = new boolean[edges];
            int v = start;
            int walked = 0;
            do {
                int next = -1;
                for (int e = 0; e < edges && next < 0; e++) {
                    if (on[e] && !seen[e] && (ends[e][0] == v || ends[e][1] == v)) {
                        seen[e] = true;
                        next = ends[e][0] == v ? ends[e][1] : ends[e][0];
                    }
                }
                if (next < 0) {
                    return false;
                }
                v = next;
                walked++;
            } while (v != start);
            return walked == used;
        }

        private boolean pearlOk(boolean[] on, int r, int c) {
            int p = pearls[r][c];
            boolean h = left(on, r, c) && right(on, r, c);
            boolean vv = up(on, r, c) && down(on, r, c);
            if (p == 1) {
                if (h) {
                    return !left(on, r, c - 1) || !right(on, r, c + 1);
                }
                if (vv) {
                    return !up(on, r - 1, c) || !down(on, r + 1, c);
                }
                return false;
            }
            if (p == 2) {
                if (h || vv) {
                    return false;
                }
                return (!right(on, r, c) || right(on, r, c + 1))
                    && (!left(on, r, c) || left(on, r, c - 1))
                    && (!down(on, r, c) || down(on, r + 1, c))
                    && (!up(on, r, c) || up(on, r - 1, c));
            }
            return true;
        }
    }

    /** True when the edge set is one route satisfying every pearl. */
    public static boolean isValid(int[][] pearls, boolean[] edgesOn) {
        Board b = new Board(pearls);
        return edgesOn.length == b.edges && b.valid(edgesOn);
    }

    /** Total edge count for an R x C grid. */
    public static int edgeCount(int rows, int cols) {
        return rows * (cols - 1) + (rows - 1) * cols;
    }

    private static final class Search {
        final Board b;
        final boolean[] on;
        final int[] deg;
        final long limit;
        long count;
        boolean[] first = new boolean[0];

        Search(Board b, long limit) {
            this.b = b;
            this.on = new boolean[b.edges];
            this.deg = new int[b.rows * b.cols];
            this.limit = limit;
        }

        boolean ok(int e) {
            for (int v : b.ends[e]) {
                if (deg[v] > 2) {
                    return false;
                }
                if (b.cellLast[v] == e) {
                    boolean pearl = b.pearls[v / b.cols][v % b.cols] > 0;
                    if (deg[v] == 1 || pearl && deg[v] != 2) {
                        return false;
                    }
                }
            }
            return true;
        }

        void run(int e) {
            if (count >= limit) {
                return;
            }
            if (e == b.edges) {
                if (b.valid(on)) {
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
            deg[b.ends[e][0]]++;
            deg[b.ends[e][1]]++;
            if (ok(e)) {
                run(e + 1);
            }
            deg[b.ends[e][0]]--;
            deg[b.ends[e][1]]--;
            on[e] = false;
        }
    }

    /** Number of valid routes, stopping at limit. */
    public static long count(int[][] pearls, long limit) {
        Search s = new Search(new Board(pearls), limit);
        s.run(0);
        return s.count;
    }

    /** First valid route as an edge mask, or an empty array when none exists. */
    public static boolean[] solve(int[][] pearls) {
        Search s = new Search(new Board(pearls), 1);
        s.run(0);
        return s.first.clone();
    }

    /** Quest hook: the player's route must satisfy every pearl. */
    public static boolean quest(int[][] pearls, boolean[] answer) {
        return isValid(pearls, answer);
    }
}