// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class TwoHoardsTest {

    private static final int N = 120;

    private static boolean[][] bruteLosing() {
        boolean[][] lose = new boolean[N][N];
        for (int s = 0; s < 2 * N; s++) {
            for (int x = 0; x < N; x++) {
                int y = s - x;
                if (y < 0 || y >= N) {
                    continue;
                }
                boolean canWin = false;
                for (int t = 1; !canWin && t <= x; t++) {
                    canWin = lose[x - t][y];
                }
                for (int t = 1; !canWin && t <= y; t++) {
                    canWin = lose[x][y - t];
                }
                for (int t = 1; !canWin && t <= Math.min(x, y); t++) {
                    canWin = lose[x - t][y - t];
                }
                lose[x][y] = !canWin;
            }
        }
        return lose;
    }

    @Test
    void losingSpotsAndMovesMatchGameTree() {
        boolean[][] lose = bruteLosing();
        for (int x = 0; x < N; x++) {
            for (int y = 0; y < N; y++) {
                assertThat(TwoHoards.isLosing(x, y)).isEqualTo(lose[x][y]);
                long[] mv = TwoHoards.winningMove(x, y);
                if (lose[x][y]) {
                    assertThat(mv).isEmpty();
                } else {
                    assertThat(TwoHoards.quest(x, y, mv[0], mv[1])).isTrue();
                }
            }
        }
    }

    @Test
    void largeSpotsStayExact() {
        SplittableRandom rnd = new SplittableRandom(354);
        for (int t = 0; t < 20_000; t++) {
            long x = rnd.nextLong(0, 1_000_000_001L);
            long y = rnd.nextLong(0, 1_000_000_001L);
            long[] mv = TwoHoards.winningMove(x, y);
            if (mv.length > 0) {
                assertThat(TwoHoards.quest(x, y, mv[0], mv[1])).isTrue();
            }
        }
        java.math.BigDecimal phi = new java.math.BigDecimal("1.6180339887498948482045868343656381177203");
        for (long k = 999_990_000L; k <= 1_000_000_000L; k += 7) {
            long want = phi.multiply(java.math.BigDecimal.valueOf(k)).longValue();
            assertThat(TwoHoards.lowerOf(k)).isEqualTo(want);
        }
    }

    @Test
    void questAndGuards() {
        assertThat(TwoHoards.QUEST_ID).isEqualTo("q_two_hoards");
        assertThat(TwoHoards.isLosing(3, 5)).isTrue();
        assertThat(TwoHoards.quest(4, 5, 3, 5)).isTrue();
        assertThat(TwoHoards.quest(4, 5, 2, 3)).isFalse();
        assertThatThrownBy(() -> TwoHoards.isLosing(-1, 2)).isInstanceOf(IllegalArgumentException.class);
    }
}