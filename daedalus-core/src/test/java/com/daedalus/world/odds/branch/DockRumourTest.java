// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.branch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class DockRumourTest {

    private static final BranchingOdds DOCKS = BranchingOdds.binomial(3, 0.4);

    @Test
    void extinctionIsTheSmallestFixedPoint() {
        assertThat(DOCKS.mean()).isCloseTo(1.2, within(1e-12));
        assertThat(DOCKS.offspring()).hasSize(4);
        assertThat(DOCKS.generating(1.0)).isCloseTo(1.0, within(1e-12));
        double q = DOCKS.extinction();
        assertThat(q).isCloseTo(0.557189138830738, within(1e-9));
        assertThat(DOCKS.generating(q)).isCloseTo(q, within(1e-9));
        assertThat(Math.pow(0.6 + 0.4 * q, 3)).isCloseTo(q, within(1e-9));
        BranchingOdds coin = new BranchingOdds(new double[] {0.25, 0.25, 0.5});
        assertThat(coin.extinction()).isCloseTo(0.5, within(1e-9));
        assertThat(new BranchingOdds(new double[] {0, 1}).extinction()).isZero();
        BranchingOdds weak = BranchingOdds.binomial(2, 0.4);
        assertThat(weak.extinction()).isEqualTo(1.0);
        assertThat(weak.expectedTotal()).isCloseTo(5.0, within(1e-12));
        assertThat(DOCKS.expectedTotal()).isInfinite();
    }

    @Test
    void generationsAndSeeds() {
        assertThat(DOCKS.extinctBy(0)).isZero();
        assertThat(DOCKS.extinctBy(1)).isCloseTo(0.216, within(1e-12));
        assertThat(DOCKS.extinctBy(8)).isCloseTo(0.5108897919749358, within(1e-12));
        for (int g = 1; g < 30; g++) {
            assertThat(DOCKS.extinctBy(g)).isGreaterThanOrEqualTo(DOCKS.extinctBy(g - 1));
            assertThat(DOCKS.extinctBy(g)).isLessThanOrEqualTo(DOCKS.extinction() + 1e-12);
        }
        assertThat(DOCKS.aliveAt(8, 4)).isCloseTo(0.9318746258077144, within(1e-12));
        assertThat(DOCKS.survival(4)).isCloseTo(0.9036147520552317, within(1e-9));
        assertThat(DOCKS.survival(3)).isCloseTo(0.827015206816427, within(1e-9));
        assertThat(DOCKS.survival(5)).isCloseTo(0.9462951867016673, within(1e-9));
        assertThat(DOCKS.extinction() - DOCKS.extinctBy(60)).isBetween(0.0, 1e-4);
        assertThat(DOCKS.seedsFor(0.90, 10)).isEqualTo(4);
        assertThat(BranchingOdds.binomial(2, 0.4).seedsFor(0.5, 10)).isEqualTo(-1);
    }

    @Test
    void seededTellingsAgreeWithTheExactOdds() {
        double[] est = RumourSpread.simulate(DOCKS, 1, 4, 2026, 20_000);
        assertThat(est[0]).isCloseTo(DOCKS.aliveAt(4, 1), within(0.015));
        assertThat(DOCKS.aliveAt(4, 1)).isBetween(est[1], est[2]);
        double[] tide = RumourSpread.simulate(DOCKS, 4, 8, 11, 4_000);
        assertThat(DOCKS.aliveAt(8, 4)).isBetween(tide[1], tide[2]);
        double[] forever = RumourSpread.simulate(DOCKS, 1, 30, 17, 4_000);
        assertThat(DOCKS.survival(1)).isBetween(forever[1], forever[2]);
        assertThat(est[1]).isLessThanOrEqualTo(est[0]);
        assertThat(est[2]).isGreaterThanOrEqualTo(est[0]);
        assertThat(RumourSpread.simulate(DOCKS, 1, 4, 2026, 20_000)).containsExactly(est);
        double[] two = RumourSpread.simulate(DOCKS, 2, 6, 5, 10_000);
        assertThat(two[0]).isCloseTo(DOCKS.aliveAt(6, 2), within(0.02));
        long[] gen = RumourSpread.spread(DOCKS, 3, 5, new OddsRng(9));
        assertThat(gen).hasSize(6);
        assertThat(gen[0]).isEqualTo(3);
        long[] boom = RumourSpread.spread(BranchingOdds.binomial(64, 1.0), 1, 6, new OddsRng(1));
        assertThat(boom[6]).isEqualTo(RumourSpread.CROWD);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new BranchingOdds(new double[] {0.5, 0.4})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new BranchingOdds(new double[0])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new BranchingOdds(new double[] {-0.1, 1.1})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BranchingOdds.binomial(65, 0.5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BranchingOdds.binomial(3, 1.5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DOCKS.extinctBy(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DOCKS.survival(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DOCKS.seedsFor(1.0, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RumourSpread.spread(DOCKS, 0, 3, new OddsRng(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RumourSpread.simulate(DOCKS, 1, 3, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        DockRumourQuest q = new DockRumourQuest();
        assertThatThrownBy(() -> q.spread(7, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questFollowsTheWord() {
        DockRumourQuest q = new DockRumourQuest();
        assertThat(q.stage()).isEqualTo(DockRumourQuest.Stage.PLANNING);
        assertThat(q.tellers()).isEmpty();
        assertThat(q.advised()).isEqualTo(4);
        assertThat(q.chance(1)).isCloseTo(0.4891102080250642, within(1e-12));
        assertThat(q.keeperLine()).contains("49%").contains("grog for 4").contains("93%");
        int spread = 0;
        for (long s = 0; s < 300; s++) {
            DockRumourQuest t = new DockRumourQuest();
            DockRumourQuest.Stage end = t.spread(4, s);
            assertThat(t.stage()).isEqualTo(end);
            assertThat(t.tellers()).hasSize(DockRumourQuest.GENERATIONS + 1);
            if (end == DockRumourQuest.Stage.SPREAD) {
                spread++;
                assertThat(t.keeperLine()).contains("Every dock knows");
            } else {
                assertThat(t.keeperLine()).contains("died out by telling");
            }
        }
        assertThat(spread).isBetween(265, 295);
        q.spread(1, 3);
        assertThatThrownBy(() -> q.spread(1, 3)).isInstanceOf(IllegalStateException.class);
    }
}
