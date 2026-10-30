// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.benford;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class CookedLedgerTest {

    @Test
    void firstDigitLawSumsToOneAndFavoursOnes() {
        double sum = 0;
        for (int d = 1; d <= 9; d++) {
            sum += BenfordLaw.firstDigit(d);
        }
        assertThat(sum).isCloseTo(1.0, within(1e-12));
        assertThat(BenfordLaw.firstDigit(1)).isCloseTo(0.30103, within(1e-5));
        assertThat(BenfordLaw.firstDigit(9)).isCloseTo(0.04576, within(1e-5));
        assertThat(BenfordLaw.leadingDigit(1000.0)).isEqualTo(1);
        assertThat(BenfordLaw.leadingDigit(0.0375)).isEqualTo(3);
        assertThat(BenfordLaw.leadingDigit(999.999)).isEqualTo(9);
        assertThatThrownBy(() -> BenfordLaw.firstDigit(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BenfordLaw.leadingDigit(0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void chiSquareTailIsExactAtTheCriticalValue() {
        assertThat(BenfordLaw.tail8(0)).isCloseTo(1.0, within(1e-15));
        assertThat(BenfordLaw.tail8(BenfordLaw.CRITICAL_5PCT)).isCloseTo(0.05, within(1e-12));
        assertThat(BenfordLaw.tail8(20.090235)).isCloseTo(0.01, within(1e-6));
        int[] perfect = new int[10];
        int[] flat = new int[10];
        for (int d = 1; d <= 9; d++) {
            perfect[d] = (int) Math.round(100_000 * BenfordLaw.firstDigit(d));
            flat[d] = 100;
        }
        assertThat(BenfordLaw.chiSquare(perfect)).isLessThan(0.01);
        assertThat(BenfordLaw.flagged(flat)).isTrue();
    }

    @Test
    void honestLedgersFollowBenfordAndCookedOnesDoNot() {
        int[] honest = BenfordLaw.digitCounts(CargoLedger.honest(90_000, new OddsRng(184L)));
        int[] cooked = BenfordLaw.digitCounts(CargoLedger.cooked(90_000, new OddsRng(184L)));
        for (int d = 1; d <= 9; d++) {
            assertThat(honest[d] / 90_000.0).isCloseTo(BenfordLaw.firstDigit(d), within(0.01));
            assertThat(cooked[d] / 90_000.0).isCloseTo(1.0 / 9, within(0.01));
        }
    }

    @Test
    void auditFalseAlarmsNearFivePercentAndCatchesCookedLedgers() {
        double[] honest = CargoLedger.flagRate(false, 200, 184L, 4000);
        assertThat(honest[1]).isLessThanOrEqualTo(0.05);
        assertThat(honest[2]).isGreaterThanOrEqualTo(0.05);
        double[] cooked = CargoLedger.flagRate(true, 200, 184L, 1000);
        assertThat(cooked[2]).isGreaterThanOrEqualTo(0.99);
        assertThat(cooked[0]).isGreaterThan(0.99);
    }

    @Test
    void questPointsAtTheWorstFitAndIsDeterministic() {
        int caught = 0;
        for (long seed = 0; seed < 200; seed++) {
            CookedLedgerQuest q = new CookedLedgerQuest(seed);
            assertThat(q.stage()).isEqualTo(CookedLedgerQuest.Stage.AUDITING);
            assertThat(q.keeperLine()).contains("Which ledger was cooked?");
            if (q.point(q.worstFit()) == CookedLedgerQuest.Stage.CAUGHT) {
                caught++;
                assertThat(q.keeperLine()).contains("caught");
            }
            assertThatThrownBy(() -> q.point(0)).isInstanceOf(IllegalStateException.class);
        }
        assertThat(caught).isGreaterThanOrEqualTo(198);
        CookedLedgerQuest a = new CookedLedgerQuest(7L);
        CookedLedgerQuest b = new CookedLedgerQuest(7L);
        assertThat(a.counts(0)).containsExactly(b.counts(0));
        assertThat(a.worstFit()).isEqualTo(b.worstFit());
        assertThatThrownBy(() -> a.counts(3)).isInstanceOf(IllegalArgumentException.class);
    }
}
