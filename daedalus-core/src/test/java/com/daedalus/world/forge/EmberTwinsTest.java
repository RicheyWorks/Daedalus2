// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.EmberTwins.Grade;
import com.daedalus.world.forge.EmberTwins.Pair;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class EmberTwinsTest {

    @Test
    void matchesBruteForceOnSeededScatters() {
        for (long seed = 0; seed < 300; seed++) {
            int n = 2 + (int) (seed % 80);
            int range = seed % 3 == 0 ? 10 : 1000;
            long[][] p = EmberTwins.embers(seed, n, range);
            long best = Long.MAX_VALUE;
            for (int i = 0; i < n; i++) {
                for (int j = i + 1; j < n; j++) {
                    best = Math.min(best, EmberTwins.dist2(p[i], p[j]));
                }
            }
            Pair got = EmberTwins.closestPair(p);
            assertThat(got.dist2()).as("seed %d", seed).isEqualTo(best);
            assertThat(got.a()).isLessThan(got.b());
            assertThat(EmberTwins.dist2(p[got.a()], p[got.b()])).isEqualTo(best);
            assertThat(EmberTwins.grade(p, got.b(), got.a())).isEqualTo(Grade.FUSED);
        }
    }

    @Test
    void knownScatters() {
        long[][] p = {{0, 0}, {10, 10}, {3, 4}, {11, 10}};
        assertThat(EmberTwins.closestPair(p)).isEqualTo(new Pair(1, 3, 1));
        long[][] far = {{-1_000_000_000L, -1_000_000_000L}, {1_000_000_000L, 1_000_000_000L}};
        assertThat(EmberTwins.closestPair(far).dist2()).isEqualTo(8_000_000_000_000_000_000L);
        assertThatThrownBy(() -> EmberTwins.closestPair(new long[][] {{0, 0}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EmberTwins.closestPair(new long[][] {{0, 0}, {2_000_000_000L, 0}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        long[][] p = {{0, 0}, {10, 10}, {3, 4}, {11, 10}};
        assertThat(EmberTwins.grade(p, 0, 2)).isEqualTo(Grade.STRAYED);
        assertThat(EmberTwins.grade(p, 1, 1)).isEqualTo(Grade.STRAYED);
        assertThat(EmberTwins.grade(p, 1, 9)).isEqualTo(Grade.STRAYED);
        for (Grade g : Grade.values()) {
            assertThat(EmberTwins.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(EmberTwins.QUEST_ID).isEqualTo("q_ember_twins");
        assertThat(EmberTwins.embers(3, 5, 50)).isDeepEqualTo(EmberTwins.embers(3, 5, 50));
        assertThatThrownBy(() -> EmberTwins.embers(1, 1, 5)).isInstanceOf(IllegalArgumentException.class);
    }
}
