// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;

class IntervalsTest {

    @Test
    void wilsonBracketsTheRateAndStaysInsideZeroOne() {
        double[] mid = Intervals.wilson(50, 100);
        assertThat(mid[0]).isLessThan(0.5);
        assertThat(mid[1]).isGreaterThan(0.5);
        assertThat(mid[0] + mid[1]).isCloseTo(1.0, within(1e-12));
        assertThat(Intervals.wilson(0, 10)[0]).isCloseTo(0.0, within(1e-12));
        assertThat(Intervals.wilson(10, 10)[1]).isCloseTo(1.0, within(1e-12));
        assertThat(Intervals.wilson(0, 10)[1]).isGreaterThan(0.0);
    }

    @Test
    void matchesTheCombatSimulatorsInterval() {
        double[] a = Intervals.wilson(37, 120);
        double[] b = CombatOddsSimulator.wilson(37, 120);
        assertThat(a).containsExactly(b);
    }

    @Test
    void rejectsImpossibleCounts() {
        assertThatThrownBy(() -> Intervals.wilson(1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Intervals.wilson(-1, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Intervals.wilson(6, 5)).isInstanceOf(IllegalArgumentException.class);
    }
}
