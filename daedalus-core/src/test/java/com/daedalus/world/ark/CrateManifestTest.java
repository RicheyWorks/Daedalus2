// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CrateManifestTest {

    private static long trialTotient(long n) {
        long c = 0;
        for (long k = 1; k <= n; k++) {
            if (CrateManifest.gcd(k, n) == 1) {
                c++;
            }
        }
        return c;
    }

    @Test
    void factorsMultiplyBackToPrimes() {
        SplittableRandom rnd = new SplittableRandom(274);
        for (int t = 0; t < 4000; t++) {
            long n = t < 2000 ? t + 1 : rnd.nextLong(1, LanternHandshake.MAX_MOD);
            long prod = 1;
            for (long p : CrateManifest.factor(n)) {
                assertThat(BigInteger.valueOf(p).isProbablePrime(40)).as("n=%d p=%d", n, p).isTrue();
                prod *= p;
            }
            assertThat(prod).isEqualTo(n);
        }
    }

    @Test
    void hardSemiprimesAndPrimePowers() {
        assertThat(CrateManifest.factor(55_103L * 55_109L)).containsExactly(55_103L, 55_109L);
        assertThat(CrateManifest.factor(46_337L * 46_337L)).containsExactly(46_337L, 46_337L);
        assertThat(CrateManifest.factor(1L << 31)).hasSize(31).containsOnly(2L);
        assertThat(CrateManifest.factor(3_037_000_493L)).containsExactly(3_037_000_493L);
        assertThat(CrateManifest.factor(1)).isEmpty();
        assertThat(CrateManifest.factor(17L * 17 * 19 * 23 * 23 * 29)).containsExactly(17L, 17L, 19L, 23L, 23L, 29L);
    }

    @Test
    void totientAndDivisors() {
        for (long n = 1; n <= 600; n++) {
            assertThat(CrateManifest.totient(n)).as("n=%d", n).isEqualTo(trialTotient(n));
            long d = 0;
            for (long k = 1; k <= n; k++) {
                if (n % k == 0) {
                    d++;
                }
            }
            assertThat(CrateManifest.divisorCount(n)).isEqualTo(d);
        }
        assertThat(CrateManifest.totient(2_147_483_647L)).isEqualTo(2_147_483_646L);
    }

    @Test
    void questAndBounds() {
        assertThat(CrateManifest.quest(360, List.of(5L, 2L, 3L, 2L, 3L, 2L))).isTrue();
        assertThat(CrateManifest.quest(360, List.of(4L, 2L, 9L, 5L))).isFalse();
        assertThat(CrateManifest.QUEST_ID).isEqualTo("q_crate_manifest");
        assertThatThrownBy(() -> CrateManifest.factor(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrateManifest.factor(LanternHandshake.MAX_MOD)).isInstanceOf(IllegalArgumentException.class);
    }
}
