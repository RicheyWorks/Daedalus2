// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class SmithStampsTest {

    private static boolean bruteSmith(long n) {
        if (n < 4) {
            return false;
        }
        long m = n;
        int fs = 0;
        int factors = 0;
        for (long d = 2; d <= m; d++) {
            while (m % d == 0) {
                long x = d;
                while (x > 0) {
                    fs += (int) (x % 10);
                    x /= 10;
                }
                m /= d;
                factors++;
            }
        }
        int ds = 0;
        for (long x = n; x > 0; x /= 10) {
            ds += (int) (x % 10);
        }
        return factors > 1 && fs == ds;
    }

    @Test
    void checksAndCountsMatchBruteForce() {
        long run = 0;
        for (int n = 1; n <= 30_000; n++) {
            boolean want = bruteSmith(n);
            assertThat(SmithStamps.isSmith(n)).as("n=%d", n).isEqualTo(want);
            if (want) {
                run++;
            }
            if (n % 751 == 0 || n < 60) {
                assertThat(SmithStamps.countSmith(n)).isEqualTo(run);
            }
        }
    }

    @Test
    void knownSmithNumbersAndCounts() {
        List<Long> first = new ArrayList<>();
        for (long n = 1; first.size() < 12; n++) {
            if (SmithStamps.isSmith(n)) {
                first.add(n);
            }
        }
        assertThat(first).containsExactly(4L, 22L, 27L, 58L, 85L, 94L, 121L, 166L, 202L, 265L, 274L, 319L);
        assertThat(SmithStamps.countSmith(100)).isEqualTo(6);
        assertThat(SmithStamps.countSmith(1000)).isEqualTo(49);
        assertThat(SmithStamps.countSmith(10_000)).isEqualTo(376);
        assertThat(SmithStamps.isSmith(4_937_775)).isTrue();
    }

    @Test
    void sieveAgreesWithSingleChecksOnRandomWindows() {
        Random r = new Random(467);
        for (int t = 0; t < 6; t++) {
            int lo = 100_000 + r.nextInt(2_000_000);
            int hi = lo + r.nextInt(3000);
            long c = SmithStamps.countSmith(lo);
            for (long n = lo + 1; n <= hi; n++) {
                if (SmithStamps.isSmith(n)) {
                    c++;
                }
            }
            assertThat(SmithStamps.countSmith(hi)).isEqualTo(c);
        }
    }

    @Test
    void edgesAndBigStamps() {
        assertThat(SmithStamps.countSmith(0)).isZero();
        assertThat(SmithStamps.countSmith(3)).isZero();
        assertThat(SmithStamps.isSmith(1)).isFalse();
        assertThat(SmithStamps.isSmith(2)).isFalse();
        assertThat(SmithStamps.factorDigitSum(1)).isZero();
        assertThat(SmithStamps.isSmith(999_999_999_989L)).isFalse();
        long big = 2L * 499_999_999_979L;
        assertThat(SmithStamps.isSmith(big)).isEqualTo(SmithStamps.digitSum(big) == SmithStamps.factorDigitSum(big));
        assertThat(SmithStamps.factorDigitSum(SmithStamps.MAX_N)).isEqualTo(12 * 2 + 12 * 5);
        assertThatThrownBy(() -> SmithStamps.isSmith(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SmithStamps.countSmith(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SmithStamps.digitSum(-5)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(SmithStamps.grade(22, true)).isEqualTo(SmithStamps.Grade.TURNED);
        assertThat(SmithStamps.grade(23, true)).isEqualTo(SmithStamps.Grade.SLIPPED);
        assertThat(SmithStamps.grade(23, false)).isEqualTo(SmithStamps.Grade.TURNED);
        for (SmithStamps.Grade g : SmithStamps.Grade.values()) {
            assertThat(SmithStamps.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(SmithStamps.QUEST_ID).isEqualTo("q_smith_stamps");
    }
}
