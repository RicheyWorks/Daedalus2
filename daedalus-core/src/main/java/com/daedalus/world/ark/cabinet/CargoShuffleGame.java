// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.CargoShuffle;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/**
 * Cabinet adapter for G422 The Cargo Shuffle (Rush Hour style, one player); legal slides, the goal test and the
 * shortest plan live in {@link CargoShuffle}. A move is a crate letter and its new 1-based start, for example
 * {@code B4}. Solving the hold counts as a win for player 1.
 */
public final class CargoShuffleGame implements ArkCabinetGame {

    private final CargoShuffle hold;
    private final int n;
    private final boolean[] across;
    private final int[] len;
    private final int[] lane;
    private final int[] pos;
    private int moves;

    /** The cabinet's starter hold: 6 x 6, three crates, solvable in 3 moves. */
    public CargoShuffleGame() {
        this(6, new boolean[] {true, false, false}, new int[] {2, 3, 2}, new int[] {2, 2, 4}, new int[] {0, 0, 1});
    }

    /** A custom hold; see {@link CargoShuffle} for the layout format. */
    public CargoShuffleGame(int n, boolean[] across, int[] len, int[] lane, int[] start) {
        this.hold = new CargoShuffle(n, across, len, lane);
        if (!hold.fits(start)) {
            throw new IllegalArgumentException("layout does not fit");
        }
        this.n = n;
        this.across = across.clone();
        this.len = len.clone();
        this.lane = lane.clone();
        this.pos = start.clone();
    }

    @Override
    public String id() {
        return "cargo";
    }

    @Override
    public String title() {
        return "The Cargo Shuffle";
    }

    @Override
    public String rules() {
        return "Slide crates along their length: type a letter and new start, e.g. B4. Get crate A to the right hatch.";
    }

    private static String token(int crate, int start) {
        return (char) ('A' + crate) + Integer.toString(start + 1);
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int[] m : hold.moves(pos)) {
                out.add(token(m[0], m[1]));
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        if (move == null || !legalMoves().contains(move.trim().toUpperCase(Locale.ROOT))) {
            return false;
        }
        String m = move.trim().toUpperCase(Locale.ROOT);
        pos[m.charAt(0) - 'A'] = Integer.parseInt(m.substring(1)) - 1;
        moves++;
        return true;
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
        char[][] g = new char[n][n];
        for (char[] row : g) {
            Arrays.fill(row, '.');
        }
        for (int k = 0; k < pos.length; k++) {
            for (int j = 0; j < len[k]; j++) {
                int r = across[k] ? lane[k] : pos[k] + j;
                int c = across[k] ? pos[k] + j : lane[k];
                g[r][c] = (char) ('A' + k);
            }
        }
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r < n; r++) {
            sb.append(g[r]).append(r == lane[0] ? '>' : '|').append('\n');
        }
        return sb.toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        int[][] plan = hold.plan(pos);
        return plan.length == 0 ? "" : token(plan[0][0], plan[0][1]);
    }
}
