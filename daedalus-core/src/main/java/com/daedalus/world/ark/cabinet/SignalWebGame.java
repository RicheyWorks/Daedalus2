// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.SignalWeb;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Cabinet adapter for G413 The Signal Web (Hex); the chain check and solver live in {@link SignalWeb}. */
public final class SignalWebGame implements ArkCabinetGame {

    private final int n;
    private final int[] cells;
    private int mover = 1;

    /** A 3 x 3 web (exactly solvable by the cabinet). */
    public SignalWebGame() {
        this(3);
    }

    /** An n x n web. */
    public SignalWebGame(int n) {
        if (n < 1 || n > SignalWeb.MAX_SIDE) {
            throw new IllegalArgumentException("side out of range");
        }
        this.n = n;
        this.cells = new int[n * n];
    }

    @Override
    public String id() {
        return "signal";
    }

    @Override
    public String title() {
        return "The Signal Web";
    }

    @Override
    public String rules() {
        return "Type a post number (1 is top-left, read across). X joins top to bottom, O joins left to right.";
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
        return SignalWeb.winner(n, cells) != 0;
    }

    @Override
    public int winner() {
        return SignalWeb.winner(n, cells);
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r < n; r++) {
            sb.append(" ".repeat(r));
            for (int c = 0; c < n; c++) {
                int v = cells[r * n + c];
                sb.append(v == 1 ? 'X' : v == 2 ? 'O' : '.');
                if (c < n - 1) {
                    sb.append(' ');
                }
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
        if (cells.length <= SignalWeb.MAX_SOLVE) {
            int p = SignalWeb.winningPost(n, cells, mover);
            if (p >= 0) {
                return Integer.toString(p + 1);
            }
            return legalMoves().get(0);
        }
        for (int who : new int[] {mover, 3 - mover}) {
            for (int i = 0; i < cells.length; i++) {
                if (cells[i] == 0) {
                    cells[i] = who;
                    boolean chain = SignalWeb.winner(n, cells) == who;
                    cells[i] = 0;
                    if (chain) {
                        return Integer.toString(i + 1);
                    }
                }
            }
        }
        return legalMoves().get(0);
    }
}
