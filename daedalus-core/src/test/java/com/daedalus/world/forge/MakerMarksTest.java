// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.MakerMarks.Grade;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class MakerMarksTest {

    @Test
    void matchesBruteForceOnSeededStrips() {
        for (long seed = 0; seed < 250; seed++) {
            String s = MakerMarks.strip(seed, (int) (seed % 40), 1 + (int) (seed % 4));
            int n = s.length();
            int[] sa = MakerMarks.suffixArray(s);
            for (int j = 1; j < n; j++) {
                assertThat(s.substring(sa[j - 1]).compareTo(s.substring(sa[j]))).as("seed %d", seed).isNegative();
            }
            Set<String> all = new HashSet<>();
            int rep = 0;
            for (int i = 0; i < n; i++) {
                for (int j = i + 1; j <= n; j++) {
                    String sub = s.substring(i, j);
                    if (!all.add(sub)) {
                        rep = Math.max(rep, sub.length());
                    }
                }
            }
            assertThat(MakerMarks.distinctSubstrings(s)).as("seed %d", seed).isEqualTo(all.size());
            String lr = MakerMarks.longestRepeat(s);
            assertThat(lr).hasSize(rep);
            if (rep > 0) {
                assertThat(s.indexOf(lr, s.indexOf(lr) + 1)).isNotNegative();
            }
            assertThat(MakerMarks.grade(s, all.size(), rep)).isEqualTo(Grade.INDEXED);
        }
    }

    @Test
    void knownStrips() {
        assertThat(MakerMarks.suffixArray("banana")).containsExactly(5, 3, 1, 0, 4, 2);
        assertThat(MakerMarks.lcp("banana", MakerMarks.suffixArray("banana"))).containsExactly(0, 1, 3, 0, 0, 2);
        assertThat(MakerMarks.distinctSubstrings("banana")).isEqualTo(15);
        assertThat(MakerMarks.longestRepeat("banana")).isEqualTo("ana");
        assertThat(MakerMarks.longestRepeat("")).isEmpty();
        assertThat(MakerMarks.distinctSubstrings("aaaa")).isEqualTo(4);
    }

    @Test
    void gradesLinesAndReplay() {
        assertThat(MakerMarks.grade("banana", 15, 3)).isEqualTo(Grade.INDEXED);
        assertThat(MakerMarks.grade("banana", 21, 3)).isEqualTo(Grade.SMUDGED);
        assertThat(MakerMarks.grade("banana", 15, 2)).isEqualTo(Grade.SMUDGED);
        for (Grade g : Grade.values()) {
            assertThat(MakerMarks.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(MakerMarks.QUEST_ID).isEqualTo("q_maker_marks");
        assertThat(MakerMarks.strip(7, 10, 2)).isEqualTo(MakerMarks.strip(7, 10, 2)).hasSize(10);
        assertThatThrownBy(() -> MakerMarks.strip(1, -1, 2)).isInstanceOf(IllegalArgumentException.class);
    }
}
