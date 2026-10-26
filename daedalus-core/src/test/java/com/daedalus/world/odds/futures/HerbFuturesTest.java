// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.futures;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.weather.Sky;
import com.daedalus.world.odds.weather.StormGlass;
import com.daedalus.world.odds.weather.StormGlass.Reading;
import org.junit.jupiter.api.Test;

class HerbFuturesTest {

    private static final HerbMarket M = HerbMarket.ODDSREAPER;

    private static FuturesDesk desk(long seed) {
        return new FuturesDesk(M, seed, Sky.CALM, 0.05);
    }

    @Test
    void fairForwardIsForecastWeightedSpot() {
        double[] d = M.forecast(Reading.FALLING, 2);
        double manual = d[0] * 10 + d[1] * 14 + d[2] * 22;
        assertThat(M.fairForward(Reading.FALLING, 2)).isCloseTo(manual, within(1e-9));
        assertThat(M.fairForward(Reading.LOW, 0)).isGreaterThan(M.fairForward(Reading.HIGH, 0));
        assertThat(M.spotVariance(Reading.LOW, 1)).isPositive();
        assertThat(M.spot(Sky.STORM)).isEqualTo(22.0);
        assertThat(M.glass()).isSameAs(StormGlass.ODDSREAPER);
    }

    @Test
    void farForwardsForgetTheGlass() {
        assertThat(M.fairForward(Reading.LOW, 60)).isCloseTo(M.fairForward(Reading.HIGH, 60), within(1e-6));
    }

    @Test
    void forwardPayoffs() {
        Forward lng = new Forward(1, 4, 12.0, true);
        Forward shrt = new Forward(1, 4, 12.0, false);
        assertThat(lng.payoff(22)).isEqualTo(40.0);
        assertThat(shrt.payoff(22)).isEqualTo(-40.0);
        assertThat(shrt.payoff(10)).isEqualTo(8.0);
        assertThatThrownBy(() -> new Forward(-1, 1, 1, true)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Forward(0, 0, 1, true)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Forward(0, 1, 0, true)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void deskQuotesAroundFairAndSettlesOnTheIslandSky() {
        FuturesDesk d = desk(2026);
        assertThat(d.bid(2)).isLessThan(d.fair(2)).isLessThan(d.ask(2));
        assertThat(d.ask(2)).isCloseTo(d.fair(2) * 1.05, within(1e-9));
        assertThat(d.buy(2, 3).price()).isEqualTo(d.ask(2));
        assertThat(d.sell(2, 3).longSide()).isFalse();
        assertThat(d.skyOn(2)).isEqualTo(StormGlass.ODDSREAPER.chain().skyOn(2026, Sky.CALM, 2));
        assertThat(d.dawnReading()).isEqualTo(StormGlass.ODDSREAPER.readOn(2026, Sky.CALM, 0));
        Forward f = d.buy(2, 3);
        assertThat(d.settle(f)).isEqualTo(f.payoff(M.spot(d.skyOn(2))));
        assertThat(new FuturesDesk(M, 1, Sky.CALM, 0.5).spread()).isEqualTo(FuturesDesk.MAX_SPREAD);
        assertThat(new FuturesDesk(M, 1, Sky.CALM, Double.NaN).spread()).isZero();
        assertThat(new FuturesDesk(M, 1, Sky.CALM, -1).spread()).isZero();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new HerbMarket(StormGlass.ODDSREAPER, 0, 1, 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> M.forecast(Reading.LOW, -1)).isInstanceOf(IllegalArgumentException.class);
        HerbHedgeQuest q = new HerbHedgeQuest(M, desk(1));
        assertThatThrownBy(() -> q.revenueVariance(21)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> q.hedge(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(q::settle).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void hedgingHalfQuartersTheVarianceAndLocksRevenue() {
        FuturesDesk d = desk(7);
        HerbHedgeQuest q = new HerbHedgeQuest(M, d);
        assertThat(q.keeperLine()).contains("Glass reads").contains("forward");
        assertThat(q.revenueVariance(20)).isZero();
        assertThat(q.revenueVariance(10)).isCloseTo(q.revenueVariance(0) * 0.25, within(1e-9));
        q.hedge(10);
        assertThat(q.prudent()).isTrue();
        assertThat(q.hedged()).isEqualTo(10);
        assertThat(q.keeperLine()).contains("Mossa sleeps");
        assertThatThrownBy(() -> q.hedge(5)).isInstanceOf(IllegalStateException.class);
        double spot = d.settleSpot(HerbHedgeQuest.HARVEST_DAY);
        assertThat(q.settle()).isCloseTo(10 * spot + 10 * d.bid(HerbHedgeQuest.HARVEST_DAY), within(1e-9));
        assertThat(q.stage()).isEqualTo(HerbHedgeQuest.Stage.SETTLED);
        assertThat(q.revenue()).isPositive();
        assertThat(q.keeperLine()).contains("tokens to Mossa");
    }

    @Test
    void unhedgedGrowerRidesTheWeather() {
        FuturesDesk d = desk(7);
        HerbHedgeQuest q = new HerbHedgeQuest(M, d);
        q.hedge(0);
        assertThat(q.prudent()).isFalse();
        assertThat(q.keeperLine()).contains("betting on the weather");
        assertThat(q.settle()).isEqualTo(20 * d.settleSpot(HerbHedgeQuest.HARVEST_DAY));
    }
}
