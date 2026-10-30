// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.NetMending;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Cabinet adapter for G419 The Net Mending (Dots and Boxes); closing and the solver live in {@link NetMending}. */
public final class NetMendingGame implements ArkCabinetGame {

    private final NetMending net;
    private final int rows;
    private final int cols;
    private final boolean[] tied;
    private final int[] score = new int[3];
    private int mover = 1;

    /** A 2 x 2 net (12 cords, exactly solvable). */
    public NetMendingGame() {
        this(2, 2);
    }

    /** A rows x cols net of meshes. */
    public NetMendingGame(int rows, int cols) {
        this.net = new NetMending(rows, cols);
        this.rows = rows;
        this.cols = cols;
        this.tied = new boolean[net.edges()];
    }

    @Override
    public String id() {
        return "net";
    }

    @Override
    public String title() {
        return "The Net Mending";
    }

    @Override
    public String rules() {
        return "Type a cord number (shown on the net). Tie the fourth side of a mesh to claim it and go again.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        for (int e = 0; e < tied.length; e++) {
            if (!tied[e]) {
                out.add(Integer.toString(e + 1));
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        int e = CabinetMoves.number(move) - 1;
        if (e < 0 || e >= tied.length || tied[e]) {
            return false;
        }
        int won = net.closes(tied, e);
        tied[e] = true;
        score[mover] += won;
        if (won == 0) {
            mover = 3 - mover;
        }
        return true;
    }

    @Override
    public int toMove() {
        return over() ? 0 : mover;
    }

    @Override
    public boolean over() {
        return net.closed(tied) == rows * cols;
    }

    /** Meshes claimed by a player (1 or 2). */
    public int meshes(int player) {
        return score[player];
    }

    @Override
    public int winner() {
        if (!over()) {
            return 0;
        }
        return score[1] > score[2] ? 1 : score[2] > score[1] ? 2 : 0;
    }

    @Override
    public String render() {
        int h = (rows + 1) * cols;
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r <= rows; r++) {
            sb.append('+');
            for (int c = 0; c < cols; c++) {
                int e = r * cols + c;
                sb.append(tied[e] ? "---" : String.format("%3d", e + 1)).append('+');
            }
            sb.append('\n');
            if (r < rows) {
                for (int c = 0; c <= cols; c++) {
                    int e = h + r * (cols + 1) + c;
                    sb.append(tied[e] ? "|" : Integer.toString((e + 1) % 10));
                    if (c < cols) {
                        sb.append("   ");
                    }
                }
                sb.append('\n');
            }
        }
        return sb.append("X ").append(score[1]).append(" - O ").append(score[2]).append('\n').toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        if (tied.length <= NetMending.MAX_SOLVE_EDGES) {
            return Integer.toString(net.bestCord(tied) + 1);
        }
        return legalMoves().get(0);
    }
}
