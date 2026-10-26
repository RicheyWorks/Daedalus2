// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;
import org.junit.jupiter.api.Test;

class DripCaveChorusTest {
    @Test void everyCaveIsSolvableAndAnswerIsTheEarliestChorus() {
        for (long s = 0; s < 200; s++) {
            DripCaveChorus c = DripCaveChorus.seeded(s);
            int n = c.drips().size();
            assertThat(n).isBetween(3, 5);
            assertThat(c.sounding(c.answer())).hasSize(n);
            for (int t = 1; t < c.answer(); t++) {
                assertThat(c.sounding(t).size()).as("seed %d beat %d", s, t).isLessThan(n);
            }
            assertThat(c.judge(c.answer() * DripCaveChorus.BEAT_MS).correct()).isTrue();
            assertThat(c.seed()).isEqualTo(s);
        }
    }

    @Test void authoredCaveAndTapWindow() {
        DripCaveChorus c = DripCaveChorus.of(List.of(new DripCaveChorus.Drip(3, 2, 220), new DripCaveChorus.Drip(5, 3, 247)));
        assertThat(c.answer()).isEqualTo(8);
        assertThat(c.judge(8 * 250 + 80).correct()).isTrue();
        assertThat(c.judge(8 * 250 - 80).correct()).isTrue();
        assertThat(c.judge(8 * 250 + 81).reason()).startsWith("off the beat");
        assertThat(c.judge(5 * 250).reason()).isEqualTo("too early");
        assertThat(c.judge(23 * 250).reason()).contains("later chorus");
        assertThat(c.sounding(-1)).isEmpty();
    }

    @Test void rejectsBadCaves() {
        assertThatThrownBy(() -> DripCaveChorus.of(List.of())).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DripCaveChorus.of(null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DripCaveChorus.of(List.of(new DripCaveChorus.Drip(3, 3, 1)))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DripCaveChorus.of(List.of(new DripCaveChorus.Drip(0, 0, 1)))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DripCaveChorus.of(List.of(new DripCaveChorus.Drip(2, 0, 1), new DripCaveChorus.Drip(4, 1, 1))))
            .hasMessageContaining("never");
    }

    @Test void pitchesArePentatonic() {
        assertThat(DripCaveChorus.hz(0)).isEqualTo(220.0);
        assertThat(DripCaveChorus.hz(3)).isEqualTo(329.628);
        assertThat(DripCaveChorus.hz(5)).isEqualTo(440.0);
    }
}