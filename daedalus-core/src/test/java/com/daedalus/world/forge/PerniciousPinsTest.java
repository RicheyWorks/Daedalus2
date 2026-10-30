// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class PerniciousPinsTest {

    private static boolean brute(long n) {
        int ones = 0;
        for (char c : Long.toBinaryString(n).toCharArray()) {
            if (c == '1') {
                ones++;
            }
        }
        if (ones < 2) {
            return false;
        }
        for (int d = 2; d < ones; d++) {
            if (ones % d == 0) {
                return false;
            }
        }
        return true;
    }

    @Test
    void matchesPopcountBruteForce() {
        long run = 0;
        for (long n = 0; n <= 200_000; n++) {
            boolean b = brute(n);
            assertThat(PerniciousPins.isPernicious(n)).as("n=%d", n).isEqualTo(b);
            if (b) {
                run++;
                if (run % 97 == 0) {
                    assertThat(PerniciousPins.nthPernicious(run)).isEqualTo(n);
                }
            }
            if (n % 331 == 0 || n < 100) {
                assertThat(PerniciousPins.countPernicious(n)).as("count %d", n).isEqualTo(run);
            }
        }
    }

    @Test
    void knownPerniciousPins() {
        List<Long> first = new ArrayList<>();
        for (long k = 1; k <= 20; k++) {
            first.add(PerniciousPins.nthPernicious(k));
        }
        assertThat(first).containsExactly(3L, 5L, 6L, 7L, 9L, 10L, 11L, 12L, 13L, 14L, 17L, 18L, 19L, 20L, 21L,
                22L, 24L, 25L, 26L, 28L);
    }

    @Test
    void countAgreesWithFilterOnBigWindows() {
        Random r = new Random(495);
        for (int t = 0; t < 20; t++) {
            long lo = (long) (r.nextDouble() * (PerniciousPins.MAX_N - 5000));
            long hi = lo + r.nextInt(5000);
            long c = PerniciousPins.countPernicious(lo);
            for (long n = lo + 1; n <= hi; n++) {
                c += brute(n) ? 1 : 0;
            }
            assertThat(PerniciousPins.countPernicious(hi)).isEqualTo(c);
            long k = 1 + (long) (r.nextDouble() * (PerniciousPins.countPernicious(PerniciousPins.MAX_N) - 1));
            long p = PerniciousPins.nthPernicious(k);
            assertThat(brute(p)).isTrue();
            assertThat(PerniciousPins.countPernicious(p)).isEqualTo(k);
            assertThat(PerniciousPins.countPernicious(p - 1)).isEqualTo(k - 1);
        }
    }

    @Test
    void edgesAndGuards() {
        for (int i = 0; i < 59; i++) {
            assertThat(PerniciousPins.isPernicious(1L << i)).isFalse();
            long ones = (1L << (i + 1)) - 1;
            assertThat(PerniciousPins.isPernicious(ones)).isEqualTo(brute(ones));
        }
        assertThat(PerniciousPins.countPernicious(0)).isZero();
        assertThat(PerniciousPins.countPernicious(2)).isZero();
        assertThat(PerniciousPins.countPernicious(3)).isEqualTo(1);
        assertThat(PerniciousPins.isPernicious(PerniciousPins.MAX_N)).isEqualTo(brute(PerniciousPins.MAX_N));
        assertThatThrownBy(() -> PerniciousPins.isPernicious(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PerniciousPins.countPernicious(PerniciousPins.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PerniciousPins.nthPernicious(0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(PerniciousPins.grade(3, true)).isEqualTo(PerniciousPins.Grade.TURNED);
        assertThat(PerniciousPins.grade(15, true)).isEqualTo(PerniciousPins.Grade.SLIPPED);
        assertThat(PerniciousPins.grade(15, false)).isEqualTo(PerniciousPins.Grade.TURNED);
        for (PerniciousPins.Grade g : PerniciousPins.Grade.values()) {
            assertThat(PerniciousPins.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(PerniciousPins.QUEST_ID).isEqualTo("q_pernicious_pins");
    }
}
