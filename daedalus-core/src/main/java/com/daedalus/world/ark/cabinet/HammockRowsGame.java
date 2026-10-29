// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.HammockRows;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Cabinet adapter for G416 The Hammock Rows (Connect Four style); rules live in {@link HammockRows}. */
public final class HammockRowsGame implements ArkCabinetGame {

    private final HammockRows rack;
    private final int w;
    private final int h;
    private int[] cells;
    private int mover = 1;

    /** A 4 x 4 rack, three in a line (small enough for the exact solver). */
    public HammockRowsGame() {
        this(4, 4, 3);
    }

    /** A w x h rack with line length k. */
    public HammockRowsGame(int w, int h, int k) {
        this.rack = new HammockRows(w, h, k);
        this.w = w;
        this.h = h;
        this.cells = new int[w * h];
    }

    @Override
    public String id() {
        return "hammock";
    }

    @Override
    public String title() {
        return "The Hammock Rows";
    }

    @Override
    public String rules() {
        return "Type a column number (1 is left). Hammocks drop to the lowest free row; first full line wins.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int c = 0; c < w; c++) {
                if (rack.height(cells, c) >= 0) {
                    out.add(Integer.toString(c + 1));
                }
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        int c = CabinetMoves.number(move) - 1;
        if (over() || c < 0 || c >= w || rack.height(cells, c) < 0) {
            return false;
        }
        cells = rack.drop(cells, c, mover);
        mover = 3 - mover;
        return true;
    }

    @Override
    public int toMove() {
        return over() ? 0 : mover;
    }

    @Override
    public boolean over() {
        if (rack.winner(cells) != 0) {
            return true;
        }
        for (int c = 0; c < w; c++) {
            if (rack.height(cells, c) >= 0) {
                return false;
            }
        }
        return true;
    }

    @Override
    public int winner() {
        return rack.winner(cells);
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int r = h - 1; r >= 0; r--) {
            for (int c = 0; c < w; c++) {
                int v = cells[c * h + r];
                sb.append(v == 1 ? 'X' : v == 2 ? 'O' : '.');
            }
            sb.append('\n');
        }
        for (int c = 0; c < w; c++) {
            sb.append((c + 1) % 10);
        }
        return sb.append('\n').toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        if (cells.length <= HammockRows.MAX_SOLVE) {
            return Integer.toString(rack.bestColumn(cells, mover) + 1);
        }
        for (int who : new int[] {mover, 3 - mover}) {
            for (int c = 0; c < w; c++) {
                if (rack.height(cells, c) >= 0 && rack.winner(rack.drop(cells, c, who)) == who) {
                    return Integer.toString(c + 1);
                }
            }
        }
        return legalMoves().get(0);
    }
}
