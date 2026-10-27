// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class SoundingMarksTest {

    private static int[] marksOf(int mask, int len) {
        int[] out = new int[Integer.bitCount(mask) + 2];
        int n = 0;
        out[n++] = 0;
        for (int p = 1; p < len; p++) {
            if ((mask >> (p - 1) & 1) != 0) {
                out[n++] = p;
            }
        }
        out[n] = len;
        return out;
    }

    @Test
    void shortestMatchesBruteForceSubsets() {
        for (int k = 2; k <= 6; k++) {
            int want = -1;
            for (int len = 1; want < 0; len++) {
                for (int mask = 0; mask < (1 << (len - 1)); mask++) {
                    if (Integer.bitCount(mask) == k - 2 && SoundingMarks.isGolomb(marksOf(mask, len))) {
                        want = len;
                        break;
                    }
                }
            }
            int[] got = SoundingMarks.shortest(k);
            assertThat(got).hasSize(k);
            assertThat(SoundingMarks.isGolomb(got)).isTrue();
            assertThat(got[k - 1]).isEqualTo(want);
        }
    }

    @Test
    void knownOptimalLengths() {
        int[] lengths = {0, 1, 3, 6, 11, 17, 25, 34};
        for (int k = 1; k <= 8; k++) {
            int[] got = SoundingMarks.shortest(k);
            assertThat(SoundingMarks.isGolomb(got)).isTrue();
            assertThat(got[k - 1]).isEqualTo(lengths[k - 1]);
        }
    }

    @Test
    void questAndGuards() {
        assertThat(SoundingMarks.QUEST_ID).isEqualTo("q_sounding_marks");
        assertThat(SoundingMarks.quest(4, new int[] {0, 1, 4, 6})).isTrue();
        assertThat(SoundingMarks.quest(4, new int[] {0, 1, 3, 7})).isFalse();
        assertThat(SoundingMarks.isGolomb(new int[] {0, 1, 2})).isFalse();
        assertThatThrownBy(() -> SoundingMarks.shortest(9)).isInstanceOf(IllegalArgumentException.class);
    }
}