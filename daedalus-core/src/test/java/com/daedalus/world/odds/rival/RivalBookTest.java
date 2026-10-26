// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.rival;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.route.ArkRouteWager;
import com.daedalus.world.odds.route.RouteOddsBoard;
import com.daedalus.world.odds.weather.Sky;
import java.util.List;
import org.junit.jupiter.api.Test;

class RivalBookTest {

    private static final double[] FAIR = {0.5, 0.3, 0.2};

    @Test
    void noiselessBookCarriesItsMargin() {
        RivalBook b = RivalBook.post(FAIR, 0.08, 0.0, 1);
        assertThat(b.overround()).isCloseTo(0.08, within(1e-9));
        assertThat(b.odds(0)).isCloseTo(1 / (0.5 * 1.08), within(1e-12));
        assertThat(ValueScan.values(FAIR, b, 0.0)).isEmpty();
    }

    @Test
    void postingIsSeededAndNoisy() {
        RivalBook a = RivalBook.post(FAIR, 0.05, 0.3, 9);
        RivalBook b = RivalBook.post(FAIR, 0.05, 0.3, 9);
        assertThat(a.all()).containsExactly(b.all());
        assertThat(RivalBook.post(FAIR, 0.05, 0.3, 10).all()).isNotEqualTo(a.all());
        assertThat(a.size()).isEqualTo(3);
    }

    @Test
    void valueLinesHavePositiveEdge() {
        RivalBook b = RivalBook.of(2.2, 3.0, 6.0);
        List<ValueScan.Value> v = ValueScan.values(FAIR, b, 0.0);
        assertThat(v).extracting(ValueScan.Value::outcome).containsExactly(0, 2);
        assertThat(v.get(1).edge()).isCloseTo(0.2, within(1e-12));
        assertThat(ValueScan.values(FAIR, b, 0.15)).extracting(ValueScan.Value::outcome).containsExactly(2);
    }

    @Test
    void arbitrageAcrossTwoBooksLocksEveryOutcome() {
        RivalBook keeper = RivalBook.of(2.1, 3.0, 4.0);
        RivalBook rival = RivalBook.of(1.8, 3.6, 5.5);
        assertThat(ValueScan.bestPrices(keeper, rival)).containsExactly(2.1, 3.6, 5.5);
        assertThat(ValueScan.isArb(keeper, rival)).isTrue();
        int[] stakes = ValueScan.arbStakes(keeper, rival, 100);
        assertThat(stakes).hasSize(3);
        int spent = stakes[0] + stakes[1] + stakes[2];
        assertThat(spent).isLessThanOrEqualTo(100);
        double[] best = ValueScan.bestPrices(keeper, rival);
        for (int i = 0; i < 3; i++) {
            assertThat(Math.floor(stakes[i] * best[i])).isGreaterThan(spent);
        }
        assertThat(ValueScan.isArb(keeper, keeper)).isFalse();
        assertThat(ValueScan.arbStakes(keeper, keeper, 100)).isEmpty();
        assertThat(ValueScan.arbSum(RivalBook.of(2, 0, 3), RivalBook.of(2, 0, 3))).isInfinite();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> RivalBook.post(new double[] {0.5, 0.4}, 0.05, 0.1, 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RivalBook.post(new double[] {1.0}, 0.05, 0.1, 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RivalBook.post(FAIR, 1.0, 0.1, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RivalBook.of(0.5, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ValueScan.values(FAIR, RivalBook.of(2, 2), 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ValueScan.bestPrices(RivalBook.of(2, 2), RivalBook.of(2, 2, 2)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ValueScan.arbStakes(RivalBook.of(2, 2), RivalBook.of(2, 2), 0))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questExposesTheRivalOnTheRouteBoard() {
        RouteOddsBoard board = RouteOddsBoard.simulate(ArkRouteWager.ODDSREAPER_ROUTES, Sky.SQUALL, 2026, 4_000);
        double[] fair = new double[3];
        for (int i = 0; i < 3; i++) {
            fair[i] = board.bestChance(i);
        }
        RivalBook rival = RivalBook.of(1 / fair[0] * 1.3, 1 / fair[1] * 0.8, 1 / fair[2] * 1.1);
        RivalBookQuest q = new RivalBookQuest(fair, rival);
        assertThat(q.valueLines()).isEqualTo(2);
        assertThat(q.keeperLine()).contains("2 of his lines");
        assertThat(q.call(0)).isTrue();
        assertThat(q.call(0)).isFalse();
        assertThat(q.miscalls()).isEqualTo(1);
        assertThat(q.call(2)).isTrue();
        assertThat(q.stage()).isEqualTo(RivalBookQuest.Stage.EXPOSED);
        assertThat(q.found()).isEqualTo(2);
        assertThat(q.reward()).isEqualTo(RivalBookQuest.REWARD);
        assertThat(q.keeperLine()).contains("Every soft line");
        assertThatThrownBy(() -> q.call(1)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void twoMiscallsAndTheRivalWins() {
        RivalBookQuest q = new RivalBookQuest(FAIR, RivalBook.of(2.2, 3.0, 4.0));
        assertThat(q.call(1)).isFalse();
        assertThat(q.call(2)).isFalse();
        assertThat(q.stage()).isEqualTo(RivalBookQuest.Stage.FOOLED);
        assertThat(q.reward()).isZero();
        assertThat(q.keeperLine()).contains("Read the chalk");
        assertThatThrownBy(() -> q.call(5)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void honestRivalLeavesNothingToFind() {
        RivalBookQuest q = new RivalBookQuest(FAIR, RivalBook.post(FAIR, 0.10, 0.0, 3));
        assertThat(q.stage()).isEqualTo(RivalBookQuest.Stage.EXPOSED);
        assertThat(q.reward()).isZero();
        assertThat(q.keeperLine()).contains("Not a soft line");
        RivalBookQuest bad = new RivalBookQuest(FAIR, RivalBook.of(2.2, 3.0, 4.0));
        assertThatThrownBy(() -> bad.call(3)).isInstanceOf(IndexOutOfBoundsException.class);
    }
}
