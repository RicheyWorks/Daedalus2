// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.PegBoard;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Solo cabinet adapter for G366 The Peg Board (triangular peg solitaire); jumps and the one-peg solver live in
 * {@link PegBoard}. The hint follows the solver's line while the player stays on it, and otherwise offers the first
 * legal jump. The game ends when no jump is left; it is won with exactly one peg standing.
 */
public final class PegBoardGame implements ArkCabinetGame {

    private final int side;
    private final int[][] jumps;
    private final int[][] line;
    private int board;
    private int played;
    private boolean onLine = true;

    /** The classic 15-hole board (side 5) with the top hole empty. */
    public PegBoardGame() {
        this(5, 0);
    }

    /** A board of side 2..5 with the given hole (0-based, row by row) empty. */
    public PegBoardGame(int side, int hole) {
        this.jumps = PegBoard.jumps(side);
        this.line = PegBoard.solve(side, hole);
        this.side = side;
        int holes = side * (side + 1) / 2;
        this.board = ((1 << holes) - 1) & ~(1 << hole);
    }

    @Override
    public String id() {
        return "pegs";
    }

    @Override
    public String title() {
        return "The Peg Board";
    }

    @Override
    public String rules() {
        return "Type from,to (holes 1..n, row by row): jump a peg over a neighbour into an empty hole. "
            + "Finish with one peg left to win.";
    }

    private boolean legal(int[] j) {
        return (board >> j[0] & 1) == 1 && (board >> j[1] & 1) == 1 && (board >> j[2] & 1) == 0;
    }

    private static String token(int[] j) {
        return (j[0] + 1) + "," + (j[2] + 1);
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        for (int[] j : jumps) {
            if (legal(j)) {
                out.add(token(j));
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        if (move == null) {
            return false;
        }
        for (int[] j : jumps) {
            if (legal(j) && token(j).equals(move.trim().replace(" ", ""))) {
                if (onLine && (played >= line.length || line[played][0] != j[0] || line[played][2] != j[2])) {
                    onLine = false;
                }
                board = board & ~(1 << j[0]) & ~(1 << j[1]) | (1 << j[2]);
                played++;
                return true;
            }
        }
        return false;
    }

    /** Pegs still standing. */
    public int pegs() {
        return Integer.bitCount(board);
    }

    /** True while every move so far follows the solver's one-peg line. */
    public boolean onSolverLine() {
        return onLine && line.length > 0;
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        return legalMoves().isEmpty();
    }

    @Override
    public int winner() {
        return over() && pegs() == 1 ? 1 : 0;
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        int i = 0;
        for (int r = 0; r < side; r++) {
            sb.append(" ".repeat(side - r - 1));
            for (int c = 0; c <= r; c++, i++) {
                sb.append((board >> i & 1) == 1 ? 'o' : '.').append(' ');
            }
            sb.append('\n');
        }
        String tail = "pegs " + pegs();
        if (over()) {
            tail = pegs() == 1 ? "one peg left - cleared!" : "stuck with " + pegs() + " pegs";
        }
        return sb.append(tail).append('\n').toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        if (onSolverLine() && played < line.length) {
            return token(line[played]);
        }
        return legalMoves().get(0);
    }
}