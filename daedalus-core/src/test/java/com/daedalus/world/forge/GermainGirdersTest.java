// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class GermainGirdersTest {

    private static boolean trial(long v) {
        if (v < 2) {
            return false;
        }
        for (long d = 2; d * d <= v; d++) {
            if (v % d == 0) {
                return false;
            }
        }
        return true;
    }

    private static int bruteChain(long p) {
        int len = 0;
        long v = p;
        while (trial(v)) {
            len++;
            v = 2 * v + 1;
        }
        return len;
    }

    @Test
    void matchesTrialDivision() {
        int count = 0;
        for (long p = 1; p <= 30_000; p++) {
            boolean g = trial(p) && trial(2 * p + 1);
            if (g) {
                count++;
            }
            assertThat(GermainGirders.isGermain(p)).as("%d", p).isEqualTo(g);
            assertThat(GermainGirders.isSafe(p)).as("safe %d", p)
                    .isEqualTo(p > 3 && trial(p) && (p & 1) != 0 && trial((p - 1) / 2));
            assertThat(GermainGirders.chainLength(p)).as("chain %d", p).isEqualTo(bruteChain(p));
        }
        assertThat(GermainGirders.countGermain(30_000)).isEqualTo(count);
    }

    @Test
    void randomSweepsAndSieve() {
        Random r = new Random(501);
        for (int t = 0; t < 3000; t++) {
            long p = 1 + (r.nextLong() >>> 1) % 1_000_000_000_000L;
            assertThat(GermainGirders.isGermain(p)).as("%d", p).isEqualTo(trial(p) && trial(2 * p + 1));
        }
        for (int t = 0; t < 40; t++) {
            int x = r.nextInt(200_000);
            int c = 0;
            for (int p = 1; p <= x; p++) {
                if (GermainGirders.isGermain(p)) {
                    c++;
                }
            }
            assertThat(GermainGirders.countGermain(x)).as("count %d", x).isEqualTo(c);
        }
    }

    @Test
    void knownGirdersAndChains() {
        List<Long> g = new ArrayList<>();
        List<Long> s = new ArrayList<>();
        for (long p = 1; p <= 300; p++) {
            if (GermainGirders.isGermain(p)) {
                g.add(p);
            }
            if (GermainGirders.isSafe(p)) {
                s.add(p);
            }
        }
        assertThat(g).containsExactly(2L, 3L, 5L, 11L, 23L, 29L, 41L, 53L, 83L, 89L, 113L, 131L, 173L, 179L, 191L,
                233L, 239L, 251L, 281L, 293L);
        assertThat(s).containsExactly(5L, 7L, 11L, 23L, 47L, 59L, 83L, 107L, 167L, 179L, 227L, 263L);
        assertThat(GermainGirders.chainLength(2)).isEqualTo(5);
        assertThat(GermainGirders.chainLength(89)).isEqualTo(6);
        assertThat(GermainGirders.chainLength(1_122_659)).isEqualTo(7);
        assertThat(GermainGirders.countGermain(1_000)).isEqualTo(37);
    }

    @Test
    void edgesAndGuards() {
        assertThat(GermainGirders.isGermain(1)).isFalse();
        assertThat(GermainGirders.isSafe(3)).isFalse();
        assertThat(GermainGirders.isSafe(4)).isFalse();
        assertThat(GermainGirders.chainLength(1)).isZero();
        assertThat(GermainGirders.chainLength(4)).isZero();
        assertThat(GermainGirders.countGermain(0)).isZero();
        assertThat(GermainGirders.countGermain(1)).isZero();
        assertThat(GermainGirders.countGermain(2)).isEqualTo(1);
        assertThat(GermainGirders.chainLength(GermainGirders.MAX_N)).isZero();
        assertThat(GermainGirders.isGermain(GermainGirders.MAX_N)).isFalse();
        assertThatThrownBy(() -> GermainGirders.isGermain(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GermainGirders.isSafe(GermainGirders.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GermainGirders.countGermain(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GermainGirders.countGermain(GermainGirders.SIEVE_MAX + 1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(GermainGirders.grade(89, true)).isEqualTo(GermainGirders.Grade.TURNED);
        assertThat(GermainGirders.grade(7, true)).isEqualTo(GermainGirders.Grade.SLIPPED);
        assertThat(GermainGirders.grade(7, false)).isEqualTo(GermainGirders.Grade.TURNED);
        for (GermainGirders.Grade x : GermainGirders.Grade.values()) {
            assertThat(GermainGirders.forgemasterLine(x)).startsWith("Forgemaster:");
        }
        assertThat(GermainGirders.QUEST_ID).isEqualTo("q_germain_girders");
    }
}
