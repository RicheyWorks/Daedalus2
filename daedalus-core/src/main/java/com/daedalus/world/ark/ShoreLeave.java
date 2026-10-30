// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G405 The Shore Leave: the bosun marks which deck cells stay roped off on a board up to 5x5
 * split into rooms (Heyawake). Roped (shaded) cells never share an edge; open cells form one
 * connected area with at least one cell; a room with a clue has exactly that many roped cells; and
 * no straight row or column run of open cells crosses two room borders. Rooms are labels 0..k-1
 * per cell; clues are one per room, -1 for none. Boards use 1 for roped and 0 for open.
 */
public final class ShoreLeave {

    public static final String QUEST_ID = "q_shore_leave";

    private ShoreLeave() { }

    private static int roomCount(int[][] rooms, int[] clues) {
        int h = rooms.length;
        if (h < 1 || h > 5) {
            throw new IllegalArgumentException("rows 1..5");
        }
        int w = rooms[0].length;
        if (w < 1 || w > 5) {
            throw new IllegalArgumentException("cols 1..5");
        }
        int k = clues.length;
        for (int[] row : rooms) {
            if (row.length != w) {
                throw new IllegalArgumentException("rectangular");
            }
            for (int v : row) {
                if (v < 0 || v >= k) {
                    throw new IllegalArgumentException("room label 0..clues-1");
                }
            }
        }
        for (int v : clues) {
            if (v < -1 || v > h * w) {
                throw new IllegalArgumentException("clue -1..cells");
            }
        }
        return k;
    }

    private static boolean runsOk(int[][] rooms, int[][] b, boolean horizontal) {
        int h = rooms.length;
        int w = rooms[0].length;
        int outer = horizontal ? h : w;
        int inner = horizontal ? w : h;
        for (int i = 0; i < outer; i++) {
            int borders = 0;
            for (int j = 0; j < inner; j++) {
                int r = horizontal ? i : j;
                int c = horizontal ? j : i;
                if (b[r][c] == 1) {
                    borders = 0;
                } else if (j > 0) {
                    int pr = horizontal ? r : r - 1;
                    int pc = horizontal ? c - 1 : c;
                    if (b[pr][pc] == 0 && rooms[pr][pc] != rooms[r][c]) {
                        borders++;
                        if (borders >= 2) {
                            return false;
                        }
                    }
                }
            }
        }
        return true;
    }

    /** True when the shading meets every rule on the rooms and clues. */
    public static boolean isValid(int[][] rooms, int[] clues, int[][] board) {
        int k = roomCount(rooms, clues);
        int h = rooms.length;
        int w = rooms[0].length;
        if (board.length != h) {
            return false;
        }
        int[] shaded = new int[k];
        int open = 0;
        int start = -1;
        for (int r = 0; r < h; r++) {
            if (board[r].length != w) {
                return false;
            }
            for (int c = 0; c < w; c++) {
                int v = board[r][c];
                if (v != 0 && v != 1) {
                    return false;
                }
                if (v == 1) {
                    shaded[rooms[r][c]]++;
                    if (r > 0 && board[r - 1][c] == 1 || c > 0 && board[r][c - 1] == 1) {
                        return false;
                    }
                } else {
                    open++;
                    start = r * w + c;
                }
            }
        }
        for (int i = 0; i < k; i++) {
            if (clues[i] >= 0 && shaded[i] != clues[i]) {
                return false;
            }
        }
        if (open == 0 || !runsOk(rooms, board, true) || !runsOk(rooms, board, false)) {
            return false;
        }
        boolean[] seen = new boolean[h * w];
        int[] stack = new int[h * w];
        int top = 0;
        int reached = 0;
        stack[top++] = start;
        seen[start] = true;
        int[] dr = {-1, 1, 0, 0};
        int[] dc = {0, 0, -1, 1};
        while (top > 0) {
            int x = stack[--top];
            reached++;
            for (int d = 0; d < 4; d++) {
                int rr = x / w + dr[d];
                int cc = x % w + dc[d];
                if (rr >= 0 && rr < h && cc >= 0 && cc < w && board[rr][cc] == 0
                    && !seen[rr * w + cc]) {
                    seen[rr * w + cc] = true;
                    stack[top++] = rr * w + cc;
                }
            }
        }
        return reached == open;
    }

    private static final class Search {
        final int[][] rooms;
        final int[] clues;
        final int h;
        final int w;
        final int[][] b;
        final int[] shaded;
        final long limit;
        long count;
        int[][] first = new int[0][];

        Search(int[][] rooms, int[] clues, long limit) {
            this.rooms = rooms;
            this.clues = clues;
            this.h = rooms.length;
            this.w = rooms[0].length;
            this.b = new int[h][w];
            this.shaded = new int[clues.length];
            this.limit = limit;
        }

        void run(int cell) {
            if (count >= limit) {
                return;
            }
            if (cell == h * w) {
                if (isValid(rooms, clues, b)) {
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
            int g = rooms[r][c];
            if ((r == 0 || b[r - 1][c] == 0) && (c == 0 || b[r][c - 1] == 0)
                && (clues[g] < 0 || shaded[g] < clues[g])) {
                b[r][c] = 1;
                shaded[g]++;
                run(cell + 1);
                shaded[g]--;
                b[r][c] = 0;
            }
            run(cell + 1);
        }
    }

    /** Number of valid shadings, stopping at limit. */
    public static long count(int[][] rooms, int[] clues, long limit) {
        roomCount(rooms, clues);
        Search s = new Search(rooms, clues, limit);
        s.run(0);
        return s.count;
    }

    /** First valid shading, or an empty array when none exists. */
    public static int[][] solve(int[][] rooms, int[] clues) {
        roomCount(rooms, clues);
        Search s = new Search(rooms, clues, 1);
        s.run(0);
        return s.first;
    }

    /** Quest hook: the player's shading must meet every rule. */
    public static boolean quest(int[][] rooms, int[] clues, int[][] answer) {
        return isValid(rooms, clues, answer);
    }
}