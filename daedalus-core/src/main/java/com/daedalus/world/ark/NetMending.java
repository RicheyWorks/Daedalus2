// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.HashMap;
import java.util.Map;

/**
 * G419 The Net Mending: two deckhands mend a cargo net of r x c meshes (Dots and Boxes). Each
 * turn ties one cord; tying the fourth side of a mesh claims it and gives another turn. Cords are
 * numbered with the (r + 1) * c horizontal ones first (row by row), then the r * (c + 1)
 * vertical ones. Gives meshes closed, and an exact memoised minimax margin of meshes still to win
 * for the player to move, with a best cord, for nets of at most {@link #MAX_SOLVE_EDGES} cords.
 */
public final class NetMending {

    public static final String QUEST_ID = "q_net_mending";
    public static final int MAX_SIDE = 6;
    public static final int MAX_SOLVE_EDGES = 20;

    private final int r;
    private final int c;
    private final int hCount;
    private final int[][] boxEdges;
    private final int[][] edgeBoxes;
    private final Map<Long, Integer> memo = new HashMap<>();

    /** A net of rows x cols meshes, each 1 to 6. */
    public NetMending(int rows, int cols) {
        if (rows < 1 || cols < 1 || rows > MAX_SIDE || cols > MAX_SIDE) {
            throw new IllegalArgumentException("net size out of range");
        }
        r = rows;
        c = cols;
        hCount = (r + 1) * c;
        boxEdges = new int[r * c][];
        int[] deg = new int[edges()];
        for (int i = 0; i < r; i++) {
            for (int j = 0; j < c; j++) {
                int[] e = {i * c + j, (i + 1) * c + j, hCount + i * (c + 1) + j, hCount + i * (c + 1) + j + 1};
                boxEdges[i * c + j] = e;
                for (int x : e) {
                    deg[x]++;
                }
            }
        }
        edgeBoxes = new int[edges()][];
        for (int e = 0; e < deg.length; e++) {
            edgeBoxes[e] = new int[deg[e]];
            deg[e] = 0;
        }
        for (int b = 0; b < boxEdges.length; b++) {
            for (int x : boxEdges[b]) {
                edgeBoxes[x][deg[x]++] = b;
            }
        }
    }

    /** Number of cords. */
    public int edges() {
        return 2 * r * c + r + c;
    }

    private void check(boolean[] tied) {
        if (tied == null || tied.length != edges()) {
            throw new IllegalArgumentException("need one flag per cord");
        }
    }

    /** Meshes with all four cords tied. */
    public int closed(boolean[] tied) {
        check(tied);
        int n = 0;
        for (int[] e : boxEdges) {
            if (tied[e[0]] && tied[e[1]] && tied[e[2]] && tied[e[3]]) {
                n++;
            }
        }
        return n;
    }

    /** Meshes that tying the untied cord e would close (0, 1 or 2). */
    public int closes(boolean[] tied, int e) {
        check(tied);
        if (e < 0 || e >= tied.length || tied[e]) {
            throw new IllegalArgumentException("cord must exist and be untied");
        }
        int n = 0;
        for (int b : edgeBoxes[e]) {
            int have = 0;
            for (int x : boxEdges[b]) {
                have += tied[x] ? 1 : 0;
            }
            n += have == 3 ? 1 : 0;
        }
        return n;
    }

    private long mask(boolean[] tied) {
        check(tied);
        if (tied.length > MAX_SOLVE_EDGES) {
            throw new IllegalArgumentException("solver limited to " + MAX_SOLVE_EDGES + " cords");
        }
        long m = 0;
        for (int i = 0; i < tied.length; i++) {
            if (tied[i]) {
                m |= 1L << i;
            }
        }
        return m;
    }

    /** Meshes still to be won by the player to move minus those won by the other, perfect play. */
    public int margin(boolean[] tied) {
        return solve(mask(tied));
    }

    private int gain(long m, int e) {
        int n = 0;
        for (int b : edgeBoxes[e]) {
            int have = 0;
            for (int x : boxEdges[b]) {
                have += (m >> x & 1) != 0 ? 1 : 0;
            }
            n += have == 3 ? 1 : 0;
        }
        return n;
    }

    private int solve(long m) {
        int n = edges();
        if (m == (1L << n) - 1) {
            return 0;
        }
        Integer hit = memo.get(m);
        if (hit != null) {
            return hit;
        }
        int best = Integer.MIN_VALUE;
        for (int e = 0; e < n; e++) {
            if ((m >> e & 1) == 0) {
                int k = gain(m, e);
                long nm = m | 1L << e;
                int v = k > 0 ? k + solve(nm) : -solve(nm);
                best = Math.max(best, v);
            }
        }
        memo.put(m, best);
        return best;
    }

    /** Lowest cord keeping the perfect-play margin, or -1 when every cord is tied. */
    public int bestCord(boolean[] tied) {
        long m = mask(tied);
        int want = solve(m);
        for (int e = 0; e < tied.length; e++) {
            if (!tied[e]) {
                int k = gain(m, e);
                long nm = m | 1L << e;
                if ((k > 0 ? k + solve(nm) : -solve(nm)) == want) {
                    return e;
                }
            }
        }
        return -1;
    }

    /** Quest q_net_mending: the bosun names the first player's perfect-play margin on an empty 2 x 2 net. */
    public static boolean quest(int answer) {
        NetMending n = new NetMending(2, 2);
        return n.margin(new boolean[n.edges()]) == answer;
    }
}