// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class BallastGridTest {

    @Test
    void everyHoldSizeBalances() {
        for (int n = 1; n <= 60; n++) {
            if (n == 2) {
                continue;
            }
            assertThat(BallastGrid.valid(BallastGrid.build(n))).as("n=%d", n).isTrue();
        }
    }

    @Test
    void magicWeightsAndTheLoShu() {
        assertThat(BallastGrid.magicWeight(3)).isEqualTo(15);
        assertThat(BallastGrid.magicWeight(4)).isEqualTo(34);
        assertThat(BallastGrid.magicWeight(1000)).isEqualTo(500_000_500L);
        int[][] lo = BallastGrid.build(3);
        assertThat(lo[1][1]).isEqualTo(5);
        assertThat(BallastGrid.build(1)).isDeepEqualTo(new int[][] {{1}});
    }

    @Test
    void unbalancedPlansFail() {
        int[][] g = BallastGrid.build(4);
        int t = g[0][0];
        g[0][0] = g[0][1];
        g[0][1] = t;
        assertThat(BallastGrid.valid(g)).isFalse();
        assertThat(BallastGrid.valid(new int[][] {{1, 2}, {3, 4}})).isFalse();
        assertThat(BallastGrid.valid(new int[][] {{5, 5, 5}, {5, 5, 5}, {5, 5, 5}})).isFalse();
        assertThat(BallastGrid.valid(new int[0][0])).isFalse();
    }

    @Test
    void questAndValidation() {
        assertThat(BallastGrid.quest(6, BallastGrid.build(6))).isTrue();
        assertThat(BallastGrid.quest(5, BallastGrid.build(6))).isFalse();
        assertThat(BallastGrid.QUEST_ID).isEqualTo("q_ballast_grid");
        assertThatThrownBy(() -> BallastGrid.build(2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BallastGrid.build(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BallastGrid.magicWeight(0)).isInstanceOf(IllegalArgumentException.class);
    }
}
