// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * G366 The Peg Board: the crew's triangular peg board has side s (holes numbered row by row). One
 * hole starts empty; a move jumps a peg over a neighbour into an empty hole in a straight line and
 * removes the jumped peg. The solver searches for a finish with one peg left, remembering dead
 * boards so each is explored once.
 */
public final class PegBoard {

    public static final String QUEST_ID = "q_peg_board";

    private static final int[][] DIRS = {{0, 1}, {0, -1}, {1, 0}, {-1, 0}, {1, 1}, {-1, -1}};

    private PegBoard() { }

    private static void checkSide(int side) {
        if (side < 2 || side > 5) {
            throw new IllegalArgumentException("side 2..5: " + side);
        }
    }

    private static int index(int r, int c) {
        return r * (r + 1) / 2 + c;
    }

    /** Every jump {from, over, to} on a board of the given side. */
    public static int[][] jumps(int side) {
        checkSide(side);
        List<int[]> out = new ArrayList<>();
        for (int r = 0; r < side; r++) {
            for (int c = 0; c <= r; c++) {
                for (int[] d : DIRS) {
                    int r2 = r + 2 * d[0];
                    int c2 = c + 2 * d[1];
                    if (r2 >= 0 && r2 < side && c2 >= 0 && c2 <= r2) {
                        out.add(new int[] {index(r, c), index(r + d[0], c + d[1]), index(r2, c2)});
                    }
                }
            }
        }
        return out.toArray(new int[0][]);
    }

    private static int start(int side, int hole) {
        int holes = side * (side + 1) / 2;
        if (hole < 0 || hole >= holes) {
            throw new IllegalArgumentException("hole 0.." + (holes - 1));
        }
        return ((1 << holes) - 1) & ~(1 << hole);
    }

    /** Moves that leave one peg, or an empty array when the board cannot be cleared to one. */
    public static int[][] solve(int side, int hole) {
        checkSide(side);
        int board = start(side, hole);
        int[][] js = jumps(side);
        List<int[]> path = new ArrayList<>();
        if (search(board, js, new HashSet<>(), path)) {
            return path.toArray(new int[0][]);
        }
        return new int[0][];
    }

    private static boolean search(int board, int[][] js, Set<Integer> dead, List<int[]> path) {
        if (Integer.bitCount(board) == 1) {
            return true;
        }
        if (dead.contains(board)) {
            return false;
        }
        for (int[] j : js) {
            if ((board >> j[0] & 1) == 1 && (board >> j[1] & 1) == 1 && (board >> j[2] & 1) == 0) {
                path.add(j);
                int next = board & ~(1 << j[0]) & ~(1 << j[1]) | (1 << j[2]);
                if (search(next, js, dead, path)) {
                    return true;
                }
                path.remove(path.size() - 1);
            }
        }
        dead.add(board);
        return false;
    }

    /** True when the moves are legal from the start and leave exactly one peg. */
    public static boolean isSolution(int side, int hole, int[][] moves) {
        checkSide(side);
        int board = start(side, hole);
        Set<String> legal = new HashSet<>();
        for (int[] j : jumps(side)) {
            legal.add(j[0] + "," + j[1] + "," + j[2]);
        }
        for (int[] mv : moves) {
            if (mv.length != 3 || !legal.contains(mv[0] + "," + mv[1] + "," + mv[2])) {
                return false;
            }
            if ((board >> mv[0] & 1) != 1 || (board >> mv[1] & 1) != 1 || (board >> mv[2] & 1) != 0) {
                return false;
            }
            board = board & ~(1 << mv[0]) & ~(1 << mv[1]) | (1 << mv[2]);
        }
        return Integer.bitCount(board) == 1;
    }

    /** Quest q_peg_board: clear the board to one peg from the given empty hole. */
    public static boolean quest(int side, int hole, int[][] moves) {
        return isSolution(side, hole, moves);
    }
}