// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class AnglerSkillTest {

    @Test
    void normalCdfIsAccurate() {
        assertThat(AnglerSkill.phi(0)).isCloseTo(0.5, within(1e-7));
        assertThat(AnglerSkill.phi(1.959963984540054)).isCloseTo(0.975, within(1e-6));
        assertThat(AnglerSkill.phi(-1)).isCloseTo(0.158655, within(1e-6));
        assertThat(AnglerSkill.erf(0)).isZero();
    }

    @Test
    void catchChanceRisesWithTheWindowAndWithSkill() {
        assertThat(AnglerSkill.STEADY.catchChance(0.40)).isCloseTo(0.5, within(1e-7));
        assertThat(AnglerSkill.STEADY.catchChance(0.9)).isGreaterThan(0.99);
        assertThat(AnglerSkill.OLD_HAND.catchChance(0.35)).isGreaterThan(AnglerSkill.NOVICE.catchChance(0.35));
        AnglerSkill robot = new AnglerSkill(0.3, 0);
        assertThat(robot.catchChance(0.3)).isEqualTo(1.0);
        assertThat(robot.catchChance(0.29)).isEqualTo(0.0);
    }

    @Test
    void sampledReactionsMatchTheModel() {
        OddsRng rng = new OddsRng(9);
        int inside = 0;
        double sum = 0;
        int n = 20000;
        for (int i = 0; i < n; i++) {
            double r = AnglerSkill.STEADY.sampleReaction(rng);
            assertThat(r).isGreaterThanOrEqualTo(0);
            sum += r;
            if (r <= 0.45) {
                inside++;
            }
        }
        assertThat(sum / n).isCloseTo(0.40, within(0.005));
        assertThat(inside / (double) n).isCloseTo(AnglerSkill.STEADY.catchChance(0.45), within(0.015));
    }

    @Test
    void rejectsBadSkills() {
        assertThatThrownBy(() -> new AnglerSkill(0, 0.1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new AnglerSkill(Double.POSITIVE_INFINITY, 0.1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new AnglerSkill(0.3, -0.1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new AnglerSkill(0.3, Double.POSITIVE_INFINITY)).isInstanceOf(IllegalArgumentException.class);
    }
}
