// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class EliasNotchesTest {

    @Test
    void publishedTables() {
        String[] g = {"1", "010", "011", "00100", "00101", "00110", "00111", "0001000"};
        String[] d = {"1", "0100", "0101", "01100", "01101", "01110", "01111", "00100000"};
        String[] o = {"0", "100", "110", "101000", "101010", "101100", "101110", "1110000"};
        for (int n = 1; n <= 8; n++) {
            assertThat(EliasNotches.encode(EliasNotches.Kind.GAMMA, n)).isEqualTo(g[n - 1]);
            assertThat(EliasNotches.encode(EliasNotches.Kind.DELTA, n)).isEqualTo(d[n - 1]);
            assertThat(EliasNotches.encode(EliasNotches.Kind.OMEGA, n)).isEqualTo(o[n - 1]);
        }
        assertThat(EliasNotches.encode(EliasNotches.Kind.GAMMA, 17)).isEqualTo("000010001");
        assertThat(EliasNotches.encode(EliasNotches.Kind.DELTA, 17)).isEqualTo("001010001");
        assertThat(EliasNotches.encode(EliasNotches.Kind.OMEGA, 17)).isEqualTo("10100100010");
    }

    @Test
    void roundTripsAndLengths() {
        SplittableRandom r = new SplittableRandom(403);
        for (EliasNotches.Kind k : EliasNotches.Kind.values()) {
            for (long n = 1; n <= 5000; n++) {
                assertThat(EliasNotches.encode(k, n)).hasSize(EliasNotches.length(k, n));
            }
            for (int t = 0; t < 100; t++) {
                long[] v = new long[1 + r.nextInt(20)];
                for (int i = 0; i < v.length; i++) {
                    v[i] = 1 + (r.nextLong() >>> (2 + r.nextInt(62)));
                }
                String s = EliasNotches.encodeAll(k, v);
                assertThat(EliasNotches.decodeAll(k, s)).containsExactly(v);
                for (long x : v) {
                    assertThat(EliasNotches.encode(k, x)).hasSize(EliasNotches.length(k, x));
                }
            }
            long big = Long.MAX_VALUE >>> 1;
            assertThat(EliasNotches.decodeAll(k, EliasNotches.encode(k, big))).containsExactly(big);
        }
    }

    @Test
    void grades() {
        String s = EliasNotches.encodeAll(EliasNotches.Kind.DELTA, 3, 17, 1);
        assertThat(EliasNotches.grade(EliasNotches.Kind.DELTA, s, new long[] {3, 17, 1}))
            .isEqualTo(EliasNotches.Grade.READ);
        assertThat(EliasNotches.grade(EliasNotches.Kind.DELTA, s.substring(1), new long[] {3, 17, 1}))
            .isEqualTo(EliasNotches.Grade.SPLINTERED);
        assertThat(EliasNotches.grade(EliasNotches.Kind.GAMMA, "000", new long[] {1}))
            .isEqualTo(EliasNotches.Grade.SPLINTERED);
        assertThat(EliasNotches.forgemasterLine(EliasNotches.Grade.READ)).contains("Forgemaster");
        assertThat(EliasNotches.forgemasterLine(EliasNotches.Grade.SPLINTERED)).contains("splintered");
        assertThat(EliasNotches.QUEST_ID).isEqualTo("q_elias_notches");
    }
}
