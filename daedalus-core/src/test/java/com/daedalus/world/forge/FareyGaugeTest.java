// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class FareyGaugeTest {

    private static long gcd(long x, long y) {
        return y == 0 ? x : gcd(y, x % y);
    }

    private static List<long[]> brute(int n) {
        List<long[]> l = new ArrayList<>();
        for (int q = 1; q <= n; q++) {
            for (int p = 0; p <= q; p++) {
                if (gcd(p, q) == 1) {
                    l.add(new long[] {p, q});
                }
            }
        }
        l.sort((x, y) -> Long.compare(x[0] * y[1], y[0] * x[1]));
        return l;
    }

    @Test
    void matchesBruteForce() {
        for (int n = 1; n <= 40; n++) {
            List<long[]> want = brute(n);
            int[][] got = FareyGauge.sequence(n);
            assertThat(got.length).isEqualTo(want.size());
            assertThat(FareyGauge.count(n)).isEqualTo(want.size());
            for (int i = 0; i < got.length; i++) {
                assertThat(got[i][0]).isEqualTo((int) want.get(i)[0]);
                assertThat(got[i][1]).isEqualTo((int) want.get(i)[1]);
                assertThat(FareyGauge.rank(got[i][0], got[i][1], n)).isEqualTo(i + 1L);
                if (i > 0) {
                    assertThat(FareyGauge.neighbours(got[i - 1][0], got[i - 1][1], got[i][0], got[i][1])).isTrue();
                }
            }
        }
        for (long s = 0; s < 50; s++) {
            int n = FareyGauge.gauge(s);
            assertThat(n).isBetween(1, 60);
            assertThat(FareyGauge.sequence(n).length).isEqualTo(brute(n).size());
        }
    }

    @Test
    void knownValues() {
        assertThat(FareyGauge.count(8)).isEqualTo(23);
        assertThat(FareyGauge.count(1)).isEqualTo(2);
        assertThat(FareyGauge.rank(1, 2, 8)).isEqualTo(12);
        assertThat(FareyGauge.rank(1, 3, 5)).isEqualTo(4);
        assertThat(FareyGauge.neighbours(1, 3, 2, 5)).isTrue();
        assertThat(FareyGauge.neighbours(1, 3, 1, 2)).isTrue();
        assertThat(FareyGauge.neighbours(1, 4, 1, 2)).isFalse();
    }

    @Test
    void grades() {
        assertThat(FareyGauge.grade(8, 23)).isEqualTo(FareyGauge.Grade.TRUE);
        assertThat(FareyGauge.grade(8, 22)).isEqualTo(FareyGauge.Grade.BENT);
        assertThat(FareyGauge.forgemasterLine(FareyGauge.Grade.TRUE)).contains("Forgemaster");
        assertThat(FareyGauge.forgemasterLine(FareyGauge.Grade.BENT)).contains("bent");
        assertThat(FareyGauge.QUEST_ID).isEqualTo("q_farey_gauge");
    }
}
