// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import java.util.List;
import org.junit.jupiter.api.Test;

class WaveOrganTest {
    @Test void everyPileHidesATriad() {
        for (long s = 0; s < 300; s++) {
            WaveOrgan w = WaveOrgan.seeded(s);
            assertThat(w.pile()).hasSize(8);
            List<List<Integer>> sol = w.solutions();
            assertThat(sol).as("seed %d", s).isNotEmpty();
            WaveOrgan.Verdict v = w.judge(sol.get(0));
            assertThat(v.triad()).isTrue();
            assertThat(v.chord()).matches("[A-G]#? (major|minor)");
            assertThat(v.worstCents()).isLessThanOrEqualTo(WaveOrgan.TOLERANCE_CENTS);
            assertThat(w.seed()).isEqualTo(s);
        }
    }

    @Test void closedPipePhysics() {
        // 343 / (4 * (0.75 + 0.3 * 0.1)) = 109.94 Hz, about A2
        assertThat(WaveOrgan.frequency(new WaveOrgan.Pipe(0.75, 0.1))).isCloseTo(109.936, within(1e-3));
    }

    @Test void authoredTriadAndBadPicks() {
        WaveOrgan w = WaveOrgan.seeded(5);
        assertThat(w.judge(null).reason()).isEqualTo("pick 3 different pipes");
        assertThat(w.judge(List.of(0, 0, 1)).triad()).isFalse();
        assertThat(w.judge(List.of(0, 1, 8)).triad()).isFalse();
        int bad = 0;
        for (int a = 0; a < 8; a++) {
            for (int b = a + 1; b < 8; b++) {
                for (int c = b + 1; c < 8; c++) {
                    WaveOrgan.Verdict v = w.judge(List.of(a, b, c));
                    if (!v.triad()) {
                        bad++;
                        assertThat(v.reason()).startsWith("out of tune by");
                    }
                }
            }
        }
        assertThat(bad).isPositive();
    }
}