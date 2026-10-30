// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class BosunChantTest {

    private static String bruteNext(String s) {
        StringBuilder sb = new StringBuilder();
        int count = 1;
        for (int i = 1; i <= s.length(); i++) {
            if (i < s.length() && s.charAt(i) == s.charAt(i - 1)) {
                count++;
            } else {
                sb.append(Integer.toString(count)).append(s.charAt(i - 1));
                count = 1;
            }
        }
        return sb.toString();
    }

    @Test
    void forwardMatchesBruteAndKnownLengths() {
        int[] lengths = {1, 2, 2, 4, 6, 6, 8, 10, 14, 20, 26, 34, 46, 62, 78, 102};
        String v = "1";
        for (int k = 0; k < lengths.length; k++) {
            assertThat(BosunChant.verse("1", k)).isEqualTo(v).hasSize(lengths[k]);
            v = bruteNext(v);
        }
        assertThat(BosunChant.verse("1", 39).length()).isEqualTo(63_138);
        assertThat(BosunChant.verse("1", 30)).doesNotContain("4");
    }

    @Test
    void randomVersesRoundTrip() {
        SplittableRandom rnd = new SplittableRandom(332);
        for (int t = 0; t < 20_000; t++) {
            StringBuilder sb = new StringBuilder();
            int runs = rnd.nextInt(1, 12);
            char last = '0';
            for (int r = 0; r < runs; r++) {
                char c;
                do {
                    c = (char) ('1' + rnd.nextInt(rnd.nextBoolean() ? 3 : 9));
                } while (c == last);
                int len = rnd.nextInt(1, 10);
                for (int i = 0; i < len; i++) {
                    sb.append(c);
                }
                last = c;
            }
            String s = sb.toString();
            String n = BosunChant.next(s);
            assertThat(n).isEqualTo(bruteNext(s));
            assertThat(BosunChant.previous(n)).hasValue(s);
        }
    }

    @Test
    void questAndGuards() {
        assertThat(BosunChant.QUEST_ID).isEqualTo("q_bosun_chant");
        assertThat(BosunChant.quest("1211", "111221")).isTrue();
        assertThat(BosunChant.quest("1211", "1112")).isFalse();
        assertThat(BosunChant.previous("111")).isEmpty();
        assertThat(BosunChant.previous("1111")).isEmpty();
        assertThatThrownBy(() -> BosunChant.next("10")).isInstanceOf(IllegalArgumentException.class);
    }
}