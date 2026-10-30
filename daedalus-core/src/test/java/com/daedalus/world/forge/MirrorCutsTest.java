// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.MirrorCuts.Grade;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class MirrorCutsTest {

    @Test
    void matchesBruteForceOverCutMasks() {
        for (long seed = 0; seed < 300; seed++) {
            String s = MirrorCuts.strip(seed, 1 + (int) (seed % 14), 1 + (int) (seed % 3));
            int n = s.length();
            int best = Integer.MAX_VALUE;
            for (int mask = 0; mask < (1 << (n - 1)); mask++) {
                int start = 0;
                boolean ok = true;
                for (int i = 0; i < n && ok; i++) {
                    if (i == n - 1 || ((mask >> i) & 1) == 1) {
                        ok = MirrorCuts.isMirror(s.substring(start, i + 1));
                        start = i + 1;
                    }
                }
                if (ok) {
                    best = Math.min(best, Integer.bitCount(mask));
                }
            }
            assertThat(MirrorCuts.minCuts(s)).as("seed %d %s", seed, s).isEqualTo(best);
            List<String> p = MirrorCuts.pieces(s);
            assertThat(p).hasSize(best + 1);
            assertThat(MirrorCuts.grade(s, p)).isEqualTo(Grade.MIRRORED);
        }
    }

    @Test
    void knownStrips() {
        assertThat(MirrorCuts.minCuts("aab")).isEqualTo(1);
        assertThat(MirrorCuts.pieces("aab")).containsExactly("aa", "b");
        assertThat(MirrorCuts.minCuts("racecar")).isZero();
        assertThat(MirrorCuts.minCuts("abcde")).isEqualTo(4);
        assertThat(MirrorCuts.minCuts("")).isZero();
        assertThat(MirrorCuts.pieces("")).isEmpty();
        assertThatThrownBy(() -> MirrorCuts.strip(1, 3, 4)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        assertThat(MirrorCuts.grade("aab", List.of("aa", "b"))).isEqualTo(Grade.MIRRORED);
        assertThat(MirrorCuts.grade("aab", List.of("a", "a", "b"))).isEqualTo(Grade.WARPED);
        assertThat(MirrorCuts.grade("aab", List.of("aab"))).isEqualTo(Grade.WARPED);
        assertThat(MirrorCuts.grade("aab", List.of("aa", "c"))).isEqualTo(Grade.WARPED);
        assertThat(MirrorCuts.grade("", List.of())).isEqualTo(Grade.MIRRORED);
        for (Grade g : Grade.values()) {
            assertThat(MirrorCuts.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(MirrorCuts.QUEST_ID).isEqualTo("q_mirror_cuts");
        assertThat(MirrorCuts.strip(5, 9, 3)).isEqualTo(MirrorCuts.strip(5, 9, 3)).hasSize(9);
    }
}
