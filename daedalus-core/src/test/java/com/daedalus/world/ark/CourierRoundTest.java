// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class CourierRoundTest {

    @Test
    void roundsExistFromTheCornerFromFiveUp() {
        for (int n = 5; n <= 40; n++) {
            int[] r = CourierRound.round(n, 0, 0);
            assertThat(r).as("n=%d", n).isNotNull();
            assertThat(CourierRound.valid(n, r)).isTrue();
            assertThat(r[0]).isZero();
        }
    }

    @Test
    void everyStartOnTheClassicDeck() {
        for (int s = 0; s < 64; s++) {
            int[] r = CourierRound.round(8, s / 8, s % 8);
            assertThat(CourierRound.quest(8, s / 8, s % 8, r)).as("start=%d", s).isTrue();
        }
    }

    @Test
    void smallDecksHaveNoRound() {
        assertThat(CourierRound.round(1, 0, 0)).containsExactly(0);
        assertThat(CourierRound.round(2, 0, 0)).isNull();
        assertThat(CourierRound.round(3, 0, 0)).isNull();
        assertThat(CourierRound.round(4, 0, 0)).isNull();
    }

    @Test
    void validatorRejectsBadRoutes() {
        int[] r = CourierRound.round(6, 0, 0);
        int[] swapped = r.clone();
        int t = swapped[3];
        swapped[3] = swapped[4];
        swapped[4] = t;
        assertThat(CourierRound.valid(6, swapped)).isFalse();
        assertThat(CourierRound.valid(6, new int[36])).isFalse();
        assertThat(CourierRound.valid(6, new int[3])).isFalse();
        assertThat(CourierRound.quest(6, 0, 1, r)).isFalse();
        assertThat(CourierRound.QUEST_ID).isEqualTo("q_courier_round");
        assertThatThrownBy(() -> CourierRound.round(5, 5, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
