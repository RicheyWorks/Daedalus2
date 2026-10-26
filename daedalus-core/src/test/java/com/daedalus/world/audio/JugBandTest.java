// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class JugBandTest {
    @Test void everyBandIsTunableByFillingOnly() {
        for (long s = 0; s < 300; s++) {
            JugBand b = JugBand.seeded(s);
            List<Double> fill = b.solution();
            for (int i = 0; i < JugBand.JUGS; i++) {
                assertThat(fill.get(i)).as("seed %d jug %d", s, i).isGreaterThanOrEqualTo(0);
                assertThat(JugBand.frequency(b.jugs().get(i), 0)).isLessThanOrEqualTo(b.melody().get(i) + 1e-6);
            }
            JugBand.Verdict v = b.judge(fill);
            assertThat(v.tuned()).as("seed %d %s", s, v.reason()).isTrue();
            assertThat(b.seed()).isEqualTo(s);
        }
    }

    @Test void helmholtzPhysics() {
        JugBand.Jug j = new JugBand.Jug(Math.PI * 0.015 * 0.015, 0.06, 5.0);
        // 343/(2 pi) * sqrt(7.0686e-4 / (0.005 * 0.06)) = 83.80 Hz
        assertThat(JugBand.frequency(j, 0)).isCloseTo(83.80, within(0.01));
        assertThat(JugBand.frequency(j, 2.5)).isCloseTo(83.80 * Math.sqrt(2), within(0.02));
        assertThatThrownBy(() -> JugBand.frequency(j, 5.0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void judgeRejectsOverfillAndReportsCents() {
        JugBand b = JugBand.seeded(8);
        assertThat(b.judge(null).reason()).startsWith("pour into all");
        List<Double> over = new ArrayList<>(b.solution());
        over.set(0, b.jugs().get(0).litres());
        assertThat(b.judge(over).reason()).contains("overfilled");
        List<Double> none = new ArrayList<>(List.of(0.0, 0.0, 0.0, 0.0));
        JugBand.Verdict v = b.judge(none);
        assertThat(v.tuned()).isFalse();
        assertThat(v.notes()).allMatch(n -> n.cents() <= 0);
    }
}