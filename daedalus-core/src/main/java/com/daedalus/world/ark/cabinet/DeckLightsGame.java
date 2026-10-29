// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.DeckLights;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Solo cabinet adapter for G396 The Deck Lights (Akari / Light Up); every rule check and the solver live in
 * {@link DeckLights}. A move toggles a lamp on an open cell. The game is won the moment
 * {@link DeckLights#isValid} accepts the lamp board. The hint toggles the first cell that differs from the piece's
 * solved board.
 */
public final class DeckLightsGame implements ArkCabinetGame {

    private static final int O = DeckLights.OPEN;
    private static final int W = DeckLights.WALL;

    private final int[][] grid;
    private final int[][] solution;
    private final int[][] lamps;
    private int toggles;

    /** The cabinet's 5x5 deck with two numbered and two plain walls. */
    public DeckLightsGame() {
        this(new int[][] {{O, O, O, O, O}, {O, 1, O, W, O}, {O, O, O, O, O}, {O, W, O, 2, O}, {O, O, O, O, O}});
    }

    /** A deck grid (cells OPEN, WALL or 0..4, up to 7x7) that has at least one solution. */
    public DeckLightsGame(int[][] deck) {
        this.grid = new int[deck.length][];
        for (int r = 0; r < deck.length; r++) {
            grid[r] = deck[r].clone();
        }
        this.solution = DeckLights.solve(grid);
        if (solution.length == 0) {
            throw new IllegalArgumentException("deck has no solution");
        }
        this.lamps = new int[grid.length][grid[0].length];
    }

    @Override
    public String id() {
        return "lights";
    }

    @Override
    public String title() {
        return "The Deck Lights";
    }

    @Override
    public String rules() {
        return "Type row,col (1-based) to hang or take down a lamp on an open cell. Light every open cell, no lamp may "
            + "see another, and each numbered wall needs exactly that many lamps beside it.";
    }

    @Override
    public List<String> legalMoves() {
        List<String> out = new ArrayList<>();
        if (!over()) {
            for (int r = 0; r < grid.length; r++) {
                for (int c = 0; c < grid[0].length; c++) {
                    if (grid[r][c] == O) {
                        out.add((r + 1) + "," + (c + 1));
                    }
                }
            }
        }
        return Collections.unmodifiableList(out);
    }

    @Override
    public boolean play(String move) {
        if (move == null || over()) {
            return false;
        }
        String[] p = move.trim().replace(" ", "").split(",");
        if (p.length != 2) {
            return false;
        }
        int r;
        int c;
        try {
            r = Integer.parseInt(p[0]) - 1;
            c = Integer.parseInt(p[1]) - 1;
        } catch (NumberFormatException e) {
            return false;
        }
        if (r < 0 || c < 0 || r >= grid.length || c >= grid[0].length || grid[r][c] != O) {
            return false;
        }
        lamps[r][c] = 1 - lamps[r][c];
        toggles++;
        return true;
    }

    /** Lamps hanging now. */
    public int lampCount() {
        int n = 0;
        for (int[] row : lamps) {
            for (int v : row) {
                n += v;
            }
        }
        return n;
    }

    /** A copy of the lamp board, 1 for a lamp. */
    public int[][] lampBoard() {
        int[][] out = new int[lamps.length][];
        for (int r = 0; r < lamps.length; r++) {
            out[r] = lamps[r].clone();
        }
        return out;
    }

    /** Lamp toggles played so far. */
    public int toggles() {
        return toggles;
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        return DeckLights.isValid(grid, lamps);
    }

    @Override
    public int winner() {
        return over() ? 1 : 0;
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r < grid.length; r++) {
            for (int c = 0; c < grid[0].length; c++) {
                int v = grid[r][c];
                char ch;
                if (v == O) {
                    ch = lamps[r][c] == 1 ? '*' : '.';
                } else if (v == W) {
                    ch = '#';
                } else {
                    ch = (char) ('0' + v);
                }
                sb.append(ch).append(' ');
            }
            sb.append('\n');
        }
        return sb.append(over() ? "deck lit!" : "lamps " + lampCount()).append('\n').toString();
    }

    @Override
    public String hint() {
        if (over()) {
            return "";
        }
        for (int r = 0; r < grid.length; r++) {
            for (int c = 0; c < grid[0].length; c++) {
                if (grid[r][c] == O && lamps[r][c] != solution[r][c]) {
                    return (r + 1) + "," + (c + 1);
                }
            }
        }
        return legalMoves().get(0);
    }
}
