// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.dice;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class StormDiceTest {

    @Test
    void twoDiceWays() {
        int total = 0;
        for (int s = 2; s <= 12; s++) {
            total += DiceMath.ways(s);
        }
        assertThat(total).isEqualTo(36);
        assertThat(DiceMath.ways(7)).isEqualTo(6);
        assertThat(DiceMath.ways(1)).isZero();
        assertThat(DiceMath.chance(2)).isCloseTo(1 / 36.0, within(1e-12));
    }

    @Test
    void passLineIs244Over495() {
        assertThat(DiceMath.passWinFraction()).containsExactly(244, 495);
        assertThat(DiceMath.passWin()).isCloseTo(244 / 495.0, within(1e-15));
        assertThat(DiceMath.pointMade(4)).isCloseTo(1 / 3.0, within(1e-12));
        assertThat(DiceMath.pointMade(6)).isCloseTo(5 / 11.0, within(1e-12));
    }

    @Test
    void trueOddsAreFair() {
        for (int p : new int[] {4, 5, 6, 8, 9, 10}) {
            double made = DiceMath.pointMade(p);
            double ev = made * DiceMath.trueOdds(p) - (1 - made);
            assertThat(ev).as("point %d", p).isCloseTo(0.0, within(1e-12));
        }
        assertThat(DiceMath.trueOdds(4)).isEqualTo(2.0);
        assertThat(DiceMath.trueOdds(5)).isEqualTo(1.5);
        assertThat(DiceMath.trueOdds(6)).isCloseTo(1.2, within(1e-12));
    }

    @Test
    void oddsSpreadTheEdgeThinner() {
        assertThat(DiceMath.edgePerHerbWagered(0)).isCloseTo(7 / 495.0, within(1e-12));
        assertThat(DiceMath.edgePerHerbWagered(3)).isCloseTo(7 / 495.0 / 3, within(1e-12));
        assertThat(DiceMath.edgePerHerbWagered(1)).isLessThan(DiceMath.edgePerHerbWagered(0));
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> DiceMath.pointMade(7)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DiceMath.trueOdds(11)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DiceMath.edgePerHerbWagered(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StormDice.play(new OddsRng(1), -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StormDice.passWinEstimate(1, 0)).isInstanceOf(IllegalArgumentException.class);
        StormDiceQuest q = new StormDiceQuest();
        assertThatThrownBy(() -> q.shoot(4, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void seededDiceAgreeWithTheExactOdds() {
        double[] est = StormDice.passWinEstimate(2026, 40_000);
        assertThat(DiceMath.passWin()).isBetween(est[1], est[2]);
        assertThat(StormDice.passWinEstimate(2026, 40_000)).containsExactly(est);
        OddsRng rng = new OddsRng(3);
        for (int i = 0; i < 1_000; i++) {
            int d = StormDice.die(rng);
            assertThat(d).isBetween(1, 6);
        }
    }

    @Test
    void roundsPayPassAndOddsConsistently() {
        for (long s = 0; s < 300; s++) {
            StormDice.Round r = StormDice.play(new OddsRng(s), 2);
            if (r.point() == 0) {
                assertThat(r.rolls()).isEqualTo(1);
                assertThat(Math.abs(r.net())).isEqualTo(1.0);
            } else if (r.won()) {
                assertThat(r.net()).isCloseTo(1 + 2 * DiceMath.trueOdds(r.point()), within(1e-12));
            } else {
                assertThat(r.net()).isEqualTo(-3.0);
            }
        }
    }

    @Test
    void fullOddsPassesTheQuest() {
        StormDiceQuest q = new StormDiceQuest();
        assertThat(q.keeperLine()).contains("244 in 495").contains("1.41%");
        double net = q.shoot(StormDiceQuest.MAX_ODDS, 77);
        assertThat(q.net()).isEqualTo(net);
        assertThat(q.wins()).isBetween(0, StormDiceQuest.ROUNDS);
        assertThat(q.passed()).isTrue();
        assertThat(q.keeperLine()).contains("Full odds").contains("0.47%");
        assertThatThrownBy(() -> q.shoot(0, 1)).isInstanceOf(IllegalStateException.class);
        StormDiceQuest flat = new StormDiceQuest();
        flat.shoot(0, 77);
        assertThat(flat.passed()).isFalse();
        assertThat(flat.keeperLine()).contains("free odds");
        assertThat(flat.wins()).isEqualTo(q.wins());
    }
}
