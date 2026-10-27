// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class NegabaseDialsTest {

    private static BigInteger eval(String s, int k) {
        BigInteger v = BigInteger.ZERO;
        BigInteger b = BigInteger.valueOf(-k);
        for (char c : s.toCharArray()) {
            v = v.multiply(b).add(BigInteger.valueOf(c - '0'));
        }
        return v;
    }

    @Test
    void matchesBigInteger() {
        SplittableRandom r = new SplittableRandom(418);
        for (int k = 2; k <= 10; k++) {
            for (int t = 0; t < 300; t++) {
                long n = r.nextLong() >> r.nextInt(64);
                if (t == 0) {
                    n = Long.MIN_VALUE;
                } else if (t == 1) {
                    n = Long.MAX_VALUE;
                }
                String s = NegabaseDials.toNegabase(n, k);
                assertThat(eval(s, k)).isEqualTo(BigInteger.valueOf(n));
                assertThat(s.length() == 1 || s.charAt(0) != '0').isTrue();
                assertThat(NegabaseDials.fromNegabase(s, k)).isEqualTo(n);
            }
        }
        for (int t = 0; t < 500; t++) {
            long a = r.nextLong() >> 2;
            long b = r.nextLong() >> 2;
            String sum = NegabaseDials.addNegabinary(NegabaseDials.toNegabase(a, 2), NegabaseDials.toNegabase(b, 2));
            assertThat(sum).isEqualTo(NegabaseDials.toNegabase(a + b, 2));
        }
    }

    @Test
    void knownValues() {
        assertThat(NegabaseDials.toNegabase(6, 2)).isEqualTo("11010");
        assertThat(NegabaseDials.toNegabase(-2, 2)).isEqualTo("10");
        assertThat(NegabaseDials.toNegabase(2, 2)).isEqualTo("110");
        assertThat(NegabaseDials.toNegabase(0, 7)).isEqualTo("0");
        assertThat(NegabaseDials.toNegabase(-1, 10)).isEqualTo("19");
        assertThat(NegabaseDials.addNegabinary("1", "1")).isEqualTo("110");
        assertThat(NegabaseDials.addNegabinary("11", "1")).isEqualTo("0");
        assertThatThrownBy(() -> NegabaseDials.fromNegabase("12", 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> NegabaseDials.fromNegabase("1".repeat(80), 2))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void grades() {
        assertThat(NegabaseDials.grade(6, 2, "11010")).isEqualTo(NegabaseDials.Grade.TRUE);
        assertThat(NegabaseDials.grade(6, 2, "110")).isEqualTo(NegabaseDials.Grade.SKEWED);
        assertThat(NegabaseDials.grade(6, 2, "x")).isEqualTo(NegabaseDials.Grade.SKEWED);
        assertThat(NegabaseDials.forgemasterLine(NegabaseDials.Grade.TRUE)).contains("Forgemaster");
        assertThat(NegabaseDials.forgemasterLine(NegabaseDials.Grade.SKEWED)).contains("skewed");
        assertThat(NegabaseDials.QUEST_ID).isEqualTo("q_negabase_dials");
    }
}
