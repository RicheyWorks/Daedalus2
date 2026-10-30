// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class BinLabelsTest {

    private static List<String> shortlex(String abc, int maxLen) {
        List<String> out = new ArrayList<>();
        List<String> level = new ArrayList<>(List.of(""));
        for (int len = 1; len <= maxLen; len++) {
            List<String> next = new ArrayList<>();
            for (String p : level) {
                for (char c : abc.toCharArray()) {
                    next.add(p + c);
                }
            }
            out.addAll(next);
            level = next;
        }
        return out;
    }

    @Test
    void matchesShortlexEnumeration() {
        for (String abc : new String[] {"x", "01", "abc", "forge", BinLabels.LETTERS}) {
            List<String> all = shortlex(abc, abc.length() > 5 ? 2 : 4);
            for (int i = 0; i < all.size(); i++) {
                assertThat(BinLabels.label(i + 1, abc)).isEqualTo(all.get(i));
                assertThat(BinLabels.number(all.get(i), abc)).isEqualTo(i + 1L);
            }
        }
        SplittableRandom r = new SplittableRandom(425);
        for (int t = 0; t < 500; t++) {
            long n = 1 + r.nextLong(Long.MAX_VALUE);
            assertThat(BinLabels.number(BinLabels.label(n, BinLabels.LETTERS), BinLabels.LETTERS)).isEqualTo(n);
        }
        String top = BinLabels.label(Long.MAX_VALUE, "ab");
        assertThat(BinLabels.number(top, "ab")).isEqualTo(Long.MAX_VALUE);
    }

    @Test
    void knownValues() {
        assertThat(BinLabels.label(1, BinLabels.LETTERS)).isEqualTo("A");
        assertThat(BinLabels.label(26, BinLabels.LETTERS)).isEqualTo("Z");
        assertThat(BinLabels.label(27, BinLabels.LETTERS)).isEqualTo("AA");
        assertThat(BinLabels.label(702, BinLabels.LETTERS)).isEqualTo("ZZ");
        assertThat(BinLabels.number("XFD", BinLabels.LETTERS)).isEqualTo(16_384);
        assertThat(BinLabels.advance("AZ", 1, BinLabels.LETTERS)).isEqualTo("BA");
        assertThat(BinLabels.advance("AA", -1, BinLabels.LETTERS)).isEqualTo("Z");
        assertThatThrownBy(() -> BinLabels.number("A1", BinLabels.LETTERS))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BinLabels.label(0, BinLabels.LETTERS)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BinLabels.label(5, "aa")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BinLabels.number("Z".repeat(20), BinLabels.LETTERS))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void grades() {
        assertThat(BinLabels.grade(28, "AB")).isEqualTo(BinLabels.Grade.FILED);
        assertThat(BinLabels.grade(28, "BA")).isEqualTo(BinLabels.Grade.MISFILED);
        assertThat(BinLabels.grade(28, "")).isEqualTo(BinLabels.Grade.MISFILED);
        assertThat(BinLabels.forgemasterLine(BinLabels.Grade.FILED)).contains("Forgemaster");
        assertThat(BinLabels.forgemasterLine(BinLabels.Grade.MISFILED)).contains("misfiled");
        assertThat(BinLabels.QUEST_ID).isEqualTo("q_bin_labels");
    }
}
