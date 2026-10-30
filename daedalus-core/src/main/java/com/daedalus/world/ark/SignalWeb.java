// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.HashMap;
import java.util.Map;

/**
 * G413 The Signal Web: two signal crews play Hex on an n x n rhombus of lamp posts. Crew 1 tries
 * to join the top row to the bottom row, crew 2 the left column to the right column; each post
 * has six neighbours. Gives the winner of a board by union-find, and an exact minimax solver with
 * a winning post for boards of at most {@link #MAX_SOLVE} cells. Cells are row-major, 0 = empty.
 */
public final class SignalWeb {

    public static final String QUEST_ID = "q_signal_web";
    public static final int MAX_SIDE = 11;
    public static final int MAX_SOLVE = 9;
    private static final int[] DR = {0, 0, -1, 1, -1, 1};
    private static final int[] DC = {-1, 1, 0, 0, 1, -1};

    private SignalWeb() { }

    private static void check(int n, int[] cells) {
        if (n < 1 || n > MAX_SIDE || cells == null || cells.length != n * n) {
            throw new IllegalArgumentException("board must be n x n with 1 <= n <= " + MAX_SIDE);
        }
        for (int v : cells) {
            if (v < 0 || v > 2) {
                throw new IllegalArgumentException("cell values are 0, 1 or 2");
            }
        }
    }

    private static int find(int[] p, int a) {
        int r = a;
        while (p[r] != r) {
            r = p[r];
        }
        int x = a;
        while (p[x] != r) {
            int nx = p[x];
            p[x] = r;
            x = nx;
        }
        return r;
    }

    private static void union(int[] p, int a, int b) {
        p[find(p, a)] = find(p, b);
    }

    private static boolean joined(int n, int[] cells, int who) {
        int size = n * n;
        int[] p = new int[size + 2];
        for (int i = 0; i < p.length; i++) {
            p[i] = i;
        }
        for (int r = 0; r < n; r++) {
            for (int c = 0; c < n; c++) {
                int i = r * n + c;
                if (cells[i] != who) {
                    continue;
                }
                int edge = who == 1 ? r : c;
                if (edge == 0) {
                    union(p, i, size);
                }
                if (edge == n - 1) {
                    union(p, i, size + 1);
                }
                for (int k = 0; k < 6; k++) {
                    int rr = r + DR[k];
                    int cc = c + DC[k];
                    if (rr >= 0 && cc >= 0 && rr < n && cc < n && cells[rr * n + cc] == who) {
                        union(p, i, rr * n + cc);
                    }
                }
            }
        }
        return find(p, size) == find(p, size + 1);
    }

    /** 1 or 2 for the crew whose chain is complete, 0 when neither (both cannot happen in play). */
    public static int winner(int n, int[] cells) {
        check(n, cells);
        if (joined(n, cells, 1)) {
            return 1;
        }
        return joined(n, cells, 2) ? 2 : 0;
    }

    /** True when the crew to move wins with perfect play from this board. */
    public static boolean wins(int n, int[] cells, int toMove) {
        return winningPost(n, cells, toMove) >= 0;
    }

    /** A post that wins for the crew to move, or -1 when every post loses. */
    public static int winningPost(int n, int[] cells, int toMove) {
        check(n, cells);
        if (cells.length > MAX_SOLVE) {
            throw new IllegalArgumentException("solver limited to " + MAX_SOLVE + " cells");
        }
        if (toMove != 1 && toMove != 2) {
            throw new IllegalArgumentException("crew must be 1 or 2");
        }
        if (winner(n, cells) != 0) {
            return -1;
        }
        int[] b = cells.clone();
        Map<Long, Boolean> memo = new HashMap<>();
        for (int i = 0; i < b.length; i++) {
            if (b[i] == 0) {
                b[i] = toMove;
                boolean ok = winner(n, b) == toMove || !solve(n, b, 3 - toMove, memo);
                b[i] = 0;
                if (ok) {
                    return i;
                }
            }
        }
        return -1;
    }

    private static boolean solve(int n, int[] b, int who, Map<Long, Boolean> memo) {
        long key = who;
        for (int v : b) {
            key = key * 3 + v;
        }
        Boolean c = memo.get(key);
        if (c != null) {
            return c;
        }
        boolean win = false;
        for (int i = 0; i < b.length && !win; i++) {
            if (b[i] == 0) {
                b[i] = who;
                win = winner(n, b) == who || !solve(n, b, 3 - who, memo);
                b[i] = 0;
            }
        }
        memo.put(key, win);
        return win;
    }

    /** Quest q_signal_web: the lookout names which crew's signal chain is complete. */
    public static boolean quest(int n, int[] cells, int answer) {
        return winner(n, cells) == answer;
    }
}