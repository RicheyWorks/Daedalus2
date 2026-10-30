// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.SkittleRow;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Cabinet adapter for G411 The Skittle Row at Kayles; the Grundy solver lives in {@link SkittleRow}. */
public final class SkittleRowGame implements ArkCabinetGame {

    /** Most skittles the cabinet seats across all rows. */
    public static final int MAX_SKITTLES = 40;

    private final List<Integer> rows = new ArrayList<>();
    private int mover = 1;
    private int lastBowler;

    /** Rows of 3, 5 and 7 skittles. */
    public SkittleRowGame() {
        this(3, 5, 7);
    }

    /** Rows of the given lengths (1 or more each, {@link #MAX_SKITTLES} in total at most). */
    public SkittleRowGame(int... lengths) {
        int total = 0;
        for (int n : lengths) {
            if (n < 1) {
                throw new IllegalArgumentException("rows need at least one skittle");
            }
            total += n;
            rows.add(n);
        }
        if (rows.isEmpty() || total > MAX_SKITTLES) {
            throw new IllegalArgumentException("1 to " + MAX_SKITTLES + " skittles");
        }
    }

    @Override
    public String id() {
        return "skittles";
    }

    @Override
    public String title() {
        return "The Skittle Row";
    }

    @Override
    public String rules() {
        return "Type row,spot,count: knock 1 or 2 side-by-side skittles from that spot (spots count from 1). "
            + "Knock the last skittle to win.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        for (int r = 0; r < rows.size(); r++) {
            int len = rows.get(r);
            for (int k = 1; k <= 2; k++) {
                for (int s = 1; s + k - 1 <= len; s++) {
                    out.add((r + 1) + "," + s + "," + k);
                }
            }
        }
        return Collections.unmodifiableList(out);
    }

    private static int[] triple(String move) {
        if (move == null) {
            return new int[] {-1, -1, -1};
        }
        String[] p = move.trim().split("\\s*,\\s*");
        if (p.length != 3) {
            return new int[] {-1, -1, -1};
        }
        return new int[] {CabinetMoves.number(p[0]), CabinetMoves.number(p[1]), CabinetMoves.number(p[2])};
    }

    @Override
    public boolean play(String move) {
        int[] t = triple(move);
        int r = t[0] - 1;
        int s = t[1] - 1;
        int k = t[2];
        if (r < 0 || r >= rows.size() || s < 0 || k < 1 || k > 2 || s + k > rows.get(r)) {
            return false;
        }
        int len = rows.remove(r);
        int right = len - s - k;
        if (right > 0) {
            rows.add(r, right);
        }
        if (s > 0) {
            rows.add(r, s);
        }
        lastBowler = mover;
        mover = 3 - mover;
        return true;
    }

    /** Row lengths now, unmodifiable. */
    public List<Integer> rows() {
        return Collections.unmodifiableList(new ArrayList<>(rows));
    }

    private int[] lengths() {
        return rows.stream().mapToInt(Integer::intValue).toArray();
    }

    /** True when the player to move wins with best play. */
    public boolean moverWins() {
        return !over() && SkittleRow.nimSum(SkittleRow.KAYLES, lengths()) != 0;
    }

    @Override
    public int toMove() {
        return over() ? 0 : mover;
    }

    @Override
    public boolean over() {
        return rows.isEmpty();
    }

    @Override
    public int winner() {
        return over() ? lastBowler : 0;
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r < rows.size(); r++) {
            sb.append(r + 1).append(": ").append("i".repeat(rows.get(r))).append('\n');
        }
        sb.append(over() ? "player " + winner() + " knocked the last skittle" : "player " + mover + " to bowl");
        return sb.append('\n').toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        int[] w = SkittleRow.winningMove(SkittleRow.KAYLES, lengths());
        if (w.length == 0) {
            return "1,1,1";
        }
        return (w[0] + 1) + "," + (w[2] + 1) + "," + w[1];
    }
}