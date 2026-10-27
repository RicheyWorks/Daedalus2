// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class PoliteStacksTest {

    private static List<long[]> bruteRuns(long n) {
        List<long[]> out = new ArrayList<>();
        for (long a = 1; a < n; a++) {
            long s = 0;
            for (long b = a; s < n; b++) {
                s += b;
                if (s == n && b > a) {
                    out.add(new long[] {a, b - a + 1});
                }
            }
        }
        return out;
    }

    @Test
    void matchesRunEnumerationBruteForce() {
        long polite = 0;
        for (long n = 1; n <= 20_000; n++) {
            List<long[]> b = bruteRuns(n);
            assertThat(PoliteStacks.politeness(n)).as("n=%d", n).isEqualTo(b.size());
            assertThat(PoliteStacks.runs(n)).hasSize(b.size());
            assertThat(PoliteStacks.isPolite(n)).isEqualTo(!b.isEmpty());
            if (!b.isEmpty()) {
                polite++;
                if (polite % 101 == 0) {
                    assertThat(PoliteStacks.nthPolite(polite)).isEqualTo(n);
                }
            }
            assertThat(PoliteStacks.countPolite(n)).isEqualTo(polite);
        }
    }

    @Test
    void knownPoliteStacks() {
        List<Long> first = new ArrayList<>();
        for (long k = 1; k <= 12; k++) {
            first.add(PoliteStacks.nthPolite(k));
        }
        assertThat(first).containsExactly(3L, 5L, 6L, 7L, 9L, 10L, 11L, 12L, 13L, 14L, 15L, 17L);
        assertThat(PoliteStacks.politeness(9)).isEqualTo(2);
        assertThat(PoliteStacks.politeness(15)).isEqualTo(3);
        assertThat(PoliteStacks.politeness(945)).isEqualTo(15);
        assertThat(PoliteStacks.runs(9)).containsExactly(new PoliteStacks.Run(4, 2), new PoliteStacks.Run(2, 3));
    }

    @Test
    void runsSumAndCountOnBigStacks() {
        Random r = new Random(496);
        for (int t = 0; t < 40; t++) {
            long n = 1 + (long) (r.nextDouble() * (PoliteStacks.MAX_N - 1));
            List<PoliteStacks.Run> rs = PoliteStacks.runs(n);
            assertThat((long) rs.size()).as("n=%d", n).isEqualTo(PoliteStacks.politeness(n));
            for (PoliteStacks.Run run : rs) {
                long a = run.start();
                long k = run.length();
                assertThat(a).isPositive();
                assertThat(k * a + k * (k - 1) / 2).isEqualTo(n);
            }
            long k = 1 + (long) (r.nextDouble() * (PoliteStacks.countPolite(PoliteStacks.MAX_N) - 1));
            long p = PoliteStacks.nthPolite(k);
            assertThat(PoliteStacks.isPolite(p)).isTrue();
            assertThat(PoliteStacks.countPolite(p)).isEqualTo(k);
        }
    }

    @Test
    void powersOfTwoEdgesAndGuards() {
        for (int i = 0; i < 40; i++) {
            long p = 1L << i;
            assertThat(PoliteStacks.isPolite(p)).isFalse();
            assertThat(PoliteStacks.politeness(p)).isZero();
            assertThat(PoliteStacks.runs(p)).isEmpty();
        }
        assertThat(PoliteStacks.countPolite(0)).isZero();
        assertThat(PoliteStacks.countPolite(2)).isZero();
        assertThat(PoliteStacks.politeness(PoliteStacks.MAX_N)).isEqualTo(12);
        assertThatThrownBy(() -> PoliteStacks.politeness(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PoliteStacks.runs(PoliteStacks.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PoliteStacks.nthPolite(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PoliteStacks.countPolite(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(PoliteStacks.grade(9, 2)).isEqualTo(PoliteStacks.Grade.TURNED);
        assertThat(PoliteStacks.grade(9, 1)).isEqualTo(PoliteStacks.Grade.SLIPPED);
        assertThat(PoliteStacks.grade(8, 0)).isEqualTo(PoliteStacks.Grade.TURNED);
        for (PoliteStacks.Grade g : PoliteStacks.Grade.values()) {
            assertThat(PoliteStacks.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(PoliteStacks.QUEST_ID).isEqualTo("q_polite_stacks");
    }
}
