// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CheckDigitsTest {

    private static String randomDigits(SplittableRandom rnd, int n) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) {
            sb.append((char) ('0' + rnd.nextInt(10)));
        }
        return sb.toString();
    }

    @Test
    void everySlipAndSwapAudited() {
        SplittableRandom rnd = new SplittableRandom(317);
        for (int t = 0; t < 400; t++) {
            String payload = randomDigits(rnd, rnd.nextInt(1, 10));
            String luhn = payload + CheckDigits.luhnDigit(payload);
            String m11 = payload + CheckDigits.mod11Digit(payload);
            assertThat(CheckDigits.luhnValid(luhn)).isTrue();
            assertThat(CheckDigits.mod11Valid(m11)).isTrue();
            for (int i = 0; i < payload.length(); i++) {
                for (char c = '0'; c <= '9'; c++) {
                    if (c != payload.charAt(i)) {
                        String bad = payload.substring(0, i) + c + payload.substring(i + 1);
                        assertThat(CheckDigits.luhnValid(bad + luhn.charAt(luhn.length() - 1))).isFalse();
                        assertThat(CheckDigits.mod11Valid(bad + m11.charAt(m11.length() - 1))).isFalse();
                    }
                }
            }
            for (int i = 0; i + 1 < luhn.length(); i++) {
                char a = luhn.charAt(i);
                char b = luhn.charAt(i + 1);
                if (a != b) {
                    String sw = luhn.substring(0, i) + b + a + luhn.substring(i + 2);
                    boolean nineZero = (a == '0' && b == '9') || (a == '9' && b == '0');
                    assertThat(CheckDigits.luhnValid(sw)).isEqualTo(nineZero);
                }
            }
            for (int i = 0; i + 1 < payload.length(); i++) {
                char a = payload.charAt(i);
                char b = payload.charAt(i + 1);
                if (a != b) {
                    String sw = payload.substring(0, i) + b + a + payload.substring(i + 2);
                    assertThat(CheckDigits.mod11Valid(sw + m11.charAt(m11.length() - 1))).isFalse();
                }
            }
        }
    }

    @Test
    void knownNumbers() {
        assertThat(CheckDigits.luhnDigit("7992739871")).isEqualTo('3');
        assertThat(CheckDigits.luhnValid("79927398713")).isTrue();
        assertThat(CheckDigits.mod11Digit("030640615")).isEqualTo('2');
        assertThat(CheckDigits.mod11Valid("080442957X")).isTrue();
    }

    @Test
    void questAndBounds() {
        assertThat(CheckDigits.quest("7992739871", '3')).isTrue();
        assertThat(CheckDigits.quest("7992739871", '4')).isFalse();
        assertThat(CheckDigits.QUEST_ID).isEqualTo("q_check_digits");
        assertThatThrownBy(() -> CheckDigits.luhnDigit("")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CheckDigits.mod11Digit("0123456789")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CheckDigits.luhnDigit("12a")).isInstanceOf(IllegalArgumentException.class);
    }
}