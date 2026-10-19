// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.convoy;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import java.util.List;
import org.junit.jupiter.api.Test;

class ConvoyOddsTest {

    private static final ConvoyRisk R = ConvoyRisk.ODDSREAPER;

    @Test
    void aidSaturatesAtTheCap() {
        assertThat(R.aidCut(1)).isZero();
        assertThat(R.aidCut(2)).isCloseTo(0.25, within(1e-12));
        assertThat(R.aidCut(6)).isEqualTo(ConvoyRisk.MAX_AID_CUT);
        assertThat(R.loss(1, true)).isCloseTo(0.60, within(1e-12));
        assertThat(R.loss(3, false)).isCloseTo(0.10 * 0.55, within(1e-12));
    }

    @Test
    void loneArkMatchesHandComputation() {
        ConvoyPlan one = new ConvoyPlan(List.of(1), R);
        double arrive = 0.7 * 0.9 + 0.3 * 0.4;
        assertThat(one.arrivals()).hasSize(2);
        assertThat(one.atLeast(1)).isCloseTo(arrive, within(1e-12));
        assertThat(one.expectedArrivals()).isCloseTo(arrive, within(1e-12));
        assertThat(one.atLeast(0)).isCloseTo(1.0, within(1e-12));
    }

    @Test
    void distributionSumsToOneAndMonteCarloAgrees() {
        ConvoyPlan p = new ConvoyPlan(List.of(3, 3), R);
        double sum = 0;
        for (double x : p.arrivals()) {
            sum += x;
        }
        assertThat(sum).isCloseTo(1.0, within(1e-12));
        double[] mc = p.simulate(4, 2026, 20_000);
        assertThat(p.atLeast(4)).isBetween(mc[1] - 0.003, mc[2] + 0.003);
        assertThat(p.simulate(4, 2026, 20_000)).containsExactly(mc);
        assertThat(p.arks()).isEqualTo(6);
        assertThat(p.convoys()).containsExactly(3, 3);
    }

    @Test
    void splitsEnumeratePartitions() {
        assertThat(ConvoyPlan.splits(4)).containsExactly(
                List.of(4), List.of(3, 1), List.of(2, 2), List.of(2, 1, 1), List.of(1, 1, 1, 1));
        assertThat(ConvoyPlan.splits(6)).hasSize(11);
    }

    @Test
    void twoConvoysOfThreeBeatBothExtremes() {
        double together = new ConvoyPlan(List.of(6), R).atLeast(4);
        double pairs = new ConvoyPlan(List.of(3, 3), R).atLeast(4);
        double alone = new ConvoyPlan(List.of(1, 1, 1, 1, 1, 1), R).atLeast(4);
        assertThat(pairs).isGreaterThan(together).isGreaterThan(alone);
        ConvoyQuest q = new ConvoyQuest(R);
        assertThat(q.best()).containsExactly(3, 3);
        assertThat(q.bestChance()).isCloseTo(pairs, within(1e-12));
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new ConvoyRisk(1.2, 0, 0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ConvoyRisk(0.1, Double.NaN, 0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> R.aidCut(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ConvoyPlan(List.of(), R)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ConvoyPlan(List.of(2, 0), R)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ConvoyPlan.splits(13)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ConvoyPlan(List.of(1), R).simulate(1, 1, 0))
                .isInstanceOf(IllegalArgumentException.class);
        ConvoyQuest q = new ConvoyQuest(R);
        assertThatThrownBy(() -> q.choose(List.of(3, 2))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> q.sail(1)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void wiseSplitSailsAndSettles() {
        ConvoyQuest q = new ConvoyQuest(R);
        assertThat(q.keeperLine()).contains("[3, 3]");
        assertThat(q.choose(List.of(3, 3))).isCloseTo(q.bestChance(), within(1e-12));
        assertThat(q.wise()).isTrue();
        assertThat(q.keeperLine()).contains("split it the same");
        assertThatThrownBy(() -> q.choose(List.of(6))).isInstanceOf(IllegalStateException.class);
        int arrived = q.sail(9);
        assertThat(arrived).isEqualTo(q.arrived())
                .isEqualTo(new ConvoyPlan(List.of(3, 3), R).sail(new OddsRng(9)));
        assertThat(q.stage()).isEqualTo(arrived >= ConvoyQuest.NEEDED
                ? ConvoyQuest.Stage.SEEDED : ConvoyQuest.Stage.SHORT);
        assertThat(q.keeperLine()).containsAnyOf("island will grow", "belt kept the rest");
    }

    @Test
    void loneArksGetTheKeepersFrown() {
        ConvoyQuest q = new ConvoyQuest(R);
        q.choose(List.of(1, 1, 1, 1, 1, 1));
        assertThat(q.wise()).isFalse();
        assertThat(q.keeperLine()).contains("the chalk had");
        boolean seeded = false;
        boolean shortfall = false;
        for (long s = 0; s < 200 && !(seeded && shortfall); s++) {
            int a = new ConvoyPlan(List.of(1, 1, 1, 1, 1, 1), R).sail(new OddsRng(s));
            seeded |= a >= ConvoyQuest.NEEDED;
            shortfall |= a < ConvoyQuest.NEEDED;
        }
        assertThat(seeded).isTrue();
        assertThat(shortfall).isTrue();
    }
}
