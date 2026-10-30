// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigInteger;
import java.util.Random;
import org.junit.jupiter.api.Test;

class DedekindDialsTest {

    private static String brute(long h, long k) {
        long acc = 0;
        for (long r = 1; r < k; r++) {
            long m = Math.floorMod(h * r, k);
            if (m != 0) {
                acc += (2 * r - k) * (2 * m - k);
            }
        }
        BigInteger n = BigInteger.valueOf(acc);
        BigInteger d = BigInteger.valueOf(4 * k * k);
        BigInteger g = n.gcd(d);
        return g.signum() == 0 ? "0/1" : n.divide(g) + "/" + d.divide(g);
    }

    private static String fast(long h, long k) {
        BigInteger[] s = DedekindDials.dedekindSum(h, k);
        return s[0] + "/" + s[1];
    }

    @Test
    void matchesSawtoothDefinition() {
        for (long k = 1; k <= 180; k++) {
            for (long h = -30; h <= 2 * k; h++) {
                assertThat(fast(h, k)).as("s(%d,%d)", h, k).isEqualTo(brute(h, k));
            }
        }
        Random r = new Random(454);
        for (int t = 0; t < 200; t++) {
            long k = 1 + r.nextInt(5000);
            long h = r.nextInt(100_000) - 50_000;
            assertThat(fast(h, k)).isEqualTo(brute(h, k));
        }
    }

    @Test
    void reciprocityAndHugeDials() {
        assertThat(fast(1, 3)).isEqualTo("1/18");
        assertThat(fast(1, 5)).isEqualTo("1/5");
        Random r = new Random(4540);
        for (int t = 0; t < 200; t++) {
            long h = 1 + (r.nextLong() >>> 2);
            long k = 1 + (r.nextLong() >>> 2);
            if (BigInteger.valueOf(h).gcd(BigInteger.valueOf(k)).intValue() != 1) {
                continue;
            }
            BigInteger[] a = DedekindDials.dedekindSum(h, k);
            BigInteger[] b = DedekindDials.dedekindSum(k, h);
            BigInteger bh = BigInteger.valueOf(h);
            BigInteger bk = BigInteger.valueOf(k);
            BigInteger hk = bh.multiply(bk);
            BigInteger lhs = a[0].multiply(b[1]).add(b[0].multiply(a[1])).multiply(hk.multiply(BigInteger.valueOf(12)));
            BigInteger rhs = bh.multiply(bh).add(bk.multiply(bk)).add(BigInteger.ONE).subtract(hk.multiply(
                BigInteger.valueOf(3))).multiply(a[1].multiply(b[1]));
            assertThat(lhs).isEqualTo(rhs);
            BigInteger[] neg = DedekindDials.dedekindSum(-h, k);
            assertThat(neg[0]).isEqualTo(a[0].negate());
        }
        assertThat(fast(1, Long.MAX_VALUE)).isNotEqualTo("0/1");
    }

    @Test
    void gradesAndLines() {
        assertThat(DedekindDials.grade(1, 3, 2, 36)).isEqualTo(DedekindDials.Grade.TURNED);
        assertThat(DedekindDials.grade(1, 3, 1, 12)).isEqualTo(DedekindDials.Grade.SLIPPED);
        assertThat(DedekindDials.grade(1, 3, 1, 0)).isEqualTo(DedekindDials.Grade.SLIPPED);
        for (DedekindDials.Grade g : DedekindDials.Grade.values()) {
            assertThat(DedekindDials.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(DedekindDials.QUEST_ID).isEqualTo("q_dedekind_dials");
    }
}
