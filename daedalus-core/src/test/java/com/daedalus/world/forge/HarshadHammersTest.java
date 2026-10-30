// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Random;
import org.junit.jupiter.api.Test;

class HarshadHammersTest {

    @Test
    void countsMatchBruteForce() {
        long run = 0;
        for (long n = 1; n <= 30_000; n++) {
            long s = 0;
            for (long m = n; m > 0; m /= 10) {
                s += m % 10;
            }
            if (n % s == 0) {
                run++;
            }
            assertThat(HarshadHammers.isHarshad(n, 10)).isEqualTo(n % s == 0);
            if (n % 613 == 0 || n < 120) {
                assertThat(HarshadHammers.countHarshad(n)).as("N=%d", n).isEqualTo(run);
            }
        }
        Random r = new Random(457);
        for (int t = 0; t < 10; t++) {
            long lo = 1_000_000L + r.nextInt(5_000_000);
            long brute = HarshadHammers.countHarshad(lo);
            long hi = lo + r.nextInt(20_000);
            for (long n = lo + 1; n <= hi; n++) {
                if (HarshadHammers.isHarshad(n, 10)) {
                    brute++;
                }
            }
            assertThat(HarshadHammers.countHarshad(hi)).isEqualTo(brute);
        }
    }

    @Test
    void knownCountsAndBases() {
        long[] want = {10, 33, 213, 1538, 11872, 95428, 806095};
        long p = 10;
        for (long w : want) {
            assertThat(HarshadHammers.countHarshad(p)).as("N=%d", p).isEqualTo(w);
            p *= 10;
        }
        assertThat(HarshadHammers.countHarshad(0)).isZero();
        for (long n = 1; n <= 2000; n++) {
            assertThat(HarshadHammers.isHarshad(n, 2)).isEqualTo(n % Long.bitCount(n) == 0);
        }
        assertThat(HarshadHammers.isHarshad(37, 16)).isFalse();
        assertThat(HarshadHammers.digitSum(255, 16)).isEqualTo(30);
        assertThat(HarshadHammers.countHarshad(HarshadHammers.MAX_N)).isPositive();
    }

    @Test
    void gradesAndLines() {
        assertThat(HarshadHammers.grade(100, 33)).isEqualTo(HarshadHammers.Grade.TURNED);
        assertThat(HarshadHammers.grade(100, 32)).isEqualTo(HarshadHammers.Grade.SLIPPED);
        for (HarshadHammers.Grade g : HarshadHammers.Grade.values()) {
            assertThat(HarshadHammers.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(HarshadHammers.QUEST_ID).isEqualTo("q_harshad_hammers");
    }
}
