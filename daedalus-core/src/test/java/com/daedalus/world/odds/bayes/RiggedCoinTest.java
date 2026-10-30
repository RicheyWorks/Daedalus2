// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.bayes;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;

class RiggedCoinTest {

    private static Sprt sprt() {
        return new Sprt(0.5, 0.7, 0.05, 0.05);
    }

    @Test
    void waldThresholdsAndSteps() {
        Sprt s = sprt();
        assertThat(s.upper()).isCloseTo(Math.log(19), within(1e-12));
        assertThat(s.lower()).isCloseTo(-Math.log(19), within(1e-12));
        for (int i = 0; i < 8; i++) {
            assertThat(s.record(true)).isEqualTo(Sprt.Decision.CONTINUE);
        }
        assertThat(s.record(true)).isEqualTo(Sprt.Decision.RIGGED);
        assertThat(s.llr()).isCloseTo(9 * Math.log(1.4), within(1e-12));
        assertThat(s.flips()).isEqualTo(9);
        assertThat(s.heads()).isEqualTo(9);
        Sprt f = sprt();
        for (int i = 0; i < 5; i++) {
            assertThat(f.record(false)).isEqualTo(Sprt.Decision.CONTINUE);
        }
        assertThat(f.record(false)).isEqualTo(Sprt.Decision.FAIR);
    }

    @Test
    void sprtRejectsBadParameters() {
        assertThatThrownBy(() -> new Sprt(0.5, 0.5, 0.05, 0.05)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Sprt(0, 0.7, 0.05, 0.05)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Sprt(0.5, 0.7, 0.5, 0.05)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SprtOdds.simulate(0.5, 0.7, 0.05, 0.05, 0.5, 10, 1, 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SprtOdds.simulate(0.5, 0.7, 0.05, 0.05, 1.5, 10, 1, 10))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void operatingCharacteristicsHonourTheErrorRates() {
        SprtOdds fair = SprtOdds.simulate(0.5, 0.7, 0.05, 0.05, 0.5, 400, 2026, 4_000);
        SprtOdds bent = SprtOdds.simulate(0.5, 0.7, 0.05, 0.05, 0.7, 400, 2026, 4_000);
        assertThat(fair.riggedRate()).isLessThan(0.08);
        assertThat(bent.riggedRate()).isGreaterThan(0.92);
        assertThat(fair.undecided()).isZero();
        assertThat(bent.meanFlips()).isBetween(5.0, 40.0);
        double[] ci = bent.riggedInterval();
        assertThat(bent.riggedRate()).isBetween(ci[0], ci[1]);
        assertThat(SprtOdds.simulate(0.5, 0.7, 0.05, 0.05, 0.7, 400, 2026, 4_000)).isEqualTo(bent);
        assertThat(SprtOdds.simulate(0.5, 0.7, 0.05, 0.05, 0.6, 3, 1, 200).undecided()).isPositive();
    }

    @Test
    void posteriorIsANormalisedBelief() {
        RiggedCoinQuest q = new RiggedCoinQuest(4);
        assertThat(q.posterior(0)).isCloseTo(1.0 / 3, within(1e-12));
        assertThat(q.riggedCoin()).isEqualTo(-1);
        for (int i = 0; i < 9; i++) {
            q.flip(i % 3);
        }
        double sum = q.posterior(0) + q.posterior(1) + q.posterior(2);
        assertThat(sum).isCloseTo(1.0, within(1e-12));
        assertThat(q.flipsLeft()).isEqualTo(RiggedCoinQuest.BUDGET - 9);
        assertThat(q.keeperLine()).contains("flips left").contains("coin " + (q.suspect() + 1));
        assertThat(q.verdict(0)).isNotNull();
    }

    @Test
    void followingThePosteriorUsuallyCatchesTheRival() {
        int caught = 0;
        for (long seed = 0; seed < 200; seed++) {
            RiggedCoinQuest q = new RiggedCoinQuest(seed);
            int c = 0;
            while (q.flipsLeft() > 0 && q.posterior(q.suspect()) < 0.95) {
                q.flip(c++ % RiggedCoinQuest.COINS);
            }
            if (q.accuse(q.suspect()) == RiggedCoinQuest.Stage.CAUGHT) {
                caught++;
                assertThat(q.keeperLine()).contains("That's the one");
            } else {
                assertThat(q.keeperLine()).contains("It was coin " + (q.riggedCoin() + 1));
            }
        }
        assertThat(caught).isGreaterThan(130);
    }

    @Test
    void wrongAccusationAndForfeitEndTheQuest() {
        boolean wrong = false;
        for (long seed = 0; seed < 20 && !wrong; seed++) {
            RiggedCoinQuest q = new RiggedCoinQuest(seed);
            wrong = q.accuse(0) == RiggedCoinQuest.Stage.WRONG_COIN;
            assertThat(q.riggedCoin()).isBetween(0, 2);
            assertThatThrownBy(() -> q.flip(0)).isInstanceOf(IllegalStateException.class);
        }
        assertThat(wrong).isTrue();
        RiggedCoinQuest f = new RiggedCoinQuest(1);
        for (int i = 0; i < RiggedCoinQuest.BUDGET; i++) {
            f.flip(0);
        }
        assertThatThrownBy(() -> f.flip(1)).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> f.flip(3)).isInstanceOf(IndexOutOfBoundsException.class);
        assertThat(f.forfeit()).isEqualTo(RiggedCoinQuest.Stage.OUT_OF_HERBS);
        assertThat(f.keeperLine()).contains("Purse is empty");
        assertThatThrownBy(() -> f.accuse(0)).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(f::forfeit).isInstanceOf(IllegalStateException.class);
    }
}
