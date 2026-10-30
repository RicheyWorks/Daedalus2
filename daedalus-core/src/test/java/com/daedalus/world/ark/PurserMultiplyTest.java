// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class PurserMultiplyTest {

    private static String tally(SplittableRandom rnd, int len) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < len; i++) {
            sb.append((char) ('0' + rnd.nextInt(10)));
        }
        return sb.toString();
    }

    @Test
    void bothMatchBigInteger() {
        SplittableRandom rnd = new SplittableRandom(257);
        for (int t = 0; t < 300; t++) {
            String a = tally(rnd, 1 + rnd.nextInt(80));
            String b = tally(rnd, 1 + rnd.nextInt(80));
            String want = new BigInteger(a).multiply(new BigInteger(b)).toString();
            assertThat(PurserMultiply.karatsuba(a, b).product()).as("%s*%s", a, b).isEqualTo(want);
            assertThat(PurserMultiply.schoolbook(a, b).product()).isEqualTo(want);
        }
    }

    @Test
    void karatsubaSavesDigitProductsOnLongTallies() {
        SplittableRandom rnd = new SplittableRandom(7);
        String a = "7" + tally(rnd, 1023);
        String b = "3" + tally(rnd, 1023);
        PurserMultiply.Result k = PurserMultiply.karatsuba(a, b);
        PurserMultiply.Result s = PurserMultiply.schoolbook(a, b);
        assertThat(k.product()).isEqualTo(s.product());
        assertThat(s.digitProducts()).isEqualTo(1024L * 1024);
        assertThat(k.digitProducts()).isLessThan(s.digitProducts() / 5);
        assertThat(PurserMultiply.karatsuba("12", "34").digitProducts()).isEqualTo(3);
    }

    @Test
    void edgesAndQuest() {
        assertThat(PurserMultiply.karatsuba("0", "98765").product()).isEqualTo("0");
        assertThat(PurserMultiply.karatsuba("0007", "006").product()).isEqualTo("42");
        assertThat(PurserMultiply.karatsuba("99999999", "99999999").product()).isEqualTo("9999999800000001");
        assertThat(PurserMultiply.quest("1234", "5678", "7006652")).isTrue();
        assertThat(PurserMultiply.quest("1234", "5678", "7006651")).isFalse();
        assertThat(PurserMultiply.QUEST_ID).isEqualTo("q_purser_long_sum");
        assertThatThrownBy(() -> PurserMultiply.karatsuba("12a", "3")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PurserMultiply.karatsuba("", "3")).isInstanceOf(IllegalArgumentException.class);
    }
}
