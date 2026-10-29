// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.SparkTally.Grade;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class SparkTallyTest {

    @Test
    void neverUndercountsAndStaysWithinBoundOnSeededStreams() {
        long over = 0;
        long checked = 0;
        for (long seed = 0; seed < 60; seed++) {
            long[] s = SparkTally.stream(seed, 3000, 500);
            SparkTally plain = new SparkTally(0.01, 0.01, seed, false);
            SparkTally cons = new SparkTally(0.01, 0.01, seed, true);
            Map<Long, Long> exact = new HashMap<>();
            for (long k : s) {
                plain.add(k, 1);
                cons.add(k, 1);
                exact.merge(k, 1L, Long::sum);
            }
            assertThat(plain.total()).isEqualTo(s.length);
            for (long k = 0; k < 600; k++) {
                long truth = exact.getOrDefault(k, 0L);
                long e = plain.estimate(k);
                long c = cons.estimate(k);
                assertThat(e).as("seed %d key %d", seed, k).isGreaterThanOrEqualTo(truth);
                assertThat(c).isGreaterThanOrEqualTo(truth).isLessThanOrEqualTo(e);
                checked++;
                if (e - truth > 0.01 * s.length) {
                    over++;
                }
            }
        }
        assertThat((double) over / checked).isLessThan(0.02);
    }

    @Test
    void sizesAndHeavy() {
        SparkTally t = new SparkTally(0.1, 0.05, 1, false);
        assertThat(t.width()).isEqualTo(28);
        assertThat(t.depth()).isEqualTo(3);
        t.add(7, 50);
        t.add(9, 5);
        t.add(11, 45);
        assertThat(t.estimate(7)).isGreaterThanOrEqualTo(50);
        assertThat(t.heavy(new long[] {7, 9, 11}, 0.3)).contains(7, 11);
        assertThatThrownBy(() -> new SparkTally(0, 0.1, 1, false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> t.add(1, -1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        SparkTally t = new SparkTally(0.001, 0.01, 5, true);
        t.add(1, 90);
        t.add(2, 10);
        assertThat(t.grade(new long[] {1, 2}, 0.5, new long[] {1})).isEqualTo(Grade.TALLIED);
        assertThat(t.grade(new long[] {1, 2}, 0.5, new long[] {1, 2})).isEqualTo(Grade.MISCOUNTED);
        for (Grade g : Grade.values()) {
            assertThat(SparkTally.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(SparkTally.QUEST_ID).isEqualTo("q_spark_tally");
        assertThat(SparkTally.stream(4, 20, 9)).containsExactly(SparkTally.stream(4, 20, 9));
        assertThatThrownBy(() -> SparkTally.stream(1, 3, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
