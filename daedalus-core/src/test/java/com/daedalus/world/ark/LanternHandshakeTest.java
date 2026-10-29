// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class LanternHandshakeTest {

    @Test
    void powerMatchesBigIntegerAndCountsAreLogarithmic() {
        SplittableRandom rnd = new SplittableRandom(271);
        for (int t = 0; t < 2000; t++) {
            long m = rnd.nextLong(1, LanternHandshake.MAX_MOD + 1);
            long b = rnd.nextLong(0, Long.MAX_VALUE);
            long e = rnd.nextLong(0, Long.MAX_VALUE);
            long want = BigInteger.valueOf(b).modPow(BigInteger.valueOf(e), BigInteger.valueOf(m)).longValue();
            LanternHandshake.Power got = LanternHandshake.power(b, e, m);
            assertThat(got.value()).isEqualTo(want);
            assertThat(got.multiplications()).isLessThanOrEqualTo(2 * 64);
        }
        assertThat(LanternHandshake.power(3, 0, 7)).isEqualTo(new LanternHandshake.Power(1, 0));
        assertThat(LanternHandshake.power(3, 1, 1).value()).isZero();
        assertThat(LanternHandshake.power(2, 1L << 40, 1_000_003).multiplications()).isEqualTo(41);
    }

    @Test
    void millerRabinMatchesTrialDivision() {
        for (long n = 0; n < 20_000; n++) {
            assertThat(LanternHandshake.isPrime(n)).as("n=%d", n).isEqualTo(BigInteger.valueOf(n).isProbablePrime(50));
        }
        assertThat(LanternHandshake.isPrime(2_147_483_647L)).isTrue();
        assertThat(LanternHandshake.isPrime(LanternHandshake.MAX_MOD - 1)).isEqualTo(
            BigInteger.valueOf(LanternHandshake.MAX_MOD - 1).isProbablePrime(50));
        assertThat(LanternHandshake.isPrime(561)).isFalse();
        assertThat(LanternHandshake.isPrime(25_326_001)).isFalse();
        assertThat(LanternHandshake.isPrime(2_152_302_898_747L % LanternHandshake.MAX_MOD)).isEqualTo(
            BigInteger.valueOf(2_152_302_898_747L % LanternHandshake.MAX_MOD).isProbablePrime(50));
    }

    @Test
    void bothArksReachTheSameCode() {
        LanternHandshake.Handshake h = LanternHandshake.handshake(23, 5, 6, 15);
        assertThat(h).isEqualTo(new LanternHandshake.Handshake(8, 19, 2));
        SplittableRandom rnd = new SplittableRandom(5);
        long p = 2_147_483_647L;
        for (int t = 0; t < 200; t++) {
            long a = rnd.nextLong(1, p);
            long b = rnd.nextLong(1, p);
            LanternHandshake.Handshake x = LanternHandshake.handshake(p, 7, a, b);
            assertThat(LanternHandshake.powMod(x.flashA(), b, p)).isEqualTo(x.code());
        }
    }

    @Test
    void questAndBadInput() {
        assertThat(LanternHandshake.quest(23, 5, 6, 15, 2)).isTrue();
        assertThat(LanternHandshake.quest(23, 5, 6, 15, 3)).isFalse();
        assertThat(LanternHandshake.QUEST_ID).isEqualTo("q_lantern_handshake");
        assertThatThrownBy(() -> LanternHandshake.handshake(21, 5, 1, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LanternHandshake.power(2, 3, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LanternHandshake.isPrime(LanternHandshake.MAX_MOD)).isInstanceOf(IllegalArgumentException.class);
    }
}
