// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.SeedTrays;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/** Cabinet adapter for G418 The Seed Trays (Kalah); sowing, captures and the solver live in {@link SeedTrays}. */
public final class SeedTraysGame implements ArkCabinetGame {

    private final SeedTrays solver = new SeedTrays();
    private final int p;
    private int[] board;
    private int side;

    /** Three trays a side with three seeds each (exactly solvable). */
    public SeedTraysGame() {
        this(3, 3);
    }

    /** p trays a side with s seeds each. */
    public SeedTraysGame(int p, int s) {
        this.p = p;
        this.board = SeedTrays.start(p, s);
    }

    @Override
    public String id() {
        return "seeds";
    }

    @Override
    public String title() {
        return "The Seed Trays";
    }

    @Override
    public String rules() {
        return "Type one of your tray numbers (1 is your leftmost). Land in your store to go again; most seeds wins.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int i = 0; i < p; i++) {
                if (board[side * (p + 1) + i] > 0) {
                    out.add(Integer.toString(i + 1));
                }
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        int i = CabinetMoves.number(move) - 1;
        if (over() || i < 0 || i >= p || board[side * (p + 1) + i] == 0) {
            return false;
        }
        int[] r = SeedTrays.sow(board, side, i);
        side = r[r.length - 1];
        board = Arrays.copyOf(r, r.length - 1);
        return true;
    }

    @Override
    public int toMove() {
        return over() ? 0 : side + 1;
    }

    @Override
    public boolean over() {
        return SeedTrays.over(board);
    }

    @Override
    public int winner() {
        if (!over()) {
            return 0;
        }
        int a = board[p];
        int b = board[2 * p + 1];
        return a > b ? 1 : b > a ? 2 : 0;
    }

    /** Seeds in a player's store (player 1 or 2). */
    public int store(int player) {
        return board[player == 1 ? p : 2 * p + 1];
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder("   ");
        for (int i = 2 * p; i > p; i--) {
            sb.append(String.format("%3d", board[i]));
        }
        sb.append('\n').append(String.format("%3d", board[2 * p + 1]));
        sb.append(" ".repeat(3 * p)).append(String.format("%3d", board[p])).append("\n   ");
        for (int i = 0; i < p; i++) {
            sb.append(String.format("%3d", board[i]));
        }
        return sb.append('\n').toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        return Integer.toString(solver.bestPit(board, side) + 1);
    }
}
