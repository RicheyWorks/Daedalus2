// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class LampCodeTest {

    @Test
    void codeHasMinimumDistanceFour() {
        for (int a = 0; a < 16; a++) {
            for (int b = a + 1; b < 16; b++) {
                assertThat(Integer.bitCount(LampCode.encode(a) ^ LampCode.encode(b))).isGreaterThanOrEqualTo(4);
            }
        }
    }

    @Test
    void decodeMatchesNearestCodewordBruteForce() {
        for (int word = 0; word < 256; word++) {
            int best = -1;
            int bestDist = 99;
            int ties = 0;
            for (int m = 0; m < 16; m++) {
                int dist = Integer.bitCount(word ^ LampCode.encode(m));
                if (dist < bestDist) {
                    bestDist = dist;
                    best = m;
                    ties = 1;
                } else if (dist == bestDist) {
                    ties++;
                }
            }
            if (bestDist <= 1) {
                assertThat(LampCode.decode(word)).hasValue(best);
                assertThat(LampCode.flipsSeen(word)).isEqualTo(bestDist);
            } else {
                assertThat(bestDist).isEqualTo(2);
                assertThat(ties).isGreaterThan(1);
                assertThat(LampCode.decode(word)).isEmpty();
            }
        }
    }

    @Test
    void everyOneAndTwoFlip() {
        for (int m = 0; m < 16; m++) {
            int w = LampCode.encode(m);
            assertThat(LampCode.flipsSeen(w)).isZero();
            for (int i = 0; i < 8; i++) {
                assertThat(LampCode.decode(w ^ (1 << i))).hasValue(m);
                for (int j = i + 1; j < 8; j++) {
                    assertThat(LampCode.decode(w ^ (1 << i) ^ (1 << j))).isEmpty();
                }
            }
        }
    }

    @Test
    void questAndGuards() {
        assertThat(LampCode.QUEST_ID).isEqualTo("q_lamp_code");
        assertThat(LampCode.quest(LampCode.encode(11) ^ 8, 11)).isTrue();
        assertThat(LampCode.quest(LampCode.encode(11) ^ 24, 11)).isFalse();
        assertThatThrownBy(() -> LampCode.encode(16)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LampCode.decode(256)).isInstanceOf(IllegalArgumentException.class);
    }
}