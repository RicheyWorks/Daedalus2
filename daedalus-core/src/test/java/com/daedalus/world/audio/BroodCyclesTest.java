// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.Test;

class BroodCyclesTest {
    @Test void primeCyclesAreAlwaysAmongTheBest() {
        for (long s = 0; s < 300; s++) {
            BroodCycles b = BroodCycles.seeded(s);
            List<Integer> best = b.bestCycles();
            assertThat(best).as("seed %d %s", s, b.predators()).contains(13, 17);
            assertThat(b.judge(13).best()).isTrue();
            assertThat(b.seed()).isEqualTo(s);
        }
    }

    @Test void sharedFactorsLetPredatorsLockOn() {
        // joint cycle 48 years: emergences 0,12,24,36 all meet a 4-year predator at phase 0
        assertThat(BroodCycles.meetings(12, 4, 0)).isEqualTo(4);
        assertThat(BroodCycles.meetings(12, 4, 1)).isZero();
        // cycle 13 vs 4: emergences 0,13,26,39; only one meets phase 0
        assertThat(BroodCycles.meetings(13, 4, 0)).isEqualTo(1);
        BroodCycles b = BroodCycles.of(List.of(2, 3, 4));
        assertThat(b.score(12)).isEqualTo(180);
        assertThat(b.score(13)).isEqualTo(65);
        assertThat(b.score(17)).isEqualTo(65);
        assertThat(b.score(13)).isLessThan(b.score(12));
        assertThat(b.judge(12).best()).isFalse();
        assertThat(b.judge(12).bestCycles()).contains(13, 17);
    }

    @Test void validationAndEar() {
        assertThatThrownBy(() -> BroodCycles.of(List.of(1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BroodCycles.seeded(1).score(9)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BroodCycles.seeded(1).score(19)).isInstanceOf(IllegalArgumentException.class);
        assertThat(BroodCycles.chorusHz()).isEqualTo(BroodCycles.CHORUS_HZ);
        assertThat(BroodCycles.of(List.of(2)).seed()).isZero();
    }
}