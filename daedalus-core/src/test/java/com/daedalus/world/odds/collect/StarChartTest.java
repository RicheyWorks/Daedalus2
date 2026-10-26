// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.collect;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class StarChartTest {

    private static final ChartFragments EIGHT = new ChartFragments(8);

    @Test
    void classicCollectorNumbers() {
        assertThat(EIGHT.fragments()).isEqualTo(8);
        assertThat(EIGHT.expectedCrates()).isCloseTo(21.742857142857144, within(1e-12));
        assertThat(EIGHT.completeNoTrade(7)).isZero();
        assertThat(EIGHT.completeNoTrade(8)).isCloseTo(40320.0 / Math.pow(8, 8), within(1e-12));
        assertThat(EIGHT.completeNoTrade(33)).isCloseTo(0.9045203642493629, within(1e-12));
        assertThat(EIGHT.expectedMissing(0)).isEqualTo(8.0);
        assertThat(EIGHT.expectedMissing(16)).isCloseTo(8 * Math.pow(7.0 / 8, 16), within(1e-12));
        assertThat(new ChartFragments(1).expectedCrates()).isEqualTo(1.0);
    }

    @Test
    void walkAgreesWithInclusionExclusion() {
        for (int c = 0; c <= 60; c += 5) {
            assertThat(EIGHT.completeWithTradeIn(c, 0)).isCloseTo(EIGHT.completeNoTrade(c), within(1e-12));
        }
        for (int c = 10; c <= 40; c += 10) {
            assertThat(EIGHT.completeWithTradeIn(c, 3)).isGreaterThan(EIGHT.completeNoTrade(c));
            assertThat(EIGHT.completeWithTradeIn(c, 2)).isGreaterThanOrEqualTo(EIGHT.completeWithTradeIn(c, 3));
        }
    }

    @Test
    void theKeepersCounterCutsTheHaul() {
        assertThat(EIGHT.smallestCrates(0.90, 0, 120)).isEqualTo(33);
        assertThat(EIGHT.smallestCrates(0.90, 3, 120)).isEqualTo(13);
        assertThat(EIGHT.completeWithTradeIn(13, 3)).isCloseTo(0.9003195399418473, within(1e-12));
        assertThat(EIGHT.completeWithTradeIn(12, 3)).isLessThan(0.90);
        assertThat(EIGHT.smallestCrates(0.90, 2, 120)).isEqualTo(11);
        assertThat(EIGHT.smallestCrates(0.99, 0, 20)).isEqualTo(-1);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new ChartFragments(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ChartFragments(31)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EIGHT.completeNoTrade(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EIGHT.completeWithTradeIn(5, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EIGHT.smallestCrates(1.0, 0, 10)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrateHaul.open(0, 1, new OddsRng(1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrateHaul.simulate(8, 5, 0, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        ChartCollectorQuest q = new ChartCollectorQuest();
        assertThatThrownBy(() -> q.haul(0, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void seededCratesAgreeWithTheExactOdds() {
        double[] est = CrateHaul.simulate(8, 13, 3, 2026, 20_000);
        assertThat(est[0]).isCloseTo(EIGHT.completeWithTradeIn(13, 3), within(0.01)).isBetween(est[1], est[2]);
        double[] plain = CrateHaul.simulate(8, 20, 0, 7, 20_000);
        assertThat(plain[0]).isCloseTo(EIGHT.completeNoTrade(20), within(0.015));
        assertThat(CrateHaul.simulate(8, 13, 3, 2026, 20_000)).containsExactly(est);
        CrateHaul h = CrateHaul.open(8, 40, new OddsRng(5));
        assertThat(h.distinct() + h.duplicates()).isEqualTo(40);
        assertThat(CrateHaul.open(8, 0, new OddsRng(5)).full(8, 3)).isFalse();
    }

    @Test
    void questFollowsTheHaul() {
        ChartCollectorQuest q = new ChartCollectorQuest();
        assertThat(q.advised()).isEqualTo(13);
        assertThat(q.advisedNoTrade()).isEqualTo(33);
        assertThat(q.traded()).isZero();
        assertThat(q.keeperLine()).contains("33 crates").contains("13 gives 90%");
        int charted = 0;
        for (long s = 0; s < 100; s++) {
            ChartCollectorQuest t = new ChartCollectorQuest();
            ChartCollectorQuest.Stage st = t.haul(13, s);
            assertThat(t.stage()).isEqualTo(st);
            if (st == ChartCollectorQuest.Stage.CHARTED) {
                charted++;
                assertThat(t.keeperLine()).contains("Charted").contains(t.traded() + " traded");
            } else {
                assertThat(t.traded()).isZero();
                assertThat(t.keeperLine()).contains("skiff has sailed");
            }
        }
        assertThat(charted).isBetween(80, 99);
        assertThatThrownBy(() -> q.chance(-1)).isInstanceOf(IllegalArgumentException.class);
        q.haul(120, 3);
        assertThat(q.stage()).isEqualTo(ChartCollectorQuest.Stage.CHARTED);
        assertThatThrownBy(() -> q.haul(5, 1)).isInstanceOf(IllegalStateException.class);
    }
}
