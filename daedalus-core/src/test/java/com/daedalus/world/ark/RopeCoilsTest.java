// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class RopeCoilsTest {

    @Test
    void fibonacciExactAndModular() {
        BigInteger a = BigInteger.ZERO;
        BigInteger b = BigInteger.ONE;
        for (int n = 0; n <= 500; n++) {
            assertThat(RopeCoils.fib(n)).as("n=%d", n).isEqualTo(a);
            assertThat(RopeCoils.fibMod(n, 1_000_000_007L))
                .isEqualTo(a.mod(BigInteger.valueOf(1_000_000_007L)).longValueExact());
            BigInteger t = a.add(b);
            a = b;
            b = t;
        }
        assertThat(RopeCoils.fib(100)).isEqualTo(new BigInteger("354224848179261915075"));
        assertThat(RopeCoils.fibMod(1_000_000_000_000L, 10)).isEqualTo(5);
        assertThat(RopeCoils.fibMod(60, 10)).isZero();
        assertThat(RopeCoils.fibMod(5, 1)).isZero();
    }

    @Test
    void cutsAreValidAndUnique() {
        assertThat(RopeCoils.cut(100)).containsExactly(89L, 8L, 3L);
        assertThat(RopeCoils.cut(0)).isEmpty();
        assertThat(RopeCoils.valid(Long.MAX_VALUE, RopeCoils.cut(Long.MAX_VALUE))).isTrue();
        for (long x = 0; x <= 3000; x++) {
            assertThat(RopeCoils.valid(x, RopeCoils.cut(x))).as("x=%d", x).isTrue();
        }
        SplittableRandom rnd = new SplittableRandom(263);
        for (int t = 0; t < 500; t++) {
            long x = rnd.nextLong(0, Long.MAX_VALUE);
            assertThat(RopeCoils.valid(x, RopeCoils.cut(x))).isTrue();
        }
    }

    @Test
    void badCutsAndQuest() {
        assertThat(RopeCoils.quest(100, List.of(89L, 8L, 3L))).isTrue();
        assertThat(RopeCoils.quest(100, List.of(89L, 5L, 3L, 2L, 1L))).isFalse();
        assertThat(RopeCoils.quest(10, List.of(8L, 2L))).isTrue();
        assertThat(RopeCoils.quest(10, List.of(5L, 3L, 2L))).isFalse();
        assertThat(RopeCoils.quest(8, List.of(4L, 4L))).isFalse();
        assertThat(RopeCoils.quest(2, List.of(1L, 1L))).isFalse();
        assertThat(RopeCoils.quest(11, List.of(3L, 8L))).isFalse();
        assertThat(RopeCoils.QUEST_ID).isEqualTo("q_rope_coils");
        assertThatThrownBy(() -> RopeCoils.cut(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RopeCoils.fibMod(3, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
