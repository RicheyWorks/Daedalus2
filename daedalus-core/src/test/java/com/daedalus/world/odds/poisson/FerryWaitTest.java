// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.poisson;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class FerryWaitTest {

    private static final FerryClock DOCK = new FerryClock(20.0);

    @Test
    void poissonCountsAndExponentialWaits() {
        assertThat(DOCK.meanGap()).isEqualTo(20.0);
        assertThat(DOCK.rate()).isCloseTo(0.05, within(1e-15));
        assertThat(DOCK.countChance(0, 20)).isCloseTo(Math.exp(-1), within(1e-12));
        assertThat(DOCK.countChance(2, 40)).isCloseTo(2 * Math.exp(-2), within(1e-12));
        assertThat(DOCK.countChance(0, 0)).isEqualTo(1.0);
        assertThat(DOCK.countChance(3, 0)).isZero();
        double sum = 0;
        double mean = 0;
        for (int k = 0; k < 60; k++) {
            sum += DOCK.countChance(k, 100);
            mean += k * DOCK.countChance(k, 100);
        }
        assertThat(sum).isCloseTo(1.0, within(1e-12));
        assertThat(mean).isCloseTo(5.0, within(1e-9));
        assertThat(DOCK.waitBeyond(30)).isCloseTo(0.22313016014842982, within(1e-12));
        assertThat(DOCK.waitQuantile(0.5)).isCloseTo(20 * Math.log(2), within(1e-12));
        assertThat(DOCK.waitBeyond(DOCK.waitQuantile(0.9))).isCloseTo(0.1, within(1e-12));
    }

    @Test
    void theInspectionParadox() {
        assertThat(DOCK.expectedWait()).isEqualTo(20.0);
        assertThat(DOCK.timetableWait()).isEqualTo(10.0);
        assertThat(DOCK.landedGapMean()).isEqualTo(40.0);
        assertThat(DOCK.landedGapMean()).isGreaterThan(DOCK.meanGap());
    }

    @Test
    void seededTravellersAgreeWithTheExactOdds() {
        double[] s = FerryDay.simulate(20.0, 300.0, 30.0, 2026, 20_000);
        assertThat(s[0]).isCloseTo(20.0, within(0.6));
        assertThat(s[1]).isCloseTo(40.0, within(1.0));
        assertThat(DOCK.waitBeyond(30)).isBetween(s[3], s[4]);
        assertThat(FerryDay.simulate(20.0, 300.0, 30.0, 2026, 20_000)).containsExactly(s);
        FerryDay d = FerryDay.at(20.0, 300.0, new OddsRng(4));
        assertThat(d.waited()).isPositive();
        assertThat(d.gap()).isGreaterThanOrEqualTo(d.waited());
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new FerryClock(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DOCK.countChance(-1, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DOCK.waitBeyond(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DOCK.waitQuantile(1.0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FerryDay.at(0, 5, new OddsRng(1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FerryDay.simulate(20, 5, 1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        FerryWaitQuest q = new FerryWaitQuest();
        assertThatThrownBy(() -> q.guess(-1, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questNodsForTheFullGap() {
        FerryWaitQuest q = new FerryWaitQuest();
        assertThat(q.stage()).isEqualTo(FerryWaitQuest.Stage.GUESSING);
        assertThat(q.waited()).isNegative();
        assertThat(q.nod()).isFalse();
        assertThat(q.expectedWait()).isEqualTo(20.0);
        assertThat(q.longWaitChance()).isCloseTo(0.22313016014842982, within(1e-12));
        assertThat(q.keeperLine()).contains("every 20 minutes");
        q.guess(20, 5);
        assertThat(q.nod()).isTrue();
        assertThat(q.waited()).isPositive();
        assertThat(q.keeperLine()).contains("Average wait 20, not 10").contains("average 40")
                .contains("Over 30 minutes: 22%").contains("Good guess.");
        assertThatThrownBy(() -> q.guess(20, 5)).isInstanceOf(IllegalStateException.class);
        FerryWaitQuest half = new FerryWaitQuest();
        half.guess(10, 5);
        assertThat(half.nod()).isFalse();
        assertThat(half.keeperLine()).contains("Not my nod.");
        double total = 0;
        for (long s = 0; s < 400; s++) {
            FerryWaitQuest t = new FerryWaitQuest();
            t.guess(20, s);
            total += t.waited();
        }
        assertThat(total / 400).isCloseTo(20.0, within(3.0));
    }
}
