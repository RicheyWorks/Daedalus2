// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SquareHatchesTest {

    @Test
    void countsAndSplitsMatchBruteForce() {
        int max = 20_000;
        long[] ways = new long[max + 1];
        for (long a = -142; a <= 142; a++) {
            for (long b = -142; b <= 142; b++) {
                long s = a * a + b * b;
                if (s <= max) {
                    ways[(int) s]++;
                }
            }
        }
        for (int n = 0; n <= max; n++) {
            assertThat(SquareHatches.r2(n)).as("n=%d", n).isEqualTo(ways[n]);
            assertThat(SquareHatches.isTwoSquares(n)).isEqualTo(ways[n] > 0);
            long[] s = SquareHatches.split(n);
            if (ways[n] > 0) {
                assertThat(s[0] * s[0] + s[1] * s[1]).isEqualTo(n);
                assertThat(s[0]).isLessThanOrEqualTo(s[1]);
            } else {
                assertThat(s).isEmpty();
            }
        }
    }

    @Test
    void largeAreasAndFourSquares() {
        SplittableRandom rnd = new SplittableRandom(310);
        for (int t = 0; t < 3000; t++) {
            long n = rnd.nextLong(1, LanternHandshake.MAX_MOD);
            long[] s = SquareHatches.split(n);
            if (s.length == 2) {
                assertThat(s[0] * s[0] + s[1] * s[1]).as("n=%d", n).isEqualTo(n);
            }
            long[] f = SquareHatches.fourSquares(n);
            assertThat(f[0] * f[0] + f[1] * f[1] + f[2] * f[2] + f[3] * f[3]).isEqualTo(n);
        }
        for (long n = 0; n <= 3000; n++) {
            long[] f = SquareHatches.fourSquares(n);
            assertThat(f[0] * f[0] + f[1] * f[1] + f[2] * f[2] + f[3] * f[3]).isEqualTo(n);
        }
        long[] p = SquareHatches.split(1_000_000_009L);
        assertThat(p[0] * p[0] + p[1] * p[1]).isEqualTo(1_000_000_009L);
    }

    @Test
    void questAndBounds() {
        assertThat(SquareHatches.quest(25, 3, 4)).isTrue();
        assertThat(SquareHatches.quest(25, 0, 5)).isTrue();
        assertThat(SquareHatches.quest(25, 2, 4)).isFalse();
        assertThat(SquareHatches.r2(3)).isZero();
        assertThat(SquareHatches.r2(25)).isEqualTo(12);
        assertThat(SquareHatches.QUEST_ID).isEqualTo("q_square_hatches");
        assertThatThrownBy(() -> SquareHatches.r2(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SquareHatches.split(LanternHandshake.MAX_MOD)).isInstanceOf(IllegalArgumentException.class);
    }
}