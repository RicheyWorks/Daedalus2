// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.match;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class BirthNightsTest {

    private static final BirthNightOdds YEAR = new BirthNightOdds(365);

    @Test
    void classicBirthdayNumbers() {
        assertThat(YEAR.nights()).isEqualTo(365);
        assertThat(YEAR.shareChance(1)).isZero();
        assertThat(YEAR.shareChance(23)).isCloseTo(0.5072972343239857, within(1e-12));
        assertThat(YEAR.shareChance(22)).isCloseTo(0.4756953076625503, within(1e-12));
        assertThat(YEAR.shareChance(30)).isCloseTo(0.7063162427192688, within(1e-12));
        assertThat(YEAR.shareChance(366)).isEqualTo(1.0);
        assertThat(YEAR.smallestCrew(0.5, 0)).isEqualTo(23);
        assertThat(YEAR.smallestCrew(0.5, 1)).isEqualTo(14);
        assertThat(YEAR.smallestCrew(0.5, 2)).isEqualTo(11);
        int[] answers = {23, 14, 11};
        for (int k = 0; k <= 2; k++) {
            assertThat(YEAR.nearChance(answers[k], k)).isGreaterThanOrEqualTo(0.5);
            assertThat(YEAR.nearChance(answers[k] - 1, k)).isLessThan(0.5);
        }
        assertThat(YEAR.nearChance(13, 1)).isCloseTo(0.48286719152497404, within(1e-12));
        assertThat(YEAR.nearChance(14, 1)).isCloseTo(0.5374927880366436, within(1e-12));
        assertThat(YEAR.expectedPairs(23, 0)).isCloseTo(253.0 / 365, within(1e-12));
        assertThat(YEAR.expectedPairs(14, 1)).isCloseTo(91.0 * 3 / 365, within(1e-12));
    }

    @Test
    void nearFormulaMatchesFullEnumeration() {
        int d = 12;
        BirthNightOdds small = new BirthNightOdds(d);
        for (int n = 2; n <= 4; n++) {
            for (int k = 0; k <= 2; k++) {
                int total = 1;
                for (int i = 0; i < n; i++) {
                    total *= d;
                }
                int near = 0;
                for (int code = 0; code < total; code++) {
                    int[] b = new int[n];
                    int c = code;
                    for (int i = 0; i < n; i++) {
                        b[i] = c % d;
                        c /= d;
                    }
                    if (anyWithin(b, d, k)) {
                        near++;
                    }
                }
                assertThat(small.nearChance(n, k)).isCloseTo(near / (double) total, within(1e-14));
            }
        }
    }

    @Test
    void theYearWraps() {
        CrewMuster ends = CrewMuster.of(365, 364, 0);
        assertThat(ends.closestGap()).isEqualTo(1);
        assertThat(ends.hasPairWithin(1)).isTrue();
        assertThat(ends.hasPairWithin(0)).isFalse();
        assertThat(CrewMuster.of(365, 0, 182).closestGap()).isEqualTo(182);
        assertThat(CrewMuster.of(365, 363, 1).closestGap()).isEqualTo(3);
        assertThat(CrewMuster.of(365, 10, 10).hasPairWithin(0)).isTrue();
        assertThatThrownBy(() -> CrewMuster.of(365, 365)).isInstanceOf(IllegalArgumentException.class);
        BirthNightOdds tiny = new BirthNightOdds(4);
        assertThat(tiny.nearChance(2, 1)).isCloseTo(0.75, within(1e-15));
    }

    @Test
    void seededMustersAgreeWithTheExactOdds() {
        double[] same = CrewMuster.simulate(365, 23, 0, 2026, 20_000);
        assertThat(YEAR.shareChance(23)).isBetween(same[1], same[2]);
        assertThat(same[0]).isCloseTo(YEAR.shareChance(23), within(0.015));
        double[] near = CrewMuster.simulate(365, 14, 1, 7, 20_000);
        assertThat(near[0]).isCloseTo(YEAR.nearChance(14, 1), within(0.015));
        assertThat(CrewMuster.simulate(365, 23, 0, 2026, 20_000)).containsExactly(same);
        CrewMuster m = CrewMuster.muster(365, 5, new OddsRng(3));
        assertThat(m.births()).hasSize(5).isSorted();
        assertThat(CrewMuster.muster(365, 1, new OddsRng(3)).closestGap()).isEqualTo(-1);
        assertThat(CrewMuster.muster(365, 1, new OddsRng(3)).hasPairWithin(5)).isFalse();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new BirthNightOdds(1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> YEAR.nearChance(-1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> YEAR.nearChance(5, 365)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> YEAR.smallestCrew(1.0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrewMuster.muster(1, 3, new OddsRng(1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrewMuster.simulate(365, 3, 0, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        BirthNightQuest q = new BirthNightQuest();
        assertThatThrownBy(() -> q.guess(1, 14, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questScoresTheGuesses() {
        BirthNightQuest q = new BirthNightQuest();
        assertThat(q.stage()).isEqualTo(BirthNightQuest.Stage.GUESSING);
        assertThat(q.sameAnswer()).isEqualTo(23);
        assertThat(q.nearAnswer()).isEqualTo(14);
        assertThat(q.nods()).isZero();
        assertThat(q.closestGap()).isEqualTo(-1);
        assertThat(q.keeperLine()).contains("365-night year");
        q.guess(24, 40, 5);
        assertThat(q.nods()).isEqualTo(1);
        assertThat(q.keeperLine()).contains("23 for a shared night (50.7%)").contains("14 within a night (53.7%)")
                .contains("71% for thirty").contains("1 of 2 nods");
        assertThatThrownBy(() -> q.guess(23, 14, 1)).isInstanceOf(IllegalStateException.class);
        int shares = 0;
        for (long s = 0; s < 300; s++) {
            BirthNightQuest t = new BirthNightQuest();
            t.guess(23, 14, s);
            assertThat(t.nods()).isEqualTo(2);
            assertThat(t.crewShares()).isEqualTo(t.closestGap() == 0);
            if (t.crewShares()) {
                shares++;
                assertThat(t.keeperLine()).contains("two share a night");
            } else {
                assertThat(t.keeperLine()).contains("no shared night");
            }
        }
        assertThat(shares).isBetween(185, 240);
    }

    private static boolean anyWithin(int[] b, int d, int k) {
        for (int i = 0; i < b.length; i++) {
            for (int j = i + 1; j < b.length; j++) {
                int gap = Math.abs(b[i] - b[j]);
                if (Math.min(gap, d - gap) <= k) {
                    return true;
                }
            }
        }
        return false;
    }
}
