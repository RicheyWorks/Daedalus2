// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.TarpCover.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class TarpCoverTest {

    @Test
    void matchesGridBruteForceOnSeededTarpSets() {
        for (long seed = 0; seed < 200; seed++) {
            int n = (int) (seed % 15);
            int range = 1 + (int) (seed % 25);
            long[][] t = TarpCover.tarps(seed, n, range);
            long one = 0;
            long two = 0;
            for (int x = 0; x < range; x++) {
                for (int y = 0; y < range; y++) {
                    int c = 0;
                    for (long[] r : t) {
                        if (r[0] <= x && x < r[2] && r[1] <= y && y < r[3]) {
                            c++;
                        }
                    }
                    one += c >= 1 ? 1 : 0;
                    two += c >= 2 ? 1 : 0;
                }
            }
            assertThat(TarpCover.unionArea(t)).as("seed %d", seed).isEqualTo(one);
            assertThat(TarpCover.overlapArea(t)).as("seed %d two", seed).isEqualTo(two);
            assertThat(TarpCover.grade(t, one, two)).isEqualTo(Grade.COVERED);
        }
    }

    @Test
    void knownYards() {
        long[][] t = {{0, 0, 2, 2}, {1, 1, 3, 3}};
        assertThat(TarpCover.unionArea(t)).isEqualTo(7);
        assertThat(TarpCover.overlapArea(t)).isEqualTo(1);
        long[][] big = {{-1_000_000_000L, -1_000_000_000L, 1_000_000_000L, 1_000_000_000L}};
        assertThat(TarpCover.unionArea(big)).isEqualTo(4_000_000_000_000_000_000L);
        assertThat(TarpCover.unionArea(new long[0][])).isZero();
        assertThat(TarpCover.unionArea(new long[][] {{0, 0, 0, 5}})).isZero();
        assertThatThrownBy(() -> TarpCover.unionArea(new long[][] {{2, 0, 1, 1}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TarpCover.unionArea(new long[][] {{0, 0, 2_000_000_000L, 1}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        long[][] t = {{0, 0, 2, 2}, {1, 1, 3, 3}};
        assertThat(TarpCover.grade(t, 8, 1)).isEqualTo(Grade.EXPOSED);
        assertThat(TarpCover.grade(t, 7, 0)).isEqualTo(Grade.EXPOSED);
        for (Grade g : Grade.values()) {
            assertThat(TarpCover.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(TarpCover.QUEST_ID).isEqualTo("q_tarp_cover");
        assertThat(TarpCover.tarps(3, 4, 9)).isDeepEqualTo(TarpCover.tarps(3, 4, 9));
        assertThatThrownBy(() -> TarpCover.tarps(1, 2, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
