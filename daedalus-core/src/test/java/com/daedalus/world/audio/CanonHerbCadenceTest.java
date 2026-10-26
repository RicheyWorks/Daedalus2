// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.Test;

class CanonHerbCadenceTest {
    @Test void everySeededHandHasACadence() {
        for (long s = 0; s < 60; s++) {
            CanonHerbCadence c = CanonHerbCadence.seeded(s);
            assertThat(c.hand()).hasSize(9).allMatch(Herb.CANON::contains);
            List<List<List<Integer>>> sol = c.solutions();
            assertThat(sol).as("seed %d", s).isNotEmpty();
            CanonHerbCadence.Verdict v = c.judge(sol.get(0));
            assertThat(v.cadence()).isTrue();
            assertThat(v.chords()).hasSize(3);
            assertThat(c.seed()).isEqualTo(s);
        }
    }

    @Test void authoredDgcCadence() {
        // D minor (Rebell Fasage Lavine), G major (Solthorn Tisquill Rebell), C major (Doleaf Mimint Solthorn)
        CanonHerbCadence c = CanonHerbCadence.of(List.of("Rebell", "Fasage", "Lavine", "Solthorn", "Tisquill", "Rebell",
            "Doleaf", "Mimint", "Solthorn"));
        CanonHerbCadence.Verdict v = c.judge(List.of(List.of(0, 1, 2), List.of(3, 4, 5), List.of(6, 7, 8)));
        assertThat(v.cadence()).as(v.reason()).isTrue();
        assertThat(v.chords()).containsExactly("D minor", "G major", "C major");
        assertThat(c.judge(List.of(List.of(6, 7, 8), List.of(3, 4, 5), List.of(0, 1, 2))).reason()).contains("not a fifth below");
        assertThat(c.judge(List.of(List.of(0, 1, 3), List.of(2, 4, 5), List.of(6, 7, 8))).reason()).startsWith("bundle 1 is");
    }

    @Test void judgeRejectsMalformedBundles() {
        CanonHerbCadence c = CanonHerbCadence.seeded(1);
        assertThat(c.judge(null).reason()).isEqualTo("press exactly 3 bundles");
        assertThat(c.judge(List.of(List.of(0, 1), List.of(2, 3, 4), List.of(5, 6, 7))).reason()).contains("needs 3");
        assertThat(c.judge(List.of(List.of(0, 1, 2), List.of(2, 3, 4), List.of(5, 6, 7))).reason()).contains("exactly one");
        assertThat(c.judge(List.of(List.of(0, 1, 9), List.of(2, 3, 4), List.of(5, 6, 7))).reason()).contains("exactly one");
        assertThatThrownBy(() -> CanonHerbCadence.of(List.of("Doleaf"))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CanonHerbCadence.of(null)).isInstanceOf(IllegalArgumentException.class);
    }
}