// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * G422 The Cargo Shuffle: crates 2 or 3 cells long sit on an n x n hold floor and slide only
 * along their own length (Rush Hour style). Crate 0 is horizontal and must reach the right-hand
 * hatch, that is its end touches column n - 1. A move slides one crate any distance. A layout is
 * the crates' positions: the start column of a horizontal crate or the start row of a vertical
 * one. Gives legal moves, fewest moves by breadth-first search and one shortest plan.
 */
public final class CargoShuffle {

    public static final String QUEST_ID = "q_cargo_shuffle";
    public static final int MAX_SIDE = 8;
    public static final int MAX_CRATES = 16;
    public static final int MAX_STATES = 200_000;

    private final int n;
    private final boolean[] across;
    private final int[] len;
    private final int[] lane;

    /** Hold of side n (4 to 8); per crate: horizontal flag, length 2 or 3, and its row or column. */
    public CargoShuffle(int n, boolean[] across, int[] len, int[] lane) {
        if (n < 4 || n > MAX_SIDE || across == null || len == null || lane == null) {
            throw new IllegalArgumentException("bad hold");
        }
        int k = across.length;
        if (k < 1 || k > MAX_CRATES || len.length != k || lane.length != k || !across[0]) {
            throw new IllegalArgumentException("need 1-16 crates, crate 0 horizontal");
        }
        for (int i = 0; i < k; i++) {
            if ((len[i] != 2 && len[i] != 3) || lane[i] < 0 || lane[i] >= n) {
                throw new IllegalArgumentException("bad crate " + i);
            }
        }
        this.n = n;
        this.across = across.clone();
        this.len = len.clone();
        this.lane = lane.clone();
    }

    /** True when the positions fit the hold without overlaps. */
    public boolean fits(int[] pos) {
        return grid(pos).length != 0;
    }

    private int[] grid(int[] pos) {
        if (pos == null || pos.length != len.length) {
            return new int[0];
        }
        int[] g = new int[n * n];
        for (int i = 0; i < pos.length; i++) {
            if (pos[i] < 0 || pos[i] + len[i] > n) {
                return new int[0];
            }
            for (int j = 0; j < len[i]; j++) {
                int cell = across[i] ? lane[i] * n + pos[i] + j : (pos[i] + j) * n + lane[i];
                if (g[cell] != 0) {
                    return new int[0];
                }
                g[cell] = i + 1;
            }
        }
        return g;
    }

    private int[] need(int[] pos) {
        int[] g = grid(pos);
        if (g.length == 0) {
            throw new IllegalArgumentException("crates overlap or leave the hold");
        }
        return g;
    }

    /** True when crate 0 touches the hatch. */
    public boolean solved(int[] pos) {
        need(pos);
        return pos[0] + len[0] == n;
    }

    /** Every legal move as {crate, new position}. */
    public List<int[]> moves(int[] pos) {
        int[] g = need(pos);
        List<int[]> out = new ArrayList<>();
        for (int i = 0; i < pos.length; i++) {
            for (int step = -1; step <= 1; step += 2) {
                int p = pos[i];
                while (true) {
                    int np = p + step;
                    int head = step < 0 ? np : np + len[i] - 1;
                    if (np < 0 || head >= n) {
                        break;
                    }
                    int cell = across[i] ? lane[i] * n + head : head * n + lane[i];
                    if (g[cell] != 0) {
                        break;
                    }
                    p = np;
                    out.add(new int[] {i, p});
                }
            }
        }
        return List.copyOf(out);
    }

    private static long key(int[] pos) {
        long k = 0;
        for (int p : pos) {
            k = k << 3 | p;
        }
        return k;
    }

    /** One shortest plan of {crate, new position} moves; empty when solved or unsolvable. */
    public int[][] plan(int[] start) {
        need(start);
        Map<Long, long[]> prev = new HashMap<>();
        ArrayDeque<int[]> q = new ArrayDeque<>();
        long s0 = key(start);
        prev.put(s0, new long[] {-1, -1, -1});
        q.add(start.clone());
        long goal = -1;
        while (!q.isEmpty() && goal < 0) {
            int[] cur = q.poll();
            long ck = key(cur);
            if (cur[0] + len[0] == n) {
                goal = ck;
                break;
            }
            for (int[] mv : moves(cur)) {
                int[] nx = cur.clone();
                nx[mv[0]] = mv[1];
                long nk = key(nx);
                if (!prev.containsKey(nk)) {
                    if (prev.size() >= MAX_STATES) {
                        throw new IllegalStateException("search passed " + MAX_STATES + " states");
                    }
                    prev.put(nk, new long[] {ck, mv[0], mv[1]});
                    q.add(nx);
                }
            }
        }
        if (goal < 0) {
            return new int[0][];
        }
        ArrayDeque<int[]> out = new ArrayDeque<>();
        for (long k = goal; prev.get(k)[0] >= 0; k = prev.get(k)[0]) {
            long[] p = prev.get(k);
            out.push(new int[] {(int) p[1], (int) p[2]});
        }
        return out.toArray(new int[0][]);
    }

    /** Fewest moves to the hatch, 0 when already there, -1 when it cannot be reached. */
    public int fewest(int[] start) {
        if (solved(start)) {
            return 0;
        }
        int[][] p = plan(start);
        return p.length == 0 ? -1 : p.length;
    }

    /** True when every move is legal from the layout reached so far and the plan ends solved. */
    public boolean valid(int[] start, int[][] plan) {
        int[] cur = start.clone();
        need(cur);
        for (int[] mv : plan) {
            boolean ok = false;
            for (int[] legal : moves(cur)) {
                ok |= mv != null && mv.length == 2 && legal[0] == mv[0] && legal[1] == mv[1];
            }
            if (!ok) {
                return false;
            }
            cur[mv[0]] = mv[1];
        }
        return solved(cur);
    }

    /** Quest q_cargo_shuffle: the quartermaster names the fewest moves for this layout. */
    public boolean quest(int[] start, int answer) {
        return fewest(start) == answer;
    }
}