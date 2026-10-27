// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class FourMastsTest {

    @Test
    void frameStewartMatchesBfsOnSmallCases() {
        for (int n = 0; n <= 7; n++) {
            assertThat((long) FourMasts.fewest(n, 4)).as("4 masts n=%d", n).isEqualTo(FourMasts.frameStewart(n, 4));
        }
        for (int n = 0; n <= 5; n++) {
            assertThat((long) FourMasts.fewest(n, 5)).as("5 masts n=%d", n).isEqualTo(FourMasts.frameStewart(n, 5));
        }
        for (int n = 0; n <= 8; n++) {
            assertThat((long) FourMasts.fewest(n, 3)).isEqualTo((1L << n) - 1);
        }
    }

    @Test
    void plansReplayInTheCountedMoves() {
        for (int p = 3; p <= 6; p++) {
            for (int n = 0; n <= 12; n++) {
                int[][] pl = FourMasts.plan(n, p);
                assertThat((long) pl.length).isEqualTo(FourMasts.frameStewart(n, p));
                assertThat(FourMasts.valid(n, p, pl)).as("p=%d n=%d", p, n).isTrue();
            }
        }
    }

    @Test
    void checkerRejectsBadMoves() {
        assertThat(FourMasts.valid(2, 4, new int[][] {{0, 1}, {0, 1}})).isFalse();
        assertThat(FourMasts.valid(2, 4, new int[][] {{1, 2}})).isFalse();
        assertThat(FourMasts.valid(2, 4, new int[][] {{0, 1}, {0, 3}, {1, 3}})).isTrue();
        assertThat(FourMasts.valid(2, 4, new int[][] {{0, 1}, {0, 3}})).isFalse();
    }

    @Test
    void questAndBounds() {
        long v = FourMasts.frameStewart(10, 4);
        assertThat(FourMasts.quest(10, v)).isTrue();
        assertThat(FourMasts.quest(10, v + 1)).isFalse();
        assertThat(FourMasts.frameStewart(3, 3)).isEqualTo(7);
        assertThat(FourMasts.frameStewart(30, 6)).isPositive();
        assertThat(FourMasts.QUEST_ID).isEqualTo("q_four_masts");
        assertThatThrownBy(() -> FourMasts.frameStewart(31, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FourMasts.plan(13, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FourMasts.fewest(12, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FourMasts.frameStewart(3, 7)).isInstanceOf(IllegalArgumentException.class);
    }
}