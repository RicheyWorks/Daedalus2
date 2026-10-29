// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SoundingLineTest {

    private static BigInteger randomBig(SplittableRandom rnd, int words) {
        BigInteger v = BigInteger.ZERO;
        for (int w = 0; w < words; w++) {
            v = v.shiftLeft(63).add(BigInteger.valueOf(rnd.nextLong(Long.MAX_VALUE)));
        }
        return v;
    }

    @Test
    void rootsBracketExactly() {
        SplittableRandom rnd = new SplittableRandom(295);
        for (int t = 0; t < 3000; t++) {
            BigInteger n = randomBig(rnd, rnd.nextInt(1, 9));
            int k = rnd.nextInt(1, 12);
            BigInteger r = SoundingLine.root(n, k);
            assertThat(r.pow(k)).isLessThanOrEqualTo(n);
            assertThat(r.add(BigInteger.ONE).pow(k)).isGreaterThan(n);
            if (k == 2) {
                assertThat(r).isEqualTo(n.sqrt());
            }
            assertThat(SoundingLine.remainder(n, k)).isEqualTo(n.subtract(r.pow(k)));
        }
        for (long n = 0; n < 5000; n++) {
            assertThat(SoundingLine.isqrt(BigInteger.valueOf(n))).isEqualTo(BigInteger.valueOf(n).sqrt());
        }
    }

    @Test
    void perfectPowersMatchBruteForce() {
        for (long n = 2; n < 20_000; n++) {
            int bestExp = 1;
            long bestBase = n;
            for (long a = 2; a * a <= n; a++) {
                long v = a;
                int e = 1;
                while (v < n) {
                    v *= a;
                    e++;
                }
                if (v == n && e > bestExp) {
                    bestExp = e;
                    bestBase = a;
                }
            }
            assertThat(SoundingLine.perfectPower(BigInteger.valueOf(n)))
                    .as("n=%d", n).isEqualTo(new SoundingLine.Power(BigInteger.valueOf(bestBase), bestExp));
        }
        BigInteger big = BigInteger.valueOf(12_345_678_901L).pow(37);
        assertThat(SoundingLine.perfectPower(big)).isEqualTo(new SoundingLine.Power(BigInteger.valueOf(12_345_678_901L), 37));
        assertThat(SoundingLine.perfectPower(BigInteger.TWO.pow(60))).isEqualTo(new SoundingLine.Power(BigInteger.TWO, 60));
    }

    @Test
    void questAndBounds() {
        assertThat(SoundingLine.quest(BigInteger.valueOf(64), BigInteger.TWO, 6)).isTrue();
        assertThat(SoundingLine.quest(BigInteger.valueOf(64), BigInteger.valueOf(8), 2)).isFalse();
        assertThat(SoundingLine.quest(BigInteger.valueOf(10), BigInteger.TEN, 1)).isTrue();
        assertThat(SoundingLine.QUEST_ID).isEqualTo("q_sounding_line");
        assertThatThrownBy(() -> SoundingLine.root(BigInteger.valueOf(-1), 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SoundingLine.root(BigInteger.TEN, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SoundingLine.perfectPower(BigInteger.ONE)).isInstanceOf(IllegalArgumentException.class);
    }
}