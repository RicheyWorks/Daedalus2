// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.SparkCensus.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

class SparkCensusTest {

    @Test
    void everySparkIsKeptWithChanceKOverN() {
        int n = 20;
        int k = 5;
        int trials = 40_000;
        int[] stream = new int[n];
        for (int i = 0; i < n; i++) {
            stream[i] = 100 + i;
        }
        int[] hits = new int[n];
        for (long seed = 0; seed < trials; seed++) {
            int[] s = SparkCensus.sample(stream, k, seed);
            assertThat(s).hasSize(k).doesNotHaveDuplicates();
            for (int x : s) {
                hits[x - 100]++;
            }
        }
        for (int i = 0; i < n; i++) {
            assertThat(hits[i] / (double) trials).as("spark %d", i).isCloseTo(SparkCensus.inclusionChance(n, k),
                    within(0.012));
        }
    }

    @Test
    void streamingStateAndWeighted() {
        SparkCensus c = new SparkCensus(3, 9);
        c.offer(7);
        c.offer(8);
        assertThat(c.sample()).containsExactly(7, 8);
        assertThat(c.seen()).isEqualTo(2);
        for (int i = 0; i < 100; i++) {
            c.offer(i);
        }
        assertThat(c.sample()).hasSize(3);
        assertThat(SparkCensus.sample(new int[] {1, 2, 3}, 4, 1)).containsExactly(1, 2, 3);
        assertThat(SparkCensus.sample(new int[] {5, 6, 7, 8}, 2, 42)).isEqualTo(
                SparkCensus.sample(new int[] {5, 6, 7, 8}, 2, 42));

        double[] w = {1, 2, 7, 0};
        int[] hits = new int[w.length];
        int trials = 50_000;
        for (long seed = 0; seed < trials; seed++) {
            int[] pick = SparkCensus.weighted(w, 1, seed);
            hits[pick[0]]++;
        }
        for (int i = 0; i < w.length; i++) {
            assertThat(hits[i] / (double) trials).as("weighted %d", i).isCloseTo(w[i] / 10, within(0.01));
        }
        assertThat(SparkCensus.weighted(w, 5, 3)).containsExactly(0, 1, 2);
    }

    @Test
    void badInputGradesAndLines() {
        assertThatThrownBy(() -> new SparkCensus(0, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SparkCensus.weighted(new double[] {-1}, 1, 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SparkCensus.inclusionChance(0, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(SparkCensus.inclusionChance(3, 5)).isEqualTo(1.0);
        assertThat(SparkCensus.grade(20, 5, 0.25)).isEqualTo(Grade.FAIR);
        assertThat(SparkCensus.grade(20, 5, 0.2)).isEqualTo(Grade.BIASED);
        for (Grade g : Grade.values()) {
            assertThat(SparkCensus.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(SparkCensus.QUEST_ID).isEqualTo("q_spark_census");
    }
}
