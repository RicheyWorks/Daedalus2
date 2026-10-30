// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class PegBoardTest {

    private static boolean brute(int board, int[][] js) {
        if (Integer.bitCount(board) == 1) {
            return true;
        }
        for (int[] j : js) {
            if ((board >> j[0] & 1) == 1 && (board >> j[1] & 1) == 1 && (board >> j[2] & 1) == 0
                    && brute(board & ~(1 << j[0]) & ~(1 << j[1]) | (1 << j[2]), js)) {
                return true;
            }
        }
        return false;
    }

    @Test
    void solverMatchesPlainGameTreeSearch() {
        for (int side = 2; side <= 5; side++) {
            int holes = side * (side + 1) / 2;
            int[][] js = PegBoard.jumps(side);
            for (int hole = 0; hole < holes; hole++) {
                boolean want = brute(((1 << holes) - 1) & ~(1 << hole), js);
                int[][] got = PegBoard.solve(side, hole);
                assertThat(got.length > 0).isEqualTo(want);
                if (want) {
                    assertThat(got.length).isEqualTo(holes - 2);
                    assertThat(PegBoard.isSolution(side, hole, got)).isTrue();
                }
            }
        }
        assertThat(PegBoard.solve(5, 0).length).isEqualTo(13);
    }

    @Test
    void jumpCounts() {
        assertThat(PegBoard.jumps(3)).hasNumberOfRows(6);
        assertThat(PegBoard.jumps(5)).hasNumberOfRows(36);
    }

    @Test
    void questAndGuards() {
        assertThat(PegBoard.QUEST_ID).isEqualTo("q_peg_board");
        assertThat(PegBoard.quest(5, 0, PegBoard.solve(5, 0))).isTrue();
        assertThat(PegBoard.quest(5, 0, new int[][] {{0, 1, 3}})).isFalse();
        assertThatThrownBy(() -> PegBoard.solve(6, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}