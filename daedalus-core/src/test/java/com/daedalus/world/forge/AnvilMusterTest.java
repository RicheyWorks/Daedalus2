// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.AnvilMuster.Grade;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AnvilMusterTest {

    @Test
    void kthMatchesSortOnSeededRoads() {
        for (long seed = 0; seed < 300; seed++) {
            long[] s = AnvilMuster.spots(seed, 1 + (int) (seed % 60), (int) (seed % 25));
            long[] sorted = s.clone();
            Arrays.sort(sorted);
            long[] copy = s.clone();
            for (int k = 0; k < s.length; k++) {
                assertThat(AnvilMuster.kth(s, k)).as("seed %d k %d", seed, k).isEqualTo(sorted[k]);
            }
            assertThat(s).isEqualTo(copy);
        }
    }

    @Test
    void weightedMedianBeatsEverySpot() {
        SplittableRandom r = new SplittableRandom(3);
        for (long seed = 0; seed < 300; seed++) {
            int n = 1 + (int) (seed % 15);
            long[] s = AnvilMuster.spots(seed, n, 50);
            long[] w = new long[n];
            for (int i = 0; i < n; i++) {
                w[i] = r.nextInt(6);
            }
            w[0] += 1;
            long m = AnvilMuster.weightedMedian(s, w);
            long best = Long.MAX_VALUE;
            for (long at = 0; at <= 50; at++) {
                best = Math.min(best, AnvilMuster.walk(s, w, at));
            }
            assertThat(AnvilMuster.walk(s, w, m)).as("seed %d", seed).isEqualTo(best);
            assertThat(AnvilMuster.grade(s, w, m)).isEqualTo(Grade.CENTRED);
        }
    }

    @Test
    void knownRoadBadInputGradesAndLines() {
        long[] s = {1, 2, 10};
        long[] w = {1, 1, 5};
        assertThat(AnvilMuster.weightedMedian(s, w)).isEqualTo(10);
        assertThat(AnvilMuster.grade(s, w, 10)).isEqualTo(Grade.CENTRED);
        assertThat(AnvilMuster.grade(s, w, 2)).isEqualTo(Grade.ASKEW);
        assertThat(AnvilMuster.kth(new long[] {5, 1, 4}, 1)).isEqualTo(4);
        assertThatThrownBy(() -> AnvilMuster.kth(new long[0], 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> AnvilMuster.weightedMedian(s, new long[] {0, 0, 0}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> AnvilMuster.walk(s, new long[] {1}, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> AnvilMuster.walk(s, new long[] {1, -1, 1}, 0))
                .isInstanceOf(IllegalArgumentException.class);
        for (Grade g : Grade.values()) {
            assertThat(AnvilMuster.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(AnvilMuster.QUEST_ID).isEqualTo("q_anvil_muster");
        assertThat(AnvilMuster.spots(2, 9, 30)).isEqualTo(AnvilMuster.spots(2, 9, 30)).hasSize(9);
    }
}
