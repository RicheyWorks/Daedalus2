// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class AchillesRivetsTest {

    /** Returns {powerful, perfect power} by plain factorization and root search. */
    private static boolean[] brute(long n) {
        boolean powerful = true;
        long m = n;
        for (long d = 2; d <= m; d++) {
            int e = 0;
            while (m % d == 0) {
                m /= d;
                e++;
            }
            if (e == 1) {
                powerful = false;
            }
        }
        boolean perfect = n == 1;
        for (int k = 2; k < 64 && !perfect; k++) {
            long r = Math.round(Math.pow(n, 1.0 / k));
            for (long x = Math.max(2, r - 1); x <= r + 1; x++) {
                long v = 1;
                for (int i = 0; i < k && v <= n; i++) {
                    v *= x;
                }
                if (v == n) {
                    perfect = true;
                }
            }
        }
        return new boolean[] {powerful, perfect};
    }

    @Test
    void checksAndCountsMatchBruteForce() {
        long pw = 0;
        long pp = 0;
        long ach = 0;
        for (int n = 1; n <= 200_000; n++) {
            boolean[] b = brute(n);
            assertThat(AchillesRivets.isPowerful(n)).as("powerful %d", n).isEqualTo(b[0]);
            assertThat(AchillesRivets.isPerfectPower(n)).as("perfect %d", n).isEqualTo(b[1]);
            boolean a = b[0] && !b[1];
            assertThat(AchillesRivets.isAchilles(n)).as("achilles %d", n).isEqualTo(a);
            pw += b[0] ? 1 : 0;
            pp += b[1] ? 1 : 0;
            ach += a ? 1 : 0;
            if (n % 1009 == 0 || n < 80) {
                assertThat(AchillesRivets.countPowerful(n)).isEqualTo(pw);
                assertThat(AchillesRivets.countPerfectPowers(n)).isEqualTo(pp);
                assertThat(AchillesRivets.countAchilles(n)).isEqualTo(ach);
            }
        }
    }

    @Test
    void knownAchillesRivets() {
        List<Long> first = new ArrayList<>();
        for (long n = 1; first.size() < 20; n++) {
            if (AchillesRivets.isAchilles(n)) {
                first.add(n);
            }
        }
        assertThat(first).containsExactly(72L, 108L, 200L, 288L, 392L, 432L, 500L, 648L, 675L, 800L, 864L, 968L,
                972L, 1125L, 1152L, 1323L, 1352L, 1372L, 1568L, 1800L);
        assertThat(AchillesRivets.countAchilles(1800)).isEqualTo(20);
        assertThat(AchillesRivets.countAchilles(71)).isZero();
    }

    @Test
    void countsAgreeWithFilterOnRandomWindows() {
        Random r = new Random(477);
        for (int t = 0; t < 6; t++) {
            long lo = 10_000_000L + (long) (r.nextDouble() * 90_000_000L);
            long hi = lo + r.nextInt(3000);
            long c = AchillesRivets.countAchilles(lo);
            long p = AchillesRivets.countPowerful(lo);
            for (long n = lo + 1; n <= hi; n++) {
                c += AchillesRivets.isAchilles(n) ? 1 : 0;
                p += AchillesRivets.isPowerful(n) ? 1 : 0;
            }
            assertThat(AchillesRivets.countAchilles(hi)).isEqualTo(c);
            assertThat(AchillesRivets.countPowerful(hi)).isEqualTo(p);
        }
        for (long b = 2; b <= 40; b++) {
            for (int k = 2; Math.pow(b, k) <= 1e12; k++) {
                long v = 1;
                for (int i = 0; i < k; i++) {
                    v *= b;
                }
                assertThat(AchillesRivets.isPerfectPower(v)).isTrue();
                assertThat(AchillesRivets.isAchilles(v)).isFalse();
            }
        }
    }

    @Test
    void edgesAndBigRivets() {
        assertThat(AchillesRivets.isAchilles(1)).isFalse();
        assertThat(AchillesRivets.isPowerful(1)).isTrue();
        assertThat(AchillesRivets.countAchilles(0)).isZero();
        assertThat(AchillesRivets.countPowerful(0)).isZero();
        assertThat(AchillesRivets.isPowerful(999_999_999_989L)).isFalse();
        assertThat(AchillesRivets.isPerfectPower(AchillesRivets.MAX_N)).isTrue();
        assertThat(AchillesRivets.isAchilles(999_983L * 999_983L)).isFalse();
        assertThat(AchillesRivets.isAchilles(8L * 100_003L * 100_003L)).isTrue();
        assertThat(AchillesRivets.countPowerful(AchillesRivets.MAX_N))
                .isGreaterThan(AchillesRivets.countPerfectPowers(AchillesRivets.MAX_N));
        assertThat(AchillesRivets.countPerfectPowers(AchillesRivets.MAX_N)).isGreaterThan(1_000_000L);
        assertThatThrownBy(() -> AchillesRivets.isAchilles(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> AchillesRivets.isPowerful(AchillesRivets.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> AchillesRivets.countAchilles(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(AchillesRivets.grade(72, true)).isEqualTo(AchillesRivets.Grade.TURNED);
        assertThat(AchillesRivets.grade(36, true)).isEqualTo(AchillesRivets.Grade.SLIPPED);
        assertThat(AchillesRivets.grade(36, false)).isEqualTo(AchillesRivets.Grade.TURNED);
        for (AchillesRivets.Grade g : AchillesRivets.Grade.values()) {
            assertThat(AchillesRivets.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(AchillesRivets.QUEST_ID).isEqualTo("q_achilles_rivets");
    }
}
