// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class SumFreeCrewsTest {

    private static boolean bruteExists(int n, int k) {
        int total = 1;
        for (int i = 0; i < n; i++) {
            total *= k;
        }
        int[] crew = new int[n];
        for (int code = 0; code < total; code++) {
            int x = code;
            for (int i = 0; i < n; i++) {
                crew[i] = x % k;
                x /= k;
            }
            if (SumFreeCrews.isValid(crew, k)) {
                return true;
            }
        }
        return false;
    }

    @Test
    void finderMatchesBruteForceColourings() {
        for (int k = 1; k <= 3; k++) {
            for (int n = 1; n <= 14; n++) {
                int[] got = SumFreeCrews.split(n, k);
                boolean want = bruteExists(n, k);
                assertThat(got.length > 0).isEqualTo(want);
                if (want) {
                    assertThat(SumFreeCrews.isValid(got, k)).isTrue();
                }
            }
        }
    }

    @Test
    void knownSchurNumbers() {
        assertThat(SumFreeCrews.largest(1)).isEqualTo(1);
        assertThat(SumFreeCrews.largest(2)).isEqualTo(4);
        assertThat(SumFreeCrews.largest(3)).isEqualTo(13);
        int[] four = SumFreeCrews.split(44, 4);
        assertThat(four).hasSize(44);
        assertThat(SumFreeCrews.isValid(four, 4)).isTrue();
    }

    @Test
    void questAndGuards() {
        assertThat(SumFreeCrews.QUEST_ID).isEqualTo("q_sum_free_crews");
        assertThat(SumFreeCrews.quest(4, 2, new int[] {0, 1, 1, 0})).isTrue();
        assertThat(SumFreeCrews.quest(4, 2, new int[] {0, 0, 1, 1})).isFalse();
        assertThatThrownBy(() -> SumFreeCrews.split(61, 2)).isInstanceOf(IllegalArgumentException.class);
    }
}