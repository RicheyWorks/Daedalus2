// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

class TallyChantTest {

    private static final Pattern RUN = Pattern.compile("(\\d)\\1*");

    private static String naive(String s) {
        Matcher m = RUN.matcher(s);
        StringBuilder sb = new StringBuilder();
        while (m.find()) {
            sb.append(m.group().length()).append(m.group(1));
        }
        return sb.toString();
    }

    @Test
    void matchesNaiveReference() {
        SplittableRandom r = new SplittableRandom(397);
        for (int t = 0; t < 300; t++) {
            StringBuilder sb = new StringBuilder();
            int len = r.nextInt(40);
            for (int i = 0; i < len; i++) {
                sb.append((char) ('0' + r.nextInt(r.nextBoolean() ? 3 : 10)));
            }
            String s = sb.toString();
            String d = TallyChant.describe(s);
            assertThat(d).isEqualTo(naive(s));
            if (noLongRuns(s)) {
                assertThat(TallyChant.undescribe(d)).isEqualTo(s);
            }
        }
        String s = "1";
        for (int n = 1; n <= 40; n++) {
            assertThat(TallyChant.nth("1", n)).isEqualTo(s);
            assertThat(s.chars().allMatch(c -> c >= '1' && c <= '3')).isTrue();
            s = naive(s);
        }
    }

    private static boolean noLongRuns(String s) {
        return !Pattern.compile("(\\d)\\1{9}").matcher(s).find();
    }

    @Test
    void knownValues() {
        int[] want = {1, 2, 2, 4, 6, 6, 8, 10, 14, 20};
        for (int n = 1; n <= want.length; n++) {
            assertThat(TallyChant.lengthOf(n)).isEqualTo(want[n - 1]);
        }
        assertThat(TallyChant.nth("1", 6)).isEqualTo("312211");
        assertThat(TallyChant.describe("1111111111")).isEqualTo("101");
        assertThat(TallyChant.undescribe("312211")).isEqualTo("111221");
        assertThatThrownBy(() -> TallyChant.undescribe("1111")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TallyChant.undescribe("101")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void grades() {
        assertThat(TallyChant.grade("1211", "111221")).isEqualTo(TallyChant.Grade.CHANTED);
        assertThat(TallyChant.grade("1211", "111222")).isEqualTo(TallyChant.Grade.STAMMERED);
        assertThat(TallyChant.forgemasterLine(TallyChant.Grade.CHANTED)).contains("Forgemaster");
        assertThat(TallyChant.forgemasterLine(TallyChant.Grade.STAMMERED)).contains("stammered");
        assertThat(TallyChant.QUEST_ID).isEqualTo("q_tally_chant");
    }
}
