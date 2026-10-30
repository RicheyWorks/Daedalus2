// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.TwoHoards;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Cabinet adapter for G354 The Two Hoards (Wythoff's game); rules and the solver live in {@link TwoHoards}. */
public final class TwoHoardsGame implements ArkCabinetGame {

    /** Largest hoard the cabinet seats, so the move list stays short enough to show. */
    public static final int MAX_HOARD = 30;

    private int x;
    private int y;
    private int mover = 1;
    private int lastTaker;

    /** Hoards of 5 and 9 coins. */
    public TwoHoardsGame() {
        this(5, 9);
    }

    /** Hoards of x and y coins, each 0 to {@link #MAX_HOARD}. */
    public TwoHoardsGame(int x, int y) {
        if (x < 0 || y < 0 || x > MAX_HOARD || y > MAX_HOARD) {
            throw new IllegalArgumentException("hoards 0.." + MAX_HOARD);
        }
        this.x = x;
        this.y = y;
    }

    @Override
    public String id() {
        return "hoards";
    }

    @Override
    public String title() {
        return "The Two Hoards";
    }

    @Override
    public String rules() {
        return "Type hoard,count: 1,k or 2,k takes k from one hoard, 3,k takes k from both. Take the last coin to win.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int k = 1; k <= x; k++) {
                out.add("1," + k);
            }
            for (int k = 1; k <= y; k++) {
                out.add("2," + k);
            }
            for (int k = 1; k <= Math.min(x, y); k++) {
                out.add("3," + k);
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        int[] hk = CabinetMoves.pair(move);
        int h = hk[0];
        int k = hk[1];
        int nx = h == 2 ? x : x - k;
        int ny = h == 1 ? y : y - k;
        if (over() || h < 1 || h > 3 || k < 1 || nx < 0 || ny < 0 || !TwoHoards.isLegal(x, y, nx, ny)) {
            return false;
        }
        x = nx;
        y = ny;
        lastTaker = mover;
        mover = 3 - mover;
        return true;
    }

    /** Coins in hoard 1. */
    public int first() {
        return x;
    }

    /** Coins in hoard 2. */
    public int second() {
        return y;
    }

    @Override
    public int toMove() {
        return over() ? 0 : mover;
    }

    @Override
    public boolean over() {
        return x == 0 && y == 0;
    }

    @Override
    public int winner() {
        return over() ? lastTaker : 0;
    }

    @Override
    public String render() {
        return "hoard 1: " + "o".repeat(x) + " (" + x + ")\nhoard 2: " + "o".repeat(y) + " (" + y + ")\n"
            + (over() ? "player " + winner() + " took the last coin" : "player " + mover + " to take") + '\n';
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        long[] w = TwoHoards.winningMove(x, y);
        if (w.length == 0) {
            return x > 0 ? "1,1" : "2,1";
        }
        long dx = x - w[0];
        long dy = y - w[1];
        if (dx > 0 && dy > 0) {
            return "3," + dx;
        }
        return dx > 0 ? "1," + dx : "2," + dy;
    }
}