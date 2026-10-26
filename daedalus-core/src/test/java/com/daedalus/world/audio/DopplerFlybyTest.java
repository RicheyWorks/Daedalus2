// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import java.util.HashSet;
import org.junit.jupiter.api.Test;

class DopplerFlybyTest {
    @Test void heardPitchesAlwaysSolveToTheRightArkAndSpeed() {
        for (long s = 0; s < 300; s++) {
            DopplerFlyby d = DopplerFlyby.seeded(s);
            assertThat(d.roster().size()).isBetween(4, 6);
            assertThat(new HashSet<>(d.roster().stream().map(DopplerFlyby.Ark::hornHz).toList())).hasSize(d.roster().size());
            double fa = d.heardApproach();
            double fr = d.heardRecede();
            assertThat(fa).isGreaterThan(fr);
            String ark = d.nearestArk(DopplerFlyby.hornFrom(fa, fr));
            DopplerFlyby.Verdict v = d.judge(ark, DopplerFlyby.speedFrom(fa, fr));
            assertThat(v.correct()).as("seed %d", s).isTrue();
            assertThat(d.seed()).isEqualTo(s);
        }
    }

    @Test void dopplerFormulasInvert() {
        double fa = DopplerFlyby.approachHz(220, 34.3);
        double fr = DopplerFlyby.recedeHz(220, 34.3);
        assertThat(fa).isCloseTo(244.444, within(1e-3));
        assertThat(fr).isCloseTo(200.0, within(1e-9));
        assertThat(DopplerFlyby.hornFrom(fa, fr)).isCloseTo(220, within(1e-9));
        assertThat(DopplerFlyby.speedFrom(fa, fr)).isCloseTo(34.3, within(1e-9));
    }

    @Test void judgeSplitsArkAndSpeed() {
        DopplerFlyby d = DopplerFlyby.seeded(11);
        DopplerFlyby.Verdict truth = d.judge("x", 0);
        assertThat(truth.correct()).isFalse();
        assertThat(truth.rightArk()).isFalse();
        DopplerFlyby.Verdict slow = d.judge(truth.ark(), truth.speed() + 1.5);
        assertThat(slow.rightArk()).isTrue();
        assertThat(slow.rightSpeed()).isFalse();
        assertThat(d.judge(truth.ark(), truth.speed() - 1.0).correct()).isTrue();
    }
}