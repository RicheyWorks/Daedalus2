// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.VeinSurvey.Grade;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class VeinSurveyTest {

    @Test
    void matchesPerQuerySetsOnSeededShafts() {
        for (long seed = 0; seed < 150; seed++) {
            int n = 1 + (int) (seed % 90);
            int[] ore = VeinSurvey.shaft(seed, n, 1 + (int) (seed % 12));
            int[][] q = VeinSurvey.stretches(seed + 7, n, 60);
            int[] got = VeinSurvey.distinctInRanges(ore, q);
            for (int i = 0; i < q.length; i++) {
                Set<Integer> s = new HashSet<>();
                for (int k = q[i][0]; k <= q[i][1]; k++) {
                    s.add(ore[k]);
                }
                assertThat(got[i]).as("seed %d query %d", seed, i).isEqualTo(s.size());
            }
            assertThat(VeinSurvey.grade(ore, q, got)).isEqualTo(Grade.CHARTED);
        }
    }

    @Test
    void knownShafts() {
        int[] ore = {-5, 7, -5, 1_000_000, 7};
        assertThat(VeinSurvey.distinctInRanges(ore, new int[][] {{0, 4}, {0, 2}, {2, 2}, {1, 4}}))
                .containsExactly(3, 2, 1, 3);
        assertThat(VeinSurvey.distinctInRanges(ore, new int[0][])).isEmpty();
        assertThatThrownBy(() -> VeinSurvey.distinctInRanges(ore, new int[][] {{3, 1}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> VeinSurvey.distinctInRanges(ore, new int[][] {{0, 5}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        int[] ore = {1, 2, 1};
        int[][] q = {{0, 2}};
        assertThat(VeinSurvey.grade(ore, q, new int[] {2})).isEqualTo(Grade.CHARTED);
        assertThat(VeinSurvey.grade(ore, q, new int[] {3})).isEqualTo(Grade.MISCHARTED);
        for (Grade g : Grade.values()) {
            assertThat(VeinSurvey.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(VeinSurvey.QUEST_ID).isEqualTo("q_vein_survey");
        assertThat(VeinSurvey.shaft(2, 8, 3)).containsExactly(VeinSurvey.shaft(2, 8, 3));
        assertThat(VeinSurvey.stretches(2, 8, 3)).isDeepEqualTo(VeinSurvey.stretches(2, 8, 3));
        assertThatThrownBy(() -> VeinSurvey.shaft(1, 3, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> VeinSurvey.stretches(1, 0, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}
