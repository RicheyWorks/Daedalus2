// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * G426 The Hold Blocks: rectangular cargo blocks (1x1 up to 3x3) fill a w x h hold, Klotski
 * style. A move slides one block one cell left, right, up or down into free floor. Block 0 is the
 * lead and must reach its goal cell (the top-left of the block). A layout lists {x, y} for each
 * block's top-left cell, flattened as x0, y0, x1, y1 and so on. Directions: 0 right, 1 left,
 * 2 down, 3 up. Gives legal moves, the fewest moves by breadth-first search and one plan.
 */
public final class HoldBlocks {

    public static final String QUEST_ID = "q_hold_blocks";
    public static final int MAX_SIDE = 6;
    public static final int MAX_BLOCKS = 10;
    public static final int MAX_STATES = 300_000;
    private static final int[] DX = {1, -1, 0, 0};
    private static final int[] DY = {0, 0, 1, -1};

    private final int w;
    private final int h;
    private final int[] bw;
    private final int[] bh;
    private final int gx;
    private final int gy;

    /** Hold w x h (2 to 6), block sizes (1 to 3 each way) and the lead block's goal cell. */
    public HoldBlocks(int w, int h, int[] bw, int[] bh, int gx, int gy) {
        if (w < 2 || h < 2 || w > MAX_SIDE || h > MAX_SIDE || bw == null || bh == null
                || bw.length < 1 || bw.length > MAX_BLOCKS || bh.length != bw.length) {
            throw new IllegalArgumentException("bad hold");
        }
        for (int i = 0; i < bw.length; i++) {
            if (bw[i] < 1 || bw[i] > 3 || bh[i] < 1 || bh[i] > 3) {
                throw new IllegalArgumentException("block sizes are 1 to 3");
            }
        }
        if (gx < 0 || gy < 0 || gx + bw[0] > w || gy + bh[0] > h) {
            throw new IllegalArgumentException("goal must fit the lead block");
        }
        this.w = w;
        this.h = h;
        this.bw = bw.clone();
        this.bh = bh.clone();
        this.gx = gx;
        this.gy = gy;
    }

    private int[] grid(int[] pos) {
        if (pos == null || pos.length != 2 * bw.length) {
            return new int[0];
        }
        int[] g = new int[w * h];
        for (int i = 0; i < bw.length; i++) {
            int x = pos[2 * i];
            int y = pos[2 * i + 1];
            if (x < 0 || y < 0 || x + bw[i] > w || y + bh[i] > h) {
                return new int[0];
            }
            for (int a = 0; a < bw[i]; a++) {
                for (int b = 0; b < bh[i]; b++) {
                    int cell = (y + b) * w + x + a;
                    if (g[cell] != 0) {
                        return new int[0];
                    }
                    g[cell] = i + 1;
                }
            }
        }
        return g;
    }

    /** True when every block lies in the hold without overlaps. */
    public boolean fits(int[] pos) {
        return grid(pos).length != 0;
    }

    private int[] need(int[] pos) {
        int[] g = grid(pos);
        if (g.length == 0) {
            throw new IllegalArgumentException("blocks overlap or leave the hold");
        }
        return g;
    }

    /** True when the lead block sits on its goal. */
    public boolean solved(int[] pos) {
        need(pos);
        return pos[0] == gx && pos[1] == gy;
    }

    /** Every legal move as {block, direction}. */
    public List<int[]> moves(int[] pos) {
        int[] g = need(pos);
        List<int[]> out = new ArrayList<>();
        for (int i = 0; i < bw.length; i++) {
            for (int d = 0; d < 4; d++) {
                int nx = pos[2 * i] + DX[d];
                int ny = pos[2 * i + 1] + DY[d];
                if (nx < 0 || ny < 0 || nx + bw[i] > w || ny + bh[i] > h) {
                    continue;
                }
                boolean free = true;
                for (int a = 0; a < bw[i] && free; a++) {
                    for (int b = 0; b < bh[i] && free; b++) {
                        int v = g[(ny + b) * w + nx + a];
                        free = v == 0 || v == i + 1;
                    }
                }
                if (free) {
                    out.add(new int[] {i, d});
                }
            }
        }
        return List.copyOf(out);
    }

    /** The layout after one move (the move must be legal). */
    public int[] apply(int[] pos, int[] move) {
        boolean ok = false;
        for (int[] mv : moves(pos)) {
            ok |= move != null && move.length == 2 && mv[0] == move[0] && mv[1] == move[1];
        }
        if (!ok) {
            throw new IllegalArgumentException("illegal move");
        }
        int[] out = pos.clone();
        out[2 * move[0]] += DX[move[1]];
        out[2 * move[0] + 1] += DY[move[1]];
        return out;
    }

    private static long key(int[] pos) {
        long k = 0;
        for (int p : pos) {
            k = k << 3 | p;
        }
        return k;
    }

    /** One shortest plan of {block, direction} moves; empty when solved or unsolvable. */
    public int[][] plan(int[] start) {
        need(start);
        Map<Long, long[]> prev = new HashMap<>();
        ArrayDeque<int[]> q = new ArrayDeque<>();
        prev.put(key(start), new long[] {-1, -1, -1});
        q.add(start.clone());
        long goal = -1;
        while (!q.isEmpty()) {
            int[] cur = q.poll();
            long ck = key(cur);
            if (cur[0] == gx && cur[1] == gy) {
                goal = ck;
                break;
            }
            for (int[] mv : moves(cur)) {
                int[] nx = cur.clone();
                nx[2 * mv[0]] += DX[mv[1]];
                nx[2 * mv[0] + 1] += DY[mv[1]];
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

    /** Fewest moves, 0 when solved, -1 when the goal cannot be reached. */
    public int fewest(int[] start) {
        if (solved(start)) {
            return 0;
        }
        int[][] p = plan(start);
        return p.length == 0 ? -1 : p.length;
    }

    /** True when every move is legal in turn and the plan ends solved. */
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
            cur = apply(cur, mv);
        }
        return solved(cur);
    }

    /** Quest q_hold_blocks: the quartermaster names the fewest moves for this layout. */
    public boolean quest(int[] start, int answer) {
        return fewest(start) == answer;
    }
}