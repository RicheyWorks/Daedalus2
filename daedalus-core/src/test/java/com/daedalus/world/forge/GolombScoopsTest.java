// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class GolombScoopsTest {

    @Test
    void publishedTables() {
        String[] m3 = {"00", "010", "011", "100", "1010", "1011", "1100"};
        String[] m5 = {"000", "001", "010", "0110", "0111", "1000", "1001"};
        for (int n = 0; n < m3.length; n++) {
            assertThat(GolombScoops.encode(n, 3)).isEqualTo(m3[n]);
            assertThat(GolombScoops.encode(n, 5)).isEqualTo(m5[n]);
        }
        assertThat(GolombScoops.encode(4, 1)).isEqualTo("11110");
        assertThat(GolombScoops.rice(9, 2)).isEqualTo("11001");
    }

    @Test
    void roundTripsLengthsAndBestM() {
        for (long m = 1; m <= 40; m++) {
            for (long n = 0; n < 300; n++) {
                assertThat(GolombScoops.encode(n, m)).hasSize((int) GolombScoops.length(n, m));
                if (Long.bitCount(m) == 1) {
                    int k = Long.numberOfTrailingZeros(m);
                    String low = k == 0 ? "" : Long.toBinaryString((n & (m - 1)) | m).substring(1);
                    String want = "1".repeat((int) (n >> k)) + "0" + low;
                    assertThat(GolombScoops.rice(n, k)).isEqualTo(want);
                }
            }
        }
        for (long seed = 0; seed < 30; seed++) {
            long[] log = GolombScoops.scoopLog(seed, 200, 0.05 + seed * 0.02);
            long m = 1 + seed % 17;
            assertThat(GolombScoops.decodeAll(GolombScoops.encodeAll(m, log), m)).containsExactly(log);
            long best = GolombScoops.bestM(log, 64);
            int bestLen = GolombScoops.encodeAll(best, log).length();
            for (long mm = 1; mm <= 64; mm++) {
                assertThat(GolombScoops.encodeAll(mm, log).length()).isGreaterThanOrEqualTo(bestLen);
            }
        }
    }

    @Test
    void grades() {
        String s = GolombScoops.encodeAll(5, 3, 0, 12);
        assertThat(GolombScoops.grade(s, 5, new long[] {3, 0, 12})).isEqualTo(GolombScoops.Grade.PACKED);
        assertThat(GolombScoops.grade(s + "1", 5, new long[] {3, 0, 12})).isEqualTo(GolombScoops.Grade.SPILLED);
        assertThat(GolombScoops.forgemasterLine(GolombScoops.Grade.PACKED)).contains("Forgemaster");
        assertThat(GolombScoops.forgemasterLine(GolombScoops.Grade.SPILLED)).contains("spilled");
        assertThat(GolombScoops.QUEST_ID).isEqualTo("q_golomb_scoops");
    }
}
