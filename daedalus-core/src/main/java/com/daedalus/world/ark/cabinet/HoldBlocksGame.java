// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.HoldBlocks;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/**
 * Cabinet adapter for G426 The Hold Blocks (Klotski, one player); slides, the goal test and the shortest plan live in
 * {@link HoldBlocks}. A move is a block letter and a direction letter: R, L, D or U, for example {@code BD}.
 */
public final class HoldBlocksGame implements ArkCabinetGame {

    private static final String DIRS = "RLDU";

    private final HoldBlocks hold;
    private final int w;
    private final int h;
    private final int[] bw;
    private final int[] bh;
    private int[] pos;
    private int moves;

    /** Starter hold: 4 x 4, a 2 x 2 lead block A that must reach the bottom-right corner past three crates. */
    public HoldBlocksGame() {
        this(4, 4, new int[] {2, 1, 2, 1}, new int[] {2, 2, 1, 1}, 2, 2, new int[] {0, 0, 2, 0, 0, 2, 3, 3});
    }

    /** A custom hold; see {@link HoldBlocks} for the layout format. */
    public HoldBlocksGame(int w, int h, int[] bw, int[] bh, int gx, int gy, int[] start) {
        this.hold = new HoldBlocks(w, h, bw, bh, gx, gy);
        if (!hold.fits(start)) {
            throw new IllegalArgumentException("layout does not fit");
        }
        this.w = w;
        this.h = h;
        this.bw = bw.clone();
        this.bh = bh.clone();
        this.pos = start.clone();
    }

    @Override
    public String id() {
        return "blocks";
    }

    @Override
    public String title() {
        return "The Hold Blocks";
    }

    @Override
    public String rules() {
        return "Slide a block one cell: letter then R, L, D or U (e.g. BD). Get block A to the corner marked *.";
    }

    private static String token(int[] m) {
        return "" + (char) ('A' + m[0]) + DIRS.charAt(m[1]);
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int[] m : hold.moves(pos)) {
                out.add(token(m));
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        if (move == null || over()) {
            return false;
        }
        String t = move.trim().toUpperCase(Locale.ROOT);
        for (int[] m : hold.moves(pos)) {
            if (token(m).equals(t)) {
                pos = hold.apply(pos, m);
                moves++;
                return true;
            }
        }
        return false;
    }

    /** Slides made so far. */
    public int movesMade() {
        return moves;
    }

    /** Fewest slides still needed, from the piece's own search. */
    public int fewestLeft() {
        return hold.fewest(pos);
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        return hold.solved(pos);
    }

    @Override
    public int winner() {
        return over() ? 1 : 0;
    }

    @Override
    public String render() {
        char[][] g = new char[h][w];
        for (char[] row : g) {
            Arrays.fill(row, '.');
        }
        for (int k = 0; k < bw.length; k++) {
            for (int dy = 0; dy < bh[k]; dy++) {
                for (int dx = 0; dx < bw[k]; dx++) {
                    g[pos[2 * k + 1] + dy][pos[2 * k] + dx] = (char) ('A' + k);
                }
            }
        }
        StringBuilder sb = new StringBuilder();
        for (char[] row : g) {
            sb.append(row).append('\n');
        }
        return sb.toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        int[][] plan = hold.plan(pos);
        return plan.length == 0 ? "" : token(plan[0]);
    }
}
