// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Random;
import org.junit.jupiter.api.Test;

class SubsetSmelterTest {

    @Test
    void transformsMatchBruteForce() {
        Random r = new Random(459);
        for (int n = 0; n <= 9; n++) {
            int size = 1 << n;
            long[] f = new long[size];
            long[] b = new long[size];
            for (int s = 0; s < size; s++) {
                f[s] = r.nextInt(2001) - 1000;
                b[s] = r.nextInt(2001) - 1000;
            }
            long[] z = SubsetSmelter.zeta(f);
            long[] up = SubsetSmelter.supersetZeta(f);
            long[] conv = SubsetSmelter.subsetConvolution(f, b);
            for (int s = 0; s < size; s++) {
                long sub = 0;
                long sup = 0;
                long c = 0;
                for (int t = 0; t < size; t++) {
                    if ((t & s) == t) {
                        sub += f[t];
                        c += f[t] * b[s ^ t];
                    }
                    if ((t & s) == s) {
                        sup += f[t];
                    }
                }
                assertThat(z[s]).isEqualTo(sub);
                assertThat(up[s]).isEqualTo(sup);
                assertThat(conv[s]).as("n=%d s=%d", n, s).isEqualTo(c);
            }
            assertThat(SubsetSmelter.mobius(z)).containsExactly(f);
        }
    }

    @Test
    void largeTablesAndCounting() {
        int n = SubsetSmelter.MAX_BITS;
        long[] ones = new long[1 << n];
        java.util.Arrays.fill(ones, 1);
        long[] z = SubsetSmelter.zeta(ones);
        for (int s = 0; s < z.length; s += 4099) {
            assertThat(z[s]).isEqualTo(1L << Integer.bitCount(s));
        }
        long[] one = new long[1 << 12];
        java.util.Arrays.fill(one, 1);
        long[] c = SubsetSmelter.subsetConvolution(one, one);
        assertThat(c[(1 << 12) - 1]).isEqualTo(1L << 12);
        assertThatThrownBy(() -> SubsetSmelter.zeta(new long[3])).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        long[] f = {1, 2, 3, 4};
        assertThat(SubsetSmelter.grade(f, 3, 10)).isEqualTo(SubsetSmelter.Grade.TURNED);
        assertThat(SubsetSmelter.grade(f, 3, 4)).isEqualTo(SubsetSmelter.Grade.SLIPPED);
        assertThat(SubsetSmelter.grade(f, 7, 10)).isEqualTo(SubsetSmelter.Grade.SLIPPED);
        for (SubsetSmelter.Grade g : SubsetSmelter.Grade.values()) {
            assertThat(SubsetSmelter.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(SubsetSmelter.QUEST_ID).isEqualTo("q_subset_smelter");
    }
}
