// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class HammerCadenceTest {

    @Test
    void matchesDoublingConstruction() {
        int len = 1 << 14;
        int[] t = HammerCadence.prefix(len);
        long ones = 0;
        for (int n = 0; n < len; n++) {
            assertThat(HammerCadence.countOnes(n)).isEqualTo(ones);
            assertThat(HammerCadence.striker(n)).isEqualTo(t[n]);
            ones += t[n];
        }
        assertThat(HammerCadence.prefix(13)).containsExactly(0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0);
        for (int k = 1; k <= 12; k++) {
            long[][] c = HammerCadence.prouhet(k);
            assertThat(HammerCadence.powerSumsAgree(c[0], c[1], k - 1)).isTrue();
            assertThat(HammerCadence.powerSumsAgree(c[0], c[1], k)).isFalse();
        }
    }

    @Test
    void knownValues() {
        assertThat(HammerCadence.striker(0)).isZero();
        assertThat(HammerCadence.striker(7)).isOne();
        assertThat(HammerCadence.striker(Long.MAX_VALUE)).isOne();
        assertThat(HammerCadence.countOnes(1_000_000_000_001L)).isEqualTo(500_000_000_001L);
        long[][] c = HammerCadence.prouhet(3);
        assertThat(c[0]).containsExactly(0, 3, 5, 6);
        assertThat(c[1]).containsExactly(1, 2, 4, 7);
    }

    @Test
    void grades() {
        long[][] c = HammerCadence.prouhet(4);
        assertThat(HammerCadence.grade(c[0], c[1], 3)).isEqualTo(HammerCadence.Grade.FAIR);
        assertThat(HammerCadence.grade(new long[] {0, 1}, new long[] {2, 3}, 1))
            .isEqualTo(HammerCadence.Grade.LOPSIDED);
        assertThat(HammerCadence.forgemasterLine(HammerCadence.Grade.FAIR)).contains("Forgemaster");
        assertThat(HammerCadence.forgemasterLine(HammerCadence.Grade.LOPSIDED)).contains("lopsided");
        assertThat(HammerCadence.QUEST_ID).isEqualTo("q_hammer_cadence");
    }
}
