// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.FlameGenerations.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class FlameGenerationsTest {

    @Test
    void matchesDirectIterationOnSeededRecurrences() {
        for (long seed = 0; seed < 120; seed++) {
            int k = 1 + (int) (seed % 5);
            long m = seed % 2 == 0 ? FlameGenerations.PRIME : 97;
            long[] c = FlameGenerations.seeded(seed, k, m);
            long[] init = FlameGenerations.seeded(seed + 1000, k, m);
            long[] a = new long[200];
            for (int i = 0; i < 200; i++) {
                if (i < k) {
                    a[i] = init[i];
                } else {
                    long s = 0;
                    for (int j = 0; j < k; j++) {
                        s = (s + c[j] * a[i - 1 - j]) % m;
                    }
                    a[i] = s;
                }
                assertThat(FlameGenerations.nthTerm(c, init, i, m)).as("seed %d n %d", seed, i).isEqualTo(a[i]);
            }
        }
    }

    @Test
    void knownRecurrences() {
        long[] fib = {1, 1};
        long[] start = {0, 1};
        assertThat(FlameGenerations.nthTerm(fib, start, 10, FlameGenerations.PRIME)).isEqualTo(55);
        assertThat(FlameGenerations.nthTerm(fib, start, 90, FlameGenerations.PRIME))
                .isEqualTo(2880067194370816120L % FlameGenerations.PRIME);
        long p = FlameGenerations.PRIME;
        assertThat(FlameGenerations.nthTerm(new long[] {2}, new long[] {1}, p - 1, p)).isEqualTo(1);
        assertThat(FlameGenerations.nthTerm(new long[] {2}, new long[] {1}, (p - 1) * 1_000_000_000L + 3, p))
                .isEqualTo(8);
        assertThat(FlameGenerations.nthTerm(new long[] {-1}, new long[] {5}, 3, 7)).isEqualTo(2);
        assertThatThrownBy(() -> FlameGenerations.nthTerm(fib, new long[] {1}, 3, 7))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FlameGenerations.matPow(new long[][] {{1}}, -1, 7))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        long[] fib = {1, 1};
        long[] start = {0, 1};
        assertThat(FlameGenerations.grade(fib, start, 10, 1000, 55)).isEqualTo(Grade.FORETOLD);
        assertThat(FlameGenerations.grade(fib, start, 10, 1000, 89)).isEqualTo(Grade.GUESSED);
        for (Grade g : Grade.values()) {
            assertThat(FlameGenerations.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(FlameGenerations.QUEST_ID).isEqualTo("q_flame_generations");
        assertThat(FlameGenerations.seeded(3, 4, 50)).containsExactly(FlameGenerations.seeded(3, 4, 50));
        assertThatThrownBy(() -> FlameGenerations.seeded(1, 0, 50)).isInstanceOf(IllegalArgumentException.class);
    }
}
