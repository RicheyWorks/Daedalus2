// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Random;
import org.junit.jupiter.api.Test;

class SelfForgedTest {

    private static long ds(long m) {
        long s = 0;
        for (char c : Long.toString(m).toCharArray()) {
            s += c - '0';
        }
        return s;
    }

    @Test
    void matchesFullScanBruteForce() {
        int n = 20_000;
        long[] gen = new long[n + 1];
        for (long m = n; m >= 1; m--) {
            long v = m + ds(m);
            if (v <= n) {
                gen[(int) v] = m;
            }
        }
        long count = 0;
        for (int x = 1; x <= n; x++) {
            assertThat(SelfForged.generator(x)).as("x=%d", x).isEqualTo(gen[x] == 0 ? -1 : gen[x]);
            if (gen[x] == 0) {
                count++;
            }
            if (x % 613 == 0 || x < 50) {
                assertThat(SelfForged.countSelf(x)).isEqualTo(count);
            }
        }
        long[] list = SelfForged.selfUpTo(n);
        assertThat(list).hasSize((int) count);
        for (long v : list) {
            assertThat(gen[(int) v]).isZero();
        }
    }

    @Test
    void knownSelfForgedMarks() {
        long[] first = java.util.Arrays.copyOf(SelfForged.selfUpTo(300), 30);
        assertThat(first).containsExactly(1, 3, 5, 7, 9, 20, 31, 42, 53, 64, 75, 86, 97, 108, 110, 121, 132, 143,
                154, 165, 176, 187, 198, 209, 211, 222, 233, 244, 255, 266);
        assertThat(SelfForged.generator(2)).isEqualTo(1);
        assertThat(SelfForged.generator(101)).isEqualTo(91);
    }

    @Test
    void sieveAgreesWithChecksOnRandomWindows() {
        Random r = new Random(491);
        for (int t = 0; t < 6; t++) {
            int lo = 100_000 + r.nextInt(9_000_000);
            int hi = lo + r.nextInt(2000);
            long c = SelfForged.countSelf(lo);
            for (long x = lo + 1; x <= hi; x++) {
                c += SelfForged.isSelf(x) ? 1 : 0;
            }
            assertThat(SelfForged.countSelf(hi)).isEqualTo(c);
        }
        for (int t = 0; t < 500; t++) {
            long x = 1 + (long) (r.nextDouble() * (SelfForged.MAX_N - 1));
            long g = SelfForged.generator(x);
            if (g > 0) {
                assertThat(g + ds(g)).isEqualTo(x);
            }
            long m = 1 + (long) (r.nextDouble() * 1e14);
            assertThat(SelfForged.isSelf(m + ds(m))).isFalse();
        }
    }

    @Test
    void edgesAndGuards() {
        assertThat(SelfForged.isSelf(1)).isTrue();
        assertThat(SelfForged.isSelf(2)).isFalse();
        assertThat(SelfForged.countSelf(0)).isZero();
        assertThat(SelfForged.selfUpTo(0)).isEmpty();
        assertThat(SelfForged.digitSum(0)).isZero();
        assertThat(SelfForged.stamp(999_999_999_999_999L)).isEqualTo(999_999_999_999_999L + 135);
        assertThat(SelfForged.generator(SelfForged.MAX_N)).isGreaterThanOrEqualTo(-1);
        assertThatThrownBy(() -> SelfForged.isSelf(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SelfForged.isSelf(SelfForged.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SelfForged.countSelf(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SelfForged.digitSum(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(SelfForged.grade(20, true)).isEqualTo(SelfForged.Grade.TURNED);
        assertThat(SelfForged.grade(21, true)).isEqualTo(SelfForged.Grade.SLIPPED);
        assertThat(SelfForged.grade(21, false)).isEqualTo(SelfForged.Grade.TURNED);
        for (SelfForged.Grade g : SelfForged.Grade.values()) {
            assertThat(SelfForged.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(SelfForged.QUEST_ID).isEqualTo("q_self_forged");
    }
}
