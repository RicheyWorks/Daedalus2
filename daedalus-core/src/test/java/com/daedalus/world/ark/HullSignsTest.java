// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class HullSignsTest {

    private static boolean bruteExists(int n) {
        int cells = n * n;
        for (int mask = 0; mask < (1 << cells); mask++) {
            int[][] h = new int[n][n];
            for (int c = 0; c < cells; c++) {
                h[c / n][c % n] = (mask >> c & 1) != 0 ? -1 : 1;
            }
            if (HullSigns.isHadamard(h)) {
                return true;
            }
        }
        return false;
    }

    @Test
    void smallOrdersMatchBruteForce() {
        for (int n = 1; n <= 4; n++) {
            boolean want = bruteExists(n);
            assertThat(want).isEqualTo(n != 3);
            assertThat(HullSigns.build(n).length == n).isEqualTo(want);
        }
    }

    @Test
    void constructionsAreValid() {
        int built = 0;
        for (int n = 1; n <= 100; n++) {
            int[][] h = HullSigns.build(n);
            if (h.length > 0) {
                built++;
                assertThat(h.length).isEqualTo(n);
                assertThat(HullSigns.isHadamard(h)).isTrue();
            } else {
                assertThat(n).isGreaterThan(2);
            }
        }
        assertThat(built).isEqualTo(20);
        assertThat(HullSigns.isHadamard(HullSigns.build(512))).isTrue();
        assertThat(HullSigns.isHadamard(HullSigns.paley(43))).isTrue();
    }

    @Test
    void questAndGuards() {
        assertThat(HullSigns.QUEST_ID).isEqualTo("q_hull_signs");
        assertThat(HullSigns.quest(2, new int[][] {{1, 1}, {1, -1}})).isTrue();
        assertThat(HullSigns.quest(2, new int[][] {{1, 1}, {1, 1}})).isFalse();
        assertThatThrownBy(() -> HullSigns.paley(5)).isInstanceOf(IllegalArgumentException.class);
    }
}