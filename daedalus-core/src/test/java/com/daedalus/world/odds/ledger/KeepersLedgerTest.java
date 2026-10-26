// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.ledger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class KeepersLedgerTest {

    @Test
    void kellyFractionAndEdge() {
        assertThat(KellyStake.fraction(0.5, 3.0)).isCloseTo(0.25, within(1e-12));
        assertThat(KellyStake.edge(0.5, 3.0)).isCloseTo(0.5, within(1e-12));
        assertThat(KellyStake.fraction(0.5, 2.0)).isZero();
        assertThat(KellyStake.fraction(0.4, 2.0)).isZero();
        assertThat(KellyStake.fraction(0.9, 1.0)).isZero();
    }

    @Test
    void adviceIsShadedCappedAndFloored() {
        assertThat(KellyStake.advise(20, 0.5, 3.0)).isEqualTo(2);
        assertThat(KellyStake.advise(100, 0.5, 3.0, 1.0, 0.25)).isEqualTo(25);
        assertThat(KellyStake.advise(100, 0.5, 3.0, 1.0, 0.10)).isEqualTo(10);
        assertThat(KellyStake.advise(1, 0.5, 3.0)).isEqualTo(1);
        assertThat(KellyStake.advise(0, 0.5, 3.0)).isZero();
        assertThat(KellyStake.advise(50, 0.4, 2.0)).isZero();
    }

    @Test
    void kellyRejectsBadInput() {
        assertThatThrownBy(() -> KellyStake.fraction(1.5, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KellyStake.fraction(0.5, Double.NaN)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KellyStake.edge(0.5, Double.POSITIVE_INFINITY))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KellyStake.advise(-1, 0.5, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KellyStake.advise(10, 0.5, 2, 0, 0.25)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KellyStake.advise(10, 0.5, 2, 1, 1.5)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void ledgerSettlesAndTracksDrawdown() {
        HerbLedger l = new HerbLedger(20);
        assertThat(l.settle("G18 parlay", 5, 3.0, true)).isEqualTo(30);
        assertThat(l.settle("G35 cup", 10, 2.0, false)).isEqualTo(20);
        assertThat(l.peak()).isEqualTo(30);
        assertThat(l.maxDrawdown()).isCloseTo(1.0 / 3, within(1e-12));
        assertThat(l.wins()).isEqualTo(1);
        assertThat(l.start()).isEqualTo(20);
        assertThat(l.history()).hasSize(2);
        assertThat(l.history().get(0).game()).isEqualTo("G18 parlay");
        assertThat(l.history().get(1).balanceAfter()).isEqualTo(20);
        assertThat(l.broke()).isFalse();
        assertThat(l.settle("G47 route", 7, 2.5, true)).isEqualTo(20 + 17 - 7);
    }

    @Test
    void ledgerRejectsBadWagers() {
        assertThatThrownBy(() -> new HerbLedger(0)).isInstanceOf(IllegalArgumentException.class);
        HerbLedger l = new HerbLedger(5);
        assertThatThrownBy(() -> l.settle("x", 6, 2, true)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> l.settle("x", 0, 2, true)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> l.settle("x", 1, 0.9, true)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> l.settle("x", 1, Double.POSITIVE_INFINITY, true))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(l.settle("x", 5, 2, false)).isZero();
        assertThat(l.broke()).isTrue();
    }

    @Test
    void overbettingRaisesRuinAndIsSeeded() {
        RuinOdds.Plan half = new RuinOdds.Plan(20, 40, 30, 0.5, 3.0, KellyStake.HALF, KellyStake.CAP);
        RuinOdds.Plan reckless = new RuinOdds.Plan(20, 40, 30, 0.5, 3.0, 4.0, 1.0);
        RuinOdds a = RuinOdds.simulate(half, 7, 4_000);
        RuinOdds b = RuinOdds.simulate(reckless, 7, 4_000);
        assertThat(b.chance(RuinOdds.Outcome.RUINED)).isGreaterThan(a.chance(RuinOdds.Outcome.RUINED) + 0.2);
        assertThat(b.chance(RuinOdds.Outcome.RUINED)).isCloseTo(0.5, within(0.05));
        RuinOdds again = RuinOdds.simulate(half, 7, 4_000);
        int sum = 0;
        for (RuinOdds.Outcome o : RuinOdds.Outcome.values()) {
            assertThat(again.count(o)).isEqualTo(a.count(o));
            sum += a.count(o);
            double[] ci = a.interval(o);
            assertThat(a.chance(o)).isBetween(ci[0], ci[1]);
        }
        assertThat(sum).isEqualTo(a.trials());
        assertThat(a.chance(RuinOdds.Outcome.DOUBLED)).isGreaterThan(0.5);
    }

    @Test
    void noEdgeMeansTheKeeperSaysDoNotBet() {
        RuinOdds.Plan none = new RuinOdds.Plan(20, 40, 10, 0.4, 2.0, KellyStake.HALF, KellyStake.CAP);
        assertThat(none.play(new OddsRng(1))).isEqualTo(RuinOdds.Outcome.EXPIRED);
        assertThat(RuinOdds.simulate(none, 1, 50).count(RuinOdds.Outcome.EXPIRED)).isEqualTo(50);
        assertThatThrownBy(() -> new RuinOdds.Plan(20, 20, 10, 0.5, 3, 0.5, 0.25))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RuinOdds.simulate(none, 1, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void disciplinedDoublingEarnsTheKeepersMark() {
        KeepersLedgerQuest q = new KeepersLedgerQuest();
        assertThat(q.keeperLine()).contains("20 herbs").contains("12 wagers left");
        assertThat(q.advice(0.6, 3.0)).isEqualTo(4);
        while (q.stage() == KeepersLedgerQuest.Stage.OPEN) {
            q.wager("G47 route", q.advice(0.6, 3.0), 0.6, 3.0, true);
        }
        assertThat(q.stage()).isEqualTo(KeepersLedgerQuest.Stage.DOUBLED);
        assertThat(q.balance()).isEqualTo(52);
        assertThat(q.disciplined()).isEqualTo(3);
        assertThat(q.history()).hasSize(3);
        assertThat(q.keepersMark()).isTrue();
        assertThat(q.keeperLine()).contains("Keeper's Mark");
        assertThatThrownBy(() -> q.wager("x", 1, 0.5, 2, true)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void recklessDoublingGetsNoMark() {
        KeepersLedgerQuest q = new KeepersLedgerQuest();
        assertThat(q.wager("G35 cup", 20, 0.6, 3.0, true)).isEqualTo(KeepersLedgerQuest.Stage.DOUBLED);
        assertThat(q.keepersMark()).isFalse();
        assertThat(q.keeperLine()).contains("Lucky or good");
    }

    @Test
    void brokeAndOutOfWagersEndTheLedger() {
        KeepersLedgerQuest broke = new KeepersLedgerQuest();
        assertThat(broke.wager("G18 parlay", 20, 0.3, 2.0, false)).isEqualTo(KeepersLedgerQuest.Stage.BROKE);
        assertThat(broke.keeperLine()).contains("empty");
        KeepersLedgerQuest slow = new KeepersLedgerQuest();
        for (int i = 0; i < KeepersLedgerQuest.MAX_WAGERS; i++) {
            slow.wager("G18 parlay", 1, 0.5, 1.0, true);
        }
        assertThat(slow.stage()).isEqualTo(KeepersLedgerQuest.Stage.OUT_OF_WAGERS);
        assertThat(slow.disciplined()).isZero();
        assertThat(slow.keeperLine()).contains("20 herbs");
    }
}
