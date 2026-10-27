// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.ChalkGrid;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Cabinet adapter for G421 The Chalk Grid (normal noughts and crosses, k in a row); rules live in {@link ChalkGrid}. */
public final class ChalkGridGame implements ArkCabinetGame {

    private final ChalkGrid grid;
    private final int rows;
    private final int cols;
    private final int[] cells;
    private int mover = 1;

    /** Classic 3 x 3, three in a row. */
    public ChalkGridGame() {
        this(3, 3, 3);
    }

    /** A rows x cols grid with line length k (normal play). */
    public ChalkGridGame(int rows, int cols, int k) {
        this.grid = new ChalkGrid(rows, cols, k, false);
        this.rows = rows;
        this.cols = cols;
        this.cells = new int[rows * cols];
    }

    @Override
    public String id() {
        return "chalk";
    }

    @Override
    public String title() {
        return "The Chalk Grid";
    }

    @Override
    public String rules() {
        return "Type a square number (1 is top-left, read across). First watch with a full line wins.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int i = 0; i < cells.length; i++) {
                if (cells[i] == 0) {
                    out.add(Integer.toString(i + 1));
                }
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        int i = CabinetMoves.number(move) - 1;
        if (over() || i < 0 || i >= cells.length || cells[i] != 0) {
            return false;
        }
        cells[i] = mover;
        mover = 3 - mover;
        return true;
    }

    @Override
    public int toMove() {
        return over() ? 0 : mover;
    }

    @Override
    public boolean over() {
        if (grid.lineOwner(cells) != 0) {
            return true;
        }
        for (int c : cells) {
            if (c == 0) {
                return false;
            }
        }
        return true;
    }

    @Override
    public int winner() {
        return grid.lineOwner(cells);
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int v = cells[r * cols + c];
                sb.append(v == 1 ? 'X' : v == 2 ? 'O' : '.');
            }
            sb.append('\n');
        }
        return sb.toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        if (cells.length <= ChalkGrid.MAX_SOLVE) {
            return Integer.toString(grid.bestSquare(cells, mover) + 1);
        }
        return legalMoves().get(0);
    }
}
