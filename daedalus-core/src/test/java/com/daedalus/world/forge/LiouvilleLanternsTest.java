// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class LiouvilleLanternsTest {

    @Test
    void matchesBruteFactorCounts() {
        long run = 0;
        for (int n = 1; n <= 20_000; n++) {
            int big = 0;
            int little = 0;
            int m = n;
            for (int d = 2; d <= m; d++) {
                if (m % d == 0) {
                    little++;
                }
                while (m % d == 0) {
                    m /= d;
                    big++;
                }
            }
            assertThat(LiouvilleLanterns.bigOmega(n)).as("Omega(%d)", n).isEqualTo(big);
            assertThat(LiouvilleLanterns.littleOmega(n)).isEqualTo(little);
            int lam = (big & 1) == 0 ? 1 : -1;
            assertThat(LiouvilleLanterns.lambda(n)).isEqualTo(lam);
            run += lam;
            if (n % 997 == 0 || n == 20_000) {
                assertThat(LiouvilleLanterns.summatory(n)).isEqualTo(run);
            }
        }
        assertThat(LiouvilleLanterns.summatory(0)).isZero();
    }

    @Test
    void knownBalancesAndBigLanterns() {
        long[] want = {1, 0, -2, -14, -94, -288, -530, -842};
        int p = 1;
        for (long w : want) {
            assertThat(LiouvilleLanterns.summatory(p)).as("L(%d)", p).isEqualTo(w);
            p *= 10;
        }
        assertThat(LiouvilleLanterns.bigOmega(1L << 39)).isEqualTo(39);
        assertThat(LiouvilleLanterns.bigOmega(LiouvilleLanterns.MAX_N)).isEqualTo(24);
        assertThat(LiouvilleLanterns.littleOmega(LiouvilleLanterns.MAX_N)).isEqualTo(2);
        assertThat(LiouvilleLanterns.lambda(999_999_999_989L)).isEqualTo(-1);
    }

    @Test
    void gradesAndLines() {
        assertThat(LiouvilleLanterns.grade(12, -1)).isEqualTo(LiouvilleLanterns.Grade.TURNED);
        assertThat(LiouvilleLanterns.grade(12, 1)).isEqualTo(LiouvilleLanterns.Grade.SLIPPED);
        for (LiouvilleLanterns.Grade g : LiouvilleLanterns.Grade.values()) {
            assertThat(LiouvilleLanterns.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(LiouvilleLanterns.QUEST_ID).isEqualTo("q_liouville_lanterns");
    }
}
