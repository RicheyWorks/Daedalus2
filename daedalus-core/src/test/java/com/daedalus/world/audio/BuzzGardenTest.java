// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;

class BuzzGardenTest {
    @Test void bestMatchingIsOptimalAndEarSafe() {
        for (long s = 0; s < 300; s++) {
            BuzzGarden g = BuzzGarden.seeded(s);
            List<Integer> best = g.best();
            BuzzGarden.Verdict v = g.judge(best);
            assertThat(v.best()).isTrue();
            assertThat(v.pollen()).as("seed %d", s).isGreaterThan(200);
            for (BuzzGarden.Bee b : g.bees()) {
                assertThat(b.hz()).isBetween(190.0, 390.0);
            }
            assertThat(g.seed()).isEqualTo(s);
        }
    }

    @Test void pollenFallsWithMismatch() {
        assertThat(BuzzGarden.pollen(300, 300)).isEqualTo(100);
        assertThat(BuzzGarden.pollen(325, 300)).isEqualTo(61);
        assertThat(BuzzGarden.pollen(250, 300)).isEqualTo(14);
        assertThat(BuzzGarden.pollen(300, 325)).isEqualTo(BuzzGarden.pollen(325, 300));
    }

    @Test void judgeRejectsNonMatchings() {
        BuzzGarden g = BuzzGarden.seeded(4);
        assertThat(g.total(null)).isEqualTo(-1);
        assertThat(g.total(List.of(0, 0, 1, 2))).isEqualTo(-1);
        assertThat(g.total(List.of(0, 1, 2, 4))).isEqualTo(-1);
        assertThat(g.judge(List.of(0, 0, 1, 2)).best()).isFalse();
    }
}