// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ChimneySightlines.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ChimneySightlinesTest {

    @Test
    void matchBruteForceOnSeededRows() {
        for (long seed = 0; seed < 300; seed++) {
            int[] h = ChimneySightlines.row(seed, (int) (seed % 45), 1 + (int) (seed % 8));
            int n = h.length;
            int[] east = new int[n];
            int[] west = new int[n];
            for (int i = 0; i < n; i++) {
                east[i] = -1;
                for (int j = i + 1; j < n; j++) {
                    if (h[j] > h[i]) {
                        east[i] = j;
                        break;
                    }
                }
                int k = i;
                while (k >= 0 && h[k] <= h[i]) {
                    k--;
                }
                west[i] = i - k;
            }
            assertThat(ChimneySightlines.nextGreater(h)).as("seed %d", seed).containsExactly(east);
            assertThat(ChimneySightlines.span(h)).as("seed %d", seed).containsExactly(west);
            assertThat(ChimneySightlines.grade(h, east, west)).isEqualTo(Grade.KEEN);
        }
    }

    @Test
    void knownRow() {
        int[] h = {100, 80, 60, 70, 60, 75, 85};
        assertThat(ChimneySightlines.span(h)).containsExactly(1, 1, 1, 2, 1, 4, 6);
        assertThat(ChimneySightlines.nextGreater(h)).containsExactly(-1, 6, 3, 5, 5, 6, -1);
        assertThat(ChimneySightlines.nextGreater(new int[] {3, 3})).containsExactly(-1, -1);
        assertThat(ChimneySightlines.span(new int[0])).isEmpty();
    }

    @Test
    void gradesLinesAndReplay() {
        int[] h = {2, 1, 3};
        assertThat(ChimneySightlines.grade(h, new int[] {2, 2, -1}, new int[] {1, 1, 3})).isEqualTo(Grade.KEEN);
        assertThat(ChimneySightlines.grade(h, new int[] {1, 2, -1}, new int[] {1, 1, 3})).isEqualTo(Grade.HAZY);
        assertThat(ChimneySightlines.grade(h, new int[] {2, 2, -1}, new int[] {1, 2, 3})).isEqualTo(Grade.HAZY);
        for (Grade g : Grade.values()) {
            assertThat(ChimneySightlines.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(ChimneySightlines.QUEST_ID).isEqualTo("q_chimney_sightlines");
        assertThat(ChimneySightlines.row(3, 20, 9)).isEqualTo(ChimneySightlines.row(3, 20, 9)).hasSize(20);
        assertThatThrownBy(() -> ChimneySightlines.row(1, 2, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
