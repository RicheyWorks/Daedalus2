// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.walk;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import java.util.Arrays;
import org.junit.jupiter.api.Test;

class LifeboatDriftTest {

    private static final DriftOdds WRECK = new DriftOdds(10, 0.45);

    @Test
    void closedFormRuinOdds() {
        assertThat(WRECK.harbour()).isEqualTo(10);
        assertThat(WRECK.shoreward()).isEqualTo(0.45);
        assertThat(WRECK.harbourChance(0)).isZero();
        assertThat(WRECK.harbourChance(10)).isCloseTo(1.0, within(1e-15));
        assertThat(WRECK.harbourChance(4)).isCloseTo(0.19126596131543716, within(1e-12));
        assertThat(WRECK.expectedWatches(4)).isCloseTo(20.873403868456275, within(1e-9));
        assertThat(WRECK.expectedWatches(0)).isCloseTo(0.0, within(1e-12));
        DriftOdds fair = new DriftOdds(20, 0.5);
        assertThat(fair.harbourChance(7)).isCloseTo(0.35, within(1e-15));
        assertThat(fair.expectedWatches(7)).isEqualTo(91.0);
    }

    @Test
    void positionSolversAgreeWithClosedForms() {
        double[] up = new double[11];
        Arrays.fill(up, 0.45);
        double[] v = DriftOdds.harbourChancesAt(up);
        double[] t = DriftOdds.expectedWatchesAt(up);
        for (int k = 0; k <= 10; k++) {
            assertThat(v[k]).isCloseTo(WRECK.harbourChance(k), within(1e-12));
            assertThat(t[k]).isCloseTo(WRECK.expectedWatches(k), within(1e-9));
        }
        double[] mixed = {0, 0.3, 0.7, 0.5, 0.2, 0.9, 0.6, 0};
        double[] mv = DriftOdds.harbourChancesAt(mixed);
        double[] mt = DriftOdds.expectedWatchesAt(mixed);
        for (int k = 1; k < 7; k++) {
            assertThat(mv[k]).isCloseTo(mixed[k] * mv[k + 1] + (1 - mixed[k]) * mv[k - 1], within(1e-12));
            assertThat(mt[k]).isCloseTo(1 + mixed[k] * mt[k + 1] + (1 - mixed[k]) * mt[k - 1], within(1e-9));
        }
        assertThat(mv[0]).isZero();
        assertThat(mv[7]).isEqualTo(1.0);
    }

    @Test
    void rationsBuyHarbourOddsAtTheEnds() {
        LifeboatDrift boat = new LifeboatDrift(10, 0.45, 0.20, 3);
        assertThat(boat.harbour()).isEqualTo(10);
        assertThat(boat.rations()).isEqualTo(3);
        assertThat(boat.rowChance()).isCloseTo(0.65, within(1e-15));
        assertThat(boat.chance(4, 0)).isCloseTo(WRECK.harbourChance(4), within(1e-15));
        assertThat(boat.chance(4, 1)).isCloseTo(0.219272011317, within(1e-9));
        assertThat(boat.chance(4, 2)).isCloseTo(0.249541176469, within(1e-9));
        assertThat(boat.chance(4, 3)).isCloseTo(0.282256334766, within(1e-9));
        assertThat(boat.plan(0)).isEqualTo("...........");
        assertThat(boat.plan(1)).isEqualTo(".R.......R.");
        assertThat(boat.plan(3)).isEqualTo(".RRR...RRR.");
        assertThat(boat.rows(4, 3)).isFalse();
        assertThat(boat.rows(1, 1)).isTrue();
        for (int k = 1; k < 10; k++) {
            for (int r = 1; r <= 3; r++) {
                assertThat(boat.chance(k, r)).isGreaterThanOrEqualTo(boat.chance(k, r - 1));
            }
        }
        LifeboatDrift lazy = new LifeboatDrift(10, 0.45, 0.0, 2);
        assertThat(lazy.plan(2)).doesNotContain("R");
        assertThat(lazy.chance(4, 2)).isCloseTo(WRECK.harbourChance(4), within(1e-12));
        LifeboatDrift galley = new LifeboatDrift(10, 0.45, 0.20, 30);
        assertThat(galley.chance(4, 30)).isLessThan(new DriftOdds(10, 0.65).harbourChance(4));
        assertThat(new LifeboatDrift(10, 0.9, 0.5, 1).rowChance()).isEqualTo(LifeboatDrift.MAX_ROW_CHANCE);
    }

    @Test
    void seededVoyagesAgreeWithTheTable() {
        LifeboatDrift boat = new LifeboatDrift(10, 0.45, 0.20, 3);
        double[] est = boat.simulate(4, 3, 2026, 20_000);
        assertThat(est[0]).isCloseTo(boat.chance(4, 3), within(0.015));
        assertThat(est[1]).isLessThanOrEqualTo(est[0]);
        assertThat(est[2]).isGreaterThanOrEqualTo(est[0]);
        assertThat(boat.simulate(4, 3, 2026, 20_000)).containsExactly(est);
        double[] drift = boat.simulate(4, 0, 9, 20_000);
        assertThat(drift[0]).isCloseTo(WRECK.harbourChance(4), within(0.015));
        assertThat(boat.sail(10, 0, new OddsRng(1))).isTrue();
        assertThat(boat.sail(0, 3, new OddsRng(1))).isFalse();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new DriftOdds(1, 0.5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new DriftOdds(10, 1.0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> WRECK.harbourChance(11)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DriftOdds.harbourChancesAt(null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DriftOdds.expectedWatchesAt(new double[] {0, 0, 0}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LifeboatDrift(41, 0.45, 0.2, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LifeboatDrift(10, 0.45, 1.0, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LifeboatDrift(10, 0.45, 0.2, 31)).isInstanceOf(IllegalArgumentException.class);
        LifeboatDrift boat = new LifeboatDrift(10, 0.45, 0.2, 1);
        assertThatThrownBy(() -> boat.chance(4, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> boat.simulate(4, 1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questFollowsTheKeeper() {
        LifeboatQuest q = new LifeboatQuest();
        assertThat(q.stage()).isEqualTo(LifeboatQuest.Stage.ADRIFT);
        assertThat(q.cable()).isEqualTo(4);
        assertThat(q.rations()).isEqualTo(3);
        assertThat(q.plan()).isEqualTo(".RRR...RRR.");
        assertThat(q.driftOnlyChance()).isCloseTo(0.19126596131543716, within(1e-12));
        assertThat(q.bestChance()).isCloseTo(0.282256334766, within(1e-9));
        assertThat(q.adviseRow()).isFalse();
        assertThat(q.keeperLine()).contains("Drift alone and it's 19%").contains("it's 28%").contains("Rest the oars.");
        int ashore = 0;
        for (long s = 0; s < 400; s++) {
            LifeboatQuest t = new LifeboatQuest();
            LifeboatQuest.Stage end = t.followKeeper(s);
            assertThat(t.stage()).isEqualTo(end).isNotEqualTo(LifeboatQuest.Stage.ADRIFT);
            assertThat(t.watches()).isPositive();
            if (end == LifeboatQuest.Stage.HARBOUR) {
                ashore++;
                assertThat(t.keeperLine()).contains("Ashore");
            } else {
                assertThat(t.keeperLine()).contains("Swim for it");
            }
        }
        assertThat(ashore).isBetween(80, 150);
        LifeboatQuest rower = new LifeboatQuest();
        OddsRng rng = new OddsRng(11);
        for (int i = 0; i < 3 && rower.stage() == LifeboatQuest.Stage.ADRIFT; i++) {
            rower.watch(true, rng);
        }
        if (rower.stage() == LifeboatQuest.Stage.ADRIFT) {
            assertThat(rower.rations()).isZero();
            assertThatThrownBy(() -> rower.watch(true, rng)).isInstanceOf(IllegalStateException.class);
        }
        LifeboatQuest done = new LifeboatQuest();
        done.followKeeper(1);
        assertThatThrownBy(() -> done.watch(false, rng)).isInstanceOf(IllegalStateException.class);
    }
}
