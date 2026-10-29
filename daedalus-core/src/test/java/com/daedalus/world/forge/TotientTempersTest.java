// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class TotientTempersTest {

    private static long gcd(long a, long b) {
        return b == 0 ? a : gcd(b, a % b);
    }

    private static long brutePhi(long n) {
        long c = 0;
        for (long k = 1; k <= n; k++) {
            if (gcd(k, n) == 1) {
                c++;
            }
        }
        return c;
    }

    @Test
    void phiMatchesGcdCountAndChainsEndAtOne() {
        for (long n = 1; n <= 3000; n++) {
            long p = brutePhi(n);
            assertThat(TotientTempers.phi(n)).as("%d", n).isEqualTo(p);
            List<Long> c = TotientTempers.chain(n);
            if (n == 1) {
                assertThat(c).isEmpty();
            } else {
                assertThat(c.get(0)).isEqualTo(p);
                assertThat(c.get(c.size() - 1)).isEqualTo(1L);
                for (int i = 1; i < c.size(); i++) {
                    assertThat(c.get(i)).isLessThan(c.get(i - 1));
                }
            }
        }
    }

    @Test
    void sieveMatchesPerValueChains() {
        List<Long> want = new ArrayList<>();
        for (long n = 1; n <= 100_000; n++) {
            if (TotientTempers.isPerfectTemper(n)) {
                want.add(n);
            }
        }
        assertThat(TotientTempers.tempersUpTo(100_000)).isEqualTo(want);
        Random r = new Random(503);
        for (int t = 0; t < 30; t++) {
            int x = r.nextInt(100_000);
            List<Long> part = new ArrayList<>();
            for (long v : want) {
                if (v <= x) {
                    part.add(v);
                }
            }
            assertThat(TotientTempers.tempersUpTo(x)).isEqualTo(part);
        }
    }

    @Test
    void knownTempersAndPowersOfThree() {
        assertThat(TotientTempers.tempersUpTo(6000)).containsExactly(3L, 9L, 15L, 27L, 39L, 81L, 111L, 183L, 243L,
                255L, 327L, 363L, 471L, 729L, 2187L, 2199L, 3063L, 4359L, 4375L, 5571L);
        long p = 3;
        while (p <= TotientTempers.MAX_N) {
            assertThat(TotientTempers.isPerfectTemper(p)).as("3-power %d", p).isTrue();
            p *= 3;
        }
        assertThat(TotientTempers.chain(15)).containsExactly(8L, 4L, 2L, 1L);
        assertThat(TotientTempers.chainSum(15)).isEqualTo(15);
    }

    @Test
    void randomLargeSweeps() {
        Random r = new Random(5031);
        for (int t = 0; t < 300; t++) {
            long n = 1 + (r.nextLong() >>> 1) % TotientTempers.MAX_N;
            long ph = TotientTempers.phi(n);
            assertThat(ph).isBetween(1L, n);
            assertThat(TotientTempers.chainSum(n)).isEqualTo(ph + (ph == 1 ? 0 : TotientTempers.chainSum(ph)));
        }
        long q = 999_983L * 1_000_003L;
        assertThat(TotientTempers.phi(q)).isEqualTo(999_982L * 1_000_002L);
        assertThat(TotientTempers.phi(1L << 39)).isEqualTo(1L << 38);
    }

    @Test
    void edgesGuardsAndGrades() {
        assertThat(TotientTempers.phi(1)).isEqualTo(1);
        assertThat(TotientTempers.chainSum(1)).isZero();
        assertThat(TotientTempers.isPerfectTemper(1)).isFalse();
        assertThat(TotientTempers.isPerfectTemper(2)).isFalse();
        assertThat(TotientTempers.tempersUpTo(0)).isEmpty();
        assertThat(TotientTempers.tempersUpTo(2)).isEmpty();
        assertThat(TotientTempers.tempersUpTo(3)).containsExactly(3L);
        assertThatThrownBy(() -> TotientTempers.phi(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TotientTempers.chain(TotientTempers.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TotientTempers.tempersUpTo(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TotientTempers.tempersUpTo(TotientTempers.SIEVE_MAX + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(TotientTempers.grade(39, true)).isEqualTo(TotientTempers.Grade.TURNED);
        assertThat(TotientTempers.grade(40, true)).isEqualTo(TotientTempers.Grade.SLIPPED);
        assertThat(TotientTempers.grade(40, false)).isEqualTo(TotientTempers.Grade.TURNED);
        for (TotientTempers.Grade g : TotientTempers.Grade.values()) {
            assertThat(TotientTempers.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(TotientTempers.QUEST_ID).isEqualTo("q_totient_tempers");
    }
}
