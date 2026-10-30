// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/**
 * G414 The Hardtack Bar: two deckhands share a bar of hardtack whose corner square (row 0,
 * column 0) is soaked in bilge. Each bite picks a square and eats it with every square below and
 * to its right; whoever must eat the soaked square loses (Chomp). A shape is its row lengths,
 * non-increasing from row 0, at most {@link #MAX_SIDE} rows and columns. Gives win or loss for
 * the player to move by memoised search and a winning bite.
 */
public final class HardtackBar {

    public static final String QUEST_ID = "q_hardtack_bar";
    public static final int MAX_SIDE = 10;

    private final Map<Long, Boolean> memo = new HashMap<>();

    /** A fresh solver; it keeps its memo between calls. */
    public HardtackBar() {
        // memo starts empty
    }

    /** Full rectangular bar of rows x cols. */
    public static int[] bar(int rows, int cols) {
        if (rows < 1 || cols < 1 || rows > MAX_SIDE || cols > MAX_SIDE) {
            throw new IllegalArgumentException("bar size out of range");
        }
        int[] s = new int[rows];
        Arrays.fill(s, cols);
        return s;
    }

    private static void check(int[] shape) {
        if (shape == null || shape.length < 1 || shape.length > MAX_SIDE || shape[0] < 1 || shape[0] > MAX_SIDE) {
            throw new IllegalArgumentException("shape must have 1-10 rows and a non-empty first row");
        }
        for (int i = 1; i < shape.length; i++) {
            if (shape[i] < 0 || shape[i] > shape[i - 1]) {
                throw new IllegalArgumentException("row lengths must be non-increasing");
            }
        }
    }

    /** Shape after biting at (row, col); the square must be on the bar. */
    public static int[] bite(int[] shape, int row, int col) {
        check(shape);
        if (row < 0 || row >= shape.length || col < 0 || col >= shape[row]) {
            throw new IllegalArgumentException("no square there");
        }
        int[] s = shape.clone();
        for (int i = row; i < s.length; i++) {
            s[i] = Math.min(s[i], col);
        }
        return s;
    }

    private static long key(int[] s) {
        long k = 0;
        for (int i = 0; i < MAX_SIDE; i++) {
            k = k * (MAX_SIDE + 1) + (i < s.length ? s[i] : 0);
        }
        return k;
    }

    /** True when the player to move wins with perfect play. */
    public boolean wins(int[] shape) {
        check(shape);
        return win(shape);
    }

    private boolean win(int[] s) {
        long k = key(s);
        Boolean c = memo.get(k);
        if (c != null) {
            return c;
        }
        boolean w = false;
        for (int i = 0; i < s.length && !w; i++) {
            for (int j = 0; j < s[i] && !w; j++) {
                if (i != 0 || j != 0) {
                    w = !win(bite(s, i, j));
                }
            }
        }
        memo.put(k, w);
        return w;
    }

    /** A winning bite {row, col}, or an empty array when the player to move loses. */
    public int[] winningBite(int[] shape) {
        check(shape);
        for (int i = 0; i < shape.length; i++) {
            for (int j = 0; j < shape[i]; j++) {
                if ((i != 0 || j != 0) && !win(bite(shape, i, j))) {
                    return new int[] {i, j};
                }
            }
        }
        return new int[0];
    }

    /** Quest q_hardtack_bar: the cook says whether the first deckhand wins on this bar. */
    public static boolean quest(int rows, int cols, boolean firstWins) {
        return new HardtackBar().wins(bar(rows, cols)) == firstWins;
    }
}