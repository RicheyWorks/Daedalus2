// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G402 The Hold Weights: the quartermaster stows crates weighing 1..9, one each, in a 3x3 hold
 * (classic Sujiko). Four clues give the total of each 2x2 corner block: top-left, top-right,
 * bottom-left, bottom-right. Boards and givens are 9 cells in row order; givens use 0 for blank.
 */
public final class HoldWeights {

    public static final String QUEST_ID = "q_hold_weights";

    private static final int[][] BLOCKS = {{0, 1, 3, 4}, {1, 2, 4, 5}, {3, 4, 6, 7}, {4, 5, 7, 8}};
    /** Cell index after which each block is complete. */
    private static final int[] DONE_AT = {4, 5, 7, 8};

    private HoldWeights() { }

    private static void check(int[] clues, int[] givens) {
        if (clues.length != 4 || givens.length != 9) {
            throw new IllegalArgumentException("4 clues, 9 givens");
        }
        for (int v : clues) {
            if (v < 10 || v > 30) {
                throw new IllegalArgumentException("clue 10..30");
            }
        }
        for (int v : givens) {
            if (v < 0 || v > 9) {
                throw new IllegalArgumentException("given 0..9");
            }
        }
    }

    /** True when the board uses 1..9 once each, meets every clue and every given. */
    public static boolean isValid(int[] clues, int[] givens, int[] board) {
        check(clues, givens);
        if (board.length != 9) {
            return false;
        }
        int seen = 0;
        for (int i = 0; i < 9; i++) {
            int v = board[i];
            if (v < 1 || v > 9 || (seen >> v & 1) != 0 || givens[i] != 0 && givens[i] != v) {
                return false;
            }
            seen |= 1 << v;
        }
        for (int k = 0; k < 4; k++) {
            int s = 0;
            for (int i : BLOCKS[k]) {
                s += board[i];
            }
            if (s != clues[k]) {
                return false;
            }
        }
        return true;
    }

    private static final class Search {
        final int[] clues;
        final int[] givens;
        final int[] b = new int[9];
        final long limit;
        int used;
        long count;
        int[] first = new int[0];

        Search(int[] clues, int[] givens, long limit) {
            this.clues = clues;
            this.givens = givens;
            this.limit = limit;
        }

        boolean blocksOk(int cell) {
            for (int k = 0; k < 4; k++) {
                if (DONE_AT[k] == cell) {
                    int s = 0;
                    for (int i : BLOCKS[k]) {
                        s += b[i];
                    }
                    if (s != clues[k]) {
                        return false;
                    }
                }
            }
            return true;
        }

        void run(int cell) {
            if (count >= limit) {
                return;
            }
            if (cell == 9) {
                if (count == 0) {
                    first = b.clone();
                }
                count++;
                return;
            }
            for (int v = 1; v <= 9; v++) {
                if ((used >> v & 1) != 0 || givens[cell] != 0 && givens[cell] != v) {
                    continue;
                }
                b[cell] = v;
                if (blocksOk(cell)) {
                    used |= 1 << v;
                    run(cell + 1);
                    used &= ~(1 << v);
                }
                b[cell] = 0;
            }
        }
    }

    /** Number of valid boards, stopping at limit. */
    public static long count(int[] clues, int[] givens, long limit) {
        check(clues, givens);
        Search s = new Search(clues, givens, limit);
        s.run(0);
        return s.count;
    }

    /** First valid board, or an empty array when none exists. */
    public static int[] solve(int[] clues, int[] givens) {
        check(clues, givens);
        Search s = new Search(clues, givens, 1);
        s.run(0);
        return s.first;
    }

    /** Quest hook: the player's board must meet every clue and given. */
    public static boolean quest(int[] clues, int[] givens, int[] answer) {
        return isValid(clues, givens, answer);
    }
}