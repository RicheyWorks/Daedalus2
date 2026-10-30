// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G409 The Deck Crawler: a deck crab walks a square deck of painted planks. On a plank of colour c
 * it turns by rule letter c (R = right, L = left), repaints the plank to colour c + 1 (mod the
 * rule length) and steps forward. Rule "RL" is Langton's ant; longer strings are multi-colour
 * turmites. Steps can be undone exactly. The crab starts at the deck centre facing north on an
 * all-zero deck. Walking off the deck throws IllegalStateException.
 */
public final class DeckCrawler {

    public static final String QUEST_ID = "q_deck_crawler";
    public static final int MAX_SIDE = 4096;
    private static final int[] DX = {0, 1, 0, -1};
    private static final int[] DY = {-1, 0, 1, 0};

    private final boolean[] right;
    private final int side;
    private final byte[] deck;
    private int x;
    private int y;
    private int dir;
    private long steps;

    /** New crab on a side x side deck with an L/R rule of 2 to 16 letters. */
    public DeckCrawler(String rule, int side) {
        if (rule == null || rule.length() < 2 || rule.length() > 16 || !rule.matches("[LR]+")) {
            throw new IllegalArgumentException("rule must be 2-16 letters of L/R");
        }
        if (side < 3 || side > MAX_SIDE) {
            throw new IllegalArgumentException("side out of range: " + side);
        }
        right = new boolean[rule.length()];
        for (int i = 0; i < right.length; i++) {
            right[i] = rule.charAt(i) == 'R';
        }
        this.side = side;
        deck = new byte[side * side];
        x = side / 2;
        y = side / 2;
    }

    /** One step forward. */
    public void step() {
        int i = y * side + x;
        int c = deck[i];
        dir = (dir + (right[c] ? 1 : 3)) & 3;
        deck[i] = (byte) ((c + 1) % right.length);
        int nx = x + DX[dir];
        int ny = y + DY[dir];
        if (nx < 0 || ny < 0 || nx >= side || ny >= side) {
            throw new IllegalStateException("crab left the deck at step " + steps);
        }
        x = nx;
        y = ny;
        steps++;
    }

    /** Many steps forward. */
    public void run(long n) {
        for (long k = 0; k < n; k++) {
            step();
        }
    }

    /** Exactly undoes the last step. */
    public void back() {
        if (steps == 0) {
            throw new IllegalStateException("nothing to undo");
        }
        x -= DX[dir];
        y -= DY[dir];
        int i = y * side + x;
        int c = (deck[i] + right.length - 1) % right.length;
        deck[i] = (byte) c;
        dir = (dir + (right[c] ? 3 : 1)) & 3;
        steps--;
    }

    public int x() {
        return x;
    }

    public int y() {
        return y;
    }

    /** 0 north, 1 east, 2 south, 3 west. */
    public int dir() {
        return dir;
    }

    public long steps() {
        return steps;
    }

    /** Colour of the plank at (px, py). */
    public int colour(int px, int py) {
        return deck[py * side + px];
    }

    /** Planks not of colour 0. */
    public int painted() {
        int n = 0;
        for (byte b : deck) {
            if (b != 0) {
                n++;
            }
        }
        return n;
    }

    /** True when every plank is colour 0. */
    public boolean clean() {
        return painted() == 0;
    }

    /** Copy of the deck colours, row-major. */
    public byte[] snapshot() {
        return Arrays.copyOf(deck, deck.length);
    }

    /** Langton's ant: painted planks after n steps on a deck large enough for it. */
    public static int langtonPainted(int n, int side) {
        DeckCrawler c = new DeckCrawler("RL", side);
        c.run(n);
        return c.painted();
    }

    /** Quest q_deck_crawler: the bosun names how many planks Langton's crab has painted. */
    public static boolean quest(int n, int answer) {
        return langtonPainted(n, 257) == answer;
    }
}