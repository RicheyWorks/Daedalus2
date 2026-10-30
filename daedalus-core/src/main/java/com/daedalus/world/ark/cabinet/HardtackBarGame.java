// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.HardtackBar;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Cabinet adapter for G414 The Hardtack Bar (Chomp); bites and the solver live in {@link HardtackBar}. */
public final class HardtackBarGame implements ArkCabinetGame {

    private final HardtackBar solver = new HardtackBar();
    private int[] shape;
    private int mover = 1;
    private int loser;

    /** A 4 x 5 bar. */
    public HardtackBarGame() {
        this(4, 5);
    }

    /** A rows x cols bar. */
    public HardtackBarGame(int rows, int cols) {
        this.shape = HardtackBar.bar(rows, cols);
    }

    @Override
    public String id() {
        return "hardtack";
    }

    @Override
    public String title() {
        return "The Hardtack Bar";
    }

    @Override
    public String rules() {
        return "Type row,col (1,1 is the soaked corner). A bite eats that square and all below-right. Eat 1,1 and lose.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int r = 0; r < shape.length; r++) {
                for (int c = 0; c < shape[r]; c++) {
                    out.add((r + 1) + "," + (c + 1));
                }
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        int[] rc = CabinetMoves.pair(move);
        int r = rc[0] - 1;
        int c = rc[1] - 1;
        if (over() || r < 0 || r >= shape.length || c < 0 || c >= shape[r]) {
            return false;
        }
        shape = HardtackBar.bite(shape, r, c);
        if (r == 0 && c == 0) {
            loser = mover;
        }
        mover = 3 - mover;
        return true;
    }

    @Override
    public int toMove() {
        return over() ? 0 : mover;
    }

    @Override
    public boolean over() {
        return loser != 0;
    }

    @Override
    public int winner() {
        return loser == 0 ? 0 : 3 - loser;
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r < shape.length && shape[r] > 0; r++) {
            for (int c = 0; c < shape[r]; c++) {
                sb.append(r == 0 && c == 0 ? '*' : '#');
            }
            sb.append('\n');
        }
        return sb.length() == 0 ? "(the bar is eaten)\n" : sb.toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        int[] b = solver.winningBite(shape);
        if (b.length == 2) {
            return (b[0] + 1) + "," + (b[1] + 1);
        }
        for (int r = shape.length - 1; r >= 0; r--) {
            if (shape[r] > 0 && (r > 0 || shape[r] > 1)) {
                return (r + 1) + "," + shape[r];
            }
        }
        return "1,1";
    }
}
