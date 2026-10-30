// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class HullKnockSurveyTest {
    @Test void solutionFindsExactlyTheCracksAndPitchesStayLowMid() {
        for (long s = 0; s < 300; s++) {
            HullKnockSurvey h = HullKnockSurvey.seeded(s);
            assertThat(h.plates().size()).isBetween(8, 12);
            for (HullKnockSurvey.Plate p : h.plates()) {
                assertThat(p.heardHz()).isBetween(40.0, 410.0);
            }
            HullKnockSurvey.Verdict v = h.judge(h.solution());
            assertThat(v.perfect()).as("seed %d", s).isTrue();
            assertThat(v.cracked().size()).isBetween(1, 3);
            for (int i : v.cracked()) {
                assertThat(h.plates().get(i).ringMs()).isEqualTo(HullKnockSurvey.CRACK_RING_MS);
            }
            assertThat(h.seed()).isEqualTo(s);
        }
    }

    @Test void judgeCountsHitsMissesAndFalseAlarms() {
        HullKnockSurvey h = HullKnockSurvey.seeded(2);
        Set<Integer> truth = h.solution();
        HullKnockSurvey.Verdict none = h.judge(null);
        assertThat(none.misses()).isEqualTo(truth.size());
        assertThat(none.perfect()).isFalse();
        Set<Integer> extra = new HashSet<>(truth);
        for (int i = 0; i < h.plates().size(); i++) {
            if (!truth.contains(i)) {
                extra.add(i);
                break;
            }
        }
        HullKnockSurvey.Verdict v = h.judge(extra);
        assertThat(v.hits()).isEqualTo(truth.size());
        assertThat(v.falseAlarms()).isEqualTo(1);
        assertThat(v.perfect()).isFalse();
    }

    @Test void platePhysics() {
        assertThat(HullKnockSurvey.expectedHz(8, 0.6)).isCloseTo(400.0, within(1e-9));
        assertThat(HullKnockSurvey.expectedHz(4, 1.2)).isCloseTo(50.0, within(1e-9));
    }
}