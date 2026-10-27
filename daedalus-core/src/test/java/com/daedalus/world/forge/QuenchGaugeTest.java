// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.QuenchGauge.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class QuenchGaugeTest {

    @Test
    void queriesMatchBruteForceOnSeededRows() {
        for (long seed = 0; seed < 120; seed++) {
            int n = 1 + (int) (seed % 37);
            int[] t = QuenchGauge.troughs(seed, n, 1 + (int) (seed % 9));
            QuenchGauge g = new QuenchGauge(t);
            for (int i = 0; i < n; i++) {
                for (int j = i; j < n; j++) {
                    int lo = i;
                    int hi = t[i];
                    for (int x = i; x <= j; x++) {
                        if (t[x] < t[lo]) {
                            lo = x;
                        }
                        hi = Math.max(hi, t[x]);
                    }
                    assertThat(g.argMin(i, j)).as("seed %d [%d,%d]", seed, i, j).isEqualTo(lo);
                    assertThat(g.min(i, j)).isEqualTo(t[lo]);
                    assertThat(g.max(i, j)).as("seed %d [%d,%d]", seed, i, j).isEqualTo(hi);
                }
            }
        }
    }

    @Test
    void knownRowAndBadSpans() {
        QuenchGauge g = new QuenchGauge(new int[] {5, 2, 8, 2, 9, 1});
        assertThat(g.min(0, 3)).isEqualTo(2);
        assertThat(g.argMin(0, 3)).isEqualTo(1);
        assertThat(g.max(1, 3)).isEqualTo(8);
        assertThat(g.min(5, 5)).isEqualTo(1);
        assertThatThrownBy(() -> g.min(3, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> g.max(0, 6)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new QuenchGauge(new int[0]).min(0, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void inputIsCopiedGradesAndReplay() {
        int[] t = {4, 3, 7};
        QuenchGauge g = new QuenchGauge(t);
        t[1] = 99;
        assertThat(g.min(0, 2)).isEqualTo(3);
        int[][] spans = {{0, 2}, {2, 2}};
        assertThat(g.grade(spans, new int[] {3, 7})).isEqualTo(Grade.SHARP);
        assertThat(g.grade(spans, new int[] {4, 7})).isEqualTo(Grade.DULL);
        assertThat(g.grade(spans, new int[] {3})).isEqualTo(Grade.DULL);
        for (Grade x : Grade.values()) {
            assertThat(QuenchGauge.forgemasterLine(x)).startsWith("Forgemaster:");
        }
        assertThat(QuenchGauge.QUEST_ID).isEqualTo("q_quench_gauge");
        assertThat(QuenchGauge.troughs(7, 25, 50)).isEqualTo(QuenchGauge.troughs(7, 25, 50)).hasSize(25);
        assertThatThrownBy(() -> QuenchGauge.troughs(1, -1, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}
