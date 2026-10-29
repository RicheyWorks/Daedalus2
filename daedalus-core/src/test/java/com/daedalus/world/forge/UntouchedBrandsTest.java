// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class UntouchedBrandsTest {

    private static long bruteS(long m) {
        long s = 0;
        for (long d = 1; d < m; d++) {
            if (m % d == 0) {
                s += d;
            }
        }
        return s;
    }

    @Test
    void matchesTrialDivisionBruteForce() {
        int n = 300;
        long[] w = new long[n + 1];
        for (long m = 1; m <= (long) n * n; m++) {
            long s = 1;
            for (long d = 2; d * d <= m; d++) {
                if (m % d == 0) {
                    s += d + (d != m / d ? m / d : 0);
                }
            }
            if (m == 1) {
                s = 0;
            }
            if (s >= 1 && s <= n && w[(int) s] == 0) {
                w[(int) s] = m;
            }
        }
        List<Long> want = new ArrayList<>();
        for (int b = 1; b <= n; b++) {
            assertThat(UntouchedBrands.witness(b)).as("brand %d", b).isEqualTo(w[b] == 0 ? -1 : w[b]);
            if (w[b] == 0) {
                want.add((long) b);
            }
        }
        assertThat(UntouchedBrands.untouchedUpTo(n)).isEqualTo(want);
        for (long m = 1; m <= 3000; m++) {
            assertThat(UntouchedBrands.aliquotSum(m)).as("s(%d)", m).isEqualTo(bruteS(m));
        }
    }

    @Test
    void knownUntouchedBrands() {
        assertThat(UntouchedBrands.untouchedUpTo(290)).containsExactly(2L, 5L, 52L, 88L, 96L, 120L, 124L, 146L,
                162L, 188L, 206L, 210L, 216L, 238L, 246L, 248L, 262L, 268L, 276L, 288L, 290L);
        assertThat(UntouchedBrands.witness(1)).isEqualTo(2);
        assertThat(UntouchedBrands.witness(6)).isEqualTo(6);
        assertThat(UntouchedBrands.witness(28)).isEqualTo(28);
    }

    @Test
    void everyTouchedBrandHasAWitness() {
        int odd = 0;
        for (long b = 1; b <= UntouchedBrands.MAX_BRAND; b++) {
            long m = UntouchedBrands.witness(b);
            if (m > 0) {
                assertThat(UntouchedBrands.aliquotSum(m)).as("brand %d", b).isEqualTo(b);
                assertThat(m).isLessThanOrEqualTo(Math.max(2, b * b));
            } else if (b % 2 != 0) {
                odd++;
                assertThat(b).isEqualTo(5);
            }
        }
        assertThat(odd).isEqualTo(1);
        Random r = new Random(483);
        for (int t = 0; t < 200; t++) {
            long m = 2 + (long) (r.nextDouble() * 1_000_000);
            assertThat(UntouchedBrands.aliquotSum(m)).isEqualTo(bruteS(m));
        }
    }

    @Test
    void edgesAndGuards() {
        assertThat(UntouchedBrands.aliquotSum(1)).isZero();
        assertThat(UntouchedBrands.aliquotSum(999_999_999_989L)).isEqualTo(1);
        assertThat(UntouchedBrands.aliquotSum(UntouchedBrands.MAX_M)).isGreaterThan(UntouchedBrands.MAX_M);
        assertThat(UntouchedBrands.untouchedUpTo(0)).isEmpty();
        assertThat(UntouchedBrands.untouchedUpTo(1)).isEmpty();
        assertThatThrownBy(() -> UntouchedBrands.aliquotSum(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> UntouchedBrands.witness(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> UntouchedBrands.witness(UntouchedBrands.MAX_BRAND + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> UntouchedBrands.untouchedUpTo(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(UntouchedBrands.grade(52, true)).isEqualTo(UntouchedBrands.Grade.TURNED);
        assertThat(UntouchedBrands.grade(6, true)).isEqualTo(UntouchedBrands.Grade.SLIPPED);
        assertThat(UntouchedBrands.grade(6, false)).isEqualTo(UntouchedBrands.Grade.TURNED);
        for (UntouchedBrands.Grade g : UntouchedBrands.Grade.values()) {
            assertThat(UntouchedBrands.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(UntouchedBrands.QUEST_ID).isEqualTo("q_untouched_brands");
    }
}
