// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

/** Small parsing helpers shared by the cabinet adapters. */
final class CabinetMoves {

    private CabinetMoves() {
    }

    /** The move as a whole number, or -1 when it is not one. */
    static int number(String move) {
        if (move == null) {
            return -1;
        }
        try {
            return Integer.parseInt(move.trim());
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    /** A "row,col" move as two whole numbers, or {-1, -1} when malformed. */
    static int[] pair(String move) {
        if (move == null) {
            return new int[] {-1, -1};
        }
        String[] p = move.trim().split("\\s*,\\s*");
        if (p.length != 2) {
            return new int[] {-1, -1};
        }
        return new int[] {number(p[0]), number(p[1])};
    }
}
