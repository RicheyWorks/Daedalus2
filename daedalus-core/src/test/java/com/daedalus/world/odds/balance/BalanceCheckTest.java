// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.odds.OddsRng;
import java.util.List;
import org.junit.jupiter.api.Test;

class BalanceCheckTest {

    private static final int TRIALS = 1500;

    /** A stub game with fixed win probabilities per difficulty, for testing the flags alone. */
    private static BalanceGame stub(double easy, double normal, double hard) {
        return new BalanceGame() {
            @Override
            public String id() {
                return "stub";
            }

            @Override
            public List<String> difficulties() {
                return List.of("easy", "normal", "hard");
            }

            @Override
            public boolean supports(String d) {
                return true;
            }

            @Override
            public SessionOutcome play(String d, OddsRng rng) {
                double p = "easy".equals(d) ? easy : "normal".equals(d) ? normal : hard;
                return new SessionOutcome(rng.chance(p), 1);
            }
        };
    }

    @Test
    void aFixedSeedGivesTheSameReport() {
        List<ModeResult> a = BalanceReport.runAll(7L, 300);
        List<ModeResult> b = BalanceReport.runAll(7L, 300);
        assertThat(a).hasSize(6);
        for (int i = 0; i < a.size(); i++) {
            assertThat(a.get(i).wins()).isEqualTo(b.get(i).wins());
            assertThat(a.get(i).meanScore()).isEqualTo(b.get(i).meanScore());
            assertThat(a.get(i).flags()).isEqualTo(b.get(i).flags());
        }
        OddsRng r1 = OddsRng.forTrial(3, 9);
        OddsRng r2 = OddsRng.forTrial(3, 9);
        SessionOutcome s1 = new ShardringBalance().play("easy", r1);
        SessionOutcome s2 = new ShardringBalance().play("easy", r2);
        assertThat(s1.score()).isEqualTo(s2.score());
        assertThat(s1.won()).isEqualTo(s2.won());
    }

    @Test
    void bandFlagsFireOnlyWhenTheWholeIntervalIsOutside() {
        List<ModeResult> r = new BalanceCheck().run(stub(0.80, 0.60, 0.30), 1, TRIALS);
        assertThat(r).allMatch(m -> !m.flagged());
        List<ModeResult> bad = new BalanceCheck().run(stub(0.40, 0.995, 0.02), 1, TRIALS);
        assertThat(bad.get(0).flags()).contains(BalanceFlag.TOO_HARD);
        assertThat(bad.get(1).flags()).contains(BalanceFlag.TOO_EASY);
        assertThat(bad.get(2).flags()).contains(BalanceFlag.TOO_HARD);
        for (ModeResult m : bad) {
            assertThat(m.low()).isLessThanOrEqualTo(m.winRate());
            assertThat(m.high()).isGreaterThanOrEqualTo(m.winRate());
        }
    }

    @Test
    void aHarderModeThatIsEasierIsFlaggedNotMonotonic() {
        List<ModeResult> r = new BalanceCheck().run(stub(0.50, 0.70, 0.30), 1, TRIALS);
        assertThat(r.get(1).flags()).contains(BalanceFlag.NOT_MONOTONIC);
        assertThat(r.get(2).flags()).doesNotContain(BalanceFlag.NOT_MONOTONIC);
        List<ModeResult> close = new BalanceCheck().run(stub(0.60, 0.61, 0.30), 1, TRIALS);
        assertThat(close.get(1).flags()).doesNotContain(BalanceFlag.NOT_MONOTONIC);
    }

    @Test
    void customBandsAndBadInputs() {
        BalanceCheck c = new BalanceCheck(new BalanceBand(0, 1)).band("hard", new BalanceBand(0.5, 1));
        List<ModeResult> r = c.run(stub(0.9, 0.9, 0.1), 2, 500);
        assertThat(r.get(0).flagged()).isFalse();
        assertThat(r.get(2).flags()).containsExactly(BalanceFlag.TOO_HARD);
        assertThatThrownBy(() -> new BalanceBand(0.6, 0.5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> c.run(stub(1, 1, 1), 1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CairnwellBalance(0, 1, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void shardringFollowsTheSourceRules() {
        int[] ring = {0, 0, -1, 1, -1, -1, -1, 0};
        assertThat(ShardringBalance.greedy(ring, 0)).isEqualTo(2);
        ring[2] = 0;
        assertThat(ShardringBalance.runAt(ring, 2)).containsExactlyInAnyOrder(7, 0, 1, 2);
        int[] empty = {-1, -1, -1};
        assertThat(ShardringBalance.greedy(empty, 1)).isZero();
        List<ModeResult> r = new BalanceCheck().run(new ShardringBalance(), BalanceReport.SEED, TRIALS);
        assertThat(r.get(0).winRate()).isBetween(0.45, 0.60);
        assertThat(r.get(1).winRate()).isLessThan(0.06);
        assertThat(r.get(2).winRate()).isLessThan(0.01);
        assertThat(r).allMatch(m -> m.flags().contains(BalanceFlag.TOO_HARD));
        assertThat(r.get(0).meanScore()).isGreaterThan(r.get(1).meanScore());
    }

    @Test
    void cairnwellShipsTwoWellsAndNoHard() {
        CairnwellBalance g = new CairnwellBalance();
        assertThat(g.supports("hard")).isFalse();
        assertThatThrownBy(() -> g.play("hard", new OddsRng(1))).isInstanceOf(IllegalArgumentException.class);
        assertThat(CairnwellBalance.lowest(new int[] {2, 1, 1, 3}, 3)).isEqualTo(2);
        List<ModeResult> r = new BalanceCheck().run(g, BalanceReport.SEED, TRIALS);
        assertThat(r.get(2).flags()).containsExactly(BalanceFlag.MISSING_MODE);
        assertThat(r.get(0).flags()).contains(BalanceFlag.TOO_EASY);
        assertThat(r.get(1).flags()).contains(BalanceFlag.TOO_EASY);
        List<ModeResult> sloppy = new BalanceCheck().run(new CairnwellBalance(20, 6, 0.75), BalanceReport.SEED, TRIALS);
        assertThat(sloppy.get(1).flags()).contains(BalanceFlag.NOT_MONOTONIC);
        SessionOutcome lost = new CairnwellBalance(20, 6, 1.0).play("normal", new OddsRng(5));
        assertThat(lost.score() % 10).isZero();
    }

    @Test
    void reportPrintsEveryMode() {
        assertThat(BalanceReport.games()).extracting(BalanceGame::id).containsExactly("shardring", "cairnwell");
        assertThat(BalanceReport.runAll(1, 50).get(5).toString()).contains("not in source");
        assertThat(BalanceReport.runAll(1, 50).get(0).toString()).contains("shardring/easy: win");
        BalanceReport.main(new String[0]);
    }
}
