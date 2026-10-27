// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ScrollFold.Folded;
import com.daedalus.world.forge.ScrollFold.Grade;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Comparator;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ScrollFoldTest {

    @Test
    void matchesNaiveRotationsAndRoundTrips() {
        for (long seed = 0; seed < 300; seed++) {
            String s = ScrollFold.scroll(seed, (int) (seed % 40), 1 + (int) (seed % 5));
            int n = s.length();
            Integer[] idx = new Integer[n];
            for (int i = 0; i < n; i++) {
                idx[i] = i;
            }
            Arrays.sort(idx, Comparator.comparing((Integer i) -> s.substring(i) + s.substring(0, i))
                    .thenComparing(i -> i));
            int[] want = Arrays.stream(idx).mapToInt(Integer::intValue).toArray();
            assertThat(ScrollFold.rotations(s)).as("seed %d %s", seed, s).containsExactly(want);
            Folded f = ScrollFold.fold(s);
            assertThat(ScrollFold.unfold(f)).isEqualTo(s);
            assertThat(ScrollFold.unmtf(ScrollFold.mtf(f.last()))).isEqualTo(f.last());
            assertThat(ScrollFold.grade(s, f)).isEqualTo(Grade.UNFOLDED);
        }
    }

    @Test
    void knownScrolls() {
        assertThat(ScrollFold.fold("banana")).isEqualTo(new Folded("nnbaaa", 3));
        assertThat(ScrollFold.unfold(new Folded("nnbaaa", 3))).isEqualTo("banana");
        assertThat(ScrollFold.fold("")).isEqualTo(new Folded("", 0));
        assertThat(ScrollFold.unfold(ScrollFold.fold("abab"))).isEqualTo("abab");
        assertThat(ScrollFold.mtf("aaab")).containsExactly(97, 0, 0, 98);
        assertThatThrownBy(() -> ScrollFold.unfold(new Folded("ab", 5))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ScrollFold.mtf("\u0400")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ScrollFold.unmtf(new int[] {256})).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        assertThat(ScrollFold.grade("banana", new Folded("nnbaaa", 3))).isEqualTo(Grade.UNFOLDED);
        assertThat(ScrollFold.grade("banana", new Folded("nnbaaa", 2))).isEqualTo(Grade.TORN);
        for (Grade g : Grade.values()) {
            assertThat(ScrollFold.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(ScrollFold.QUEST_ID).isEqualTo("q_scroll_fold");
        assertThat(ScrollFold.scroll(5, 9, 3)).isEqualTo(ScrollFold.scroll(5, 9, 3)).hasSize(9);
        assertThatThrownBy(() -> ScrollFold.scroll(1, 3, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
