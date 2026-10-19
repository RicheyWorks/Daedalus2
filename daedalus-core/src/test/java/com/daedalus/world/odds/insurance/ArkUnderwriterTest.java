// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.insurance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import com.daedalus.world.odds.route.ArkRoute;
import com.daedalus.world.odds.route.ArkRouteWager;
import com.daedalus.world.odds.route.Hazard;
import com.daedalus.world.odds.route.RouteLeg;
import com.daedalus.world.odds.weather.Sky;
import java.util.List;
import org.junit.jupiter.api.Test;

class ArkUnderwriterTest {

    private static final ArkRoute SHARD = ArkRouteWager.ODDSREAPER_ROUTES.get(0);

    @Test
    void premiumIsExpectedClaimPlusClampedLoading() {
        ArkPolicy p = new ArkPolicy(SHARD, Sky.SQUALL, 2.0);
        assertThat(p.expectedClaim()).isCloseTo(2.0 * (120 - 120 * 0.85 * 0.90), within(1e-9));
        assertThat(p.premium(0.0)).isEqualTo((int) Math.ceil(p.expectedClaim() - 1e-9));
        assertThat(p.premium(0.2)).isEqualTo((int) Math.ceil(p.expectedClaim() * 1.2 - 1e-9));
        assertThat(p.premium(5.0)).isEqualTo(p.premium(ArkPolicy.MAX_LOADING));
        assertThat(p.premium(-1)).isEqualTo(p.premium(Double.NaN)).isEqualTo(p.premium(0));
        assertThat(p.claim(120)).isZero();
        assertThat(p.claim(100)).isEqualTo(40.0);
    }

    @Test
    void safeRouteCostsNothingToCover() {
        ArkRoute safe = new ArkRoute("Safe", List.of(new RouteLeg("a", Hazard.DRIFT, 0.0)), 50);
        ArkPolicy p = new ArkPolicy(safe, Sky.STORM, 1.0);
        assertThat(p.premium(0.5)).isZero();
        UnderwritingPool pool = new UnderwritingPool(0, List.of(p), 0.5);
        assertThat(pool.season(new OddsRng(1))).isZero();
        assertThat(pool.simulate(1, 10).insolvent()).isZero();
    }

    @Test
    void poolSimulationConvergesAndIsSeeded() {
        UnderwritingPool pool = new UnderwritingPool(80, UnderwriterQuest.fleet(Sky.SQUALL), 0.2);
        UnderwritingPool.Board a = pool.simulate(5, 6_000);
        assertThat(pool.simulate(5, 6_000)).isEqualTo(a);
        assertThat(a.meanProfit()).isCloseTo(pool.premiums() - pool.expectedClaims(), within(3.0));
        double[] ci = a.interval();
        assertThat(a.insolvency()).isBetween(ci[0], ci[1]);
        assertThat(pool.policies()).hasSize(6);
        assertThat(pool.reserve()).isEqualTo(80);
    }

    @Test
    void thickerLoadingMeansFewerBusts() {
        List<ArkPolicy> fleet = UnderwriterQuest.fleet(Sky.STORM);
        double thin = new UnderwritingPool(80, fleet, 0.0).simulate(9, 4_000).insolvency();
        double thick = new UnderwritingPool(80, fleet, 0.5).simulate(9, 4_000).insolvency();
        assertThat(thick).isLessThan(thin);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new ArkPolicy(SHARD, Sky.CALM, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ArkPolicy(SHARD, Sky.CALM, Double.POSITIVE_INFINITY))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new UnderwritingPool(-1, UnderwriterQuest.fleet(Sky.CALM), 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new UnderwritingPool(10, List.of(), 0)).isInstanceOf(IllegalArgumentException.class);
        UnderwritingPool pool = new UnderwritingPool(10, UnderwriterQuest.fleet(Sky.CALM), 0);
        assertThatThrownBy(() -> pool.simulate(1, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void keeperRejectsDearAndThinQuotesThenApproves() {
        UnderwriterQuest q = new UnderwriterQuest(Sky.SQUALL, 2026);
        assertThat(q.keeperLine()).contains("Six arks");
        assertThatThrownBy(() -> q.sail(1)).isInstanceOf(IllegalStateException.class);
        assertThat(q.quote(0.40)).isEqualTo(UnderwriterQuest.Stage.REJECTED);
        assertThat(q.keeperLine()).contains("Survivors cannot pay");
        assertThat(q.quote(0.0)).isEqualTo(UnderwriterQuest.Stage.REJECTED);
        assertThat(q.board().insolvency()).isGreaterThan(UnderwriterQuest.MAX_INSOLVENCY);
        assertThat(q.keeperLine()).contains("Price it thicker");
        assertThat(q.quote(UnderwriterQuest.FAIR_LOADING)).isEqualTo(UnderwriterQuest.Stage.APPROVED);
        assertThat(q.keeperLine()).contains("Approved");
        assertThatThrownBy(() -> q.quote(0.1)).isInstanceOf(IllegalStateException.class);
        UnderwriterQuest.Stage end = q.sail(77);
        assertThat(end).isIn(UnderwriterQuest.Stage.SOLVENT, UnderwriterQuest.Stage.BUST);
        assertThat(q.keeperLine()).containsAnyOf("Season closed", "pool broke");
        assertThat(q.close() >= 0).isEqualTo(end == UnderwriterQuest.Stage.SOLVENT);
    }

    @Test
    void bothSeasonEndingsAreReachable() {
        UnderwritingPool pool = new UnderwritingPool(0, UnderwriterQuest.fleet(Sky.STORM), 0.0);
        boolean solvent = false;
        boolean bust = false;
        for (long s = 0; s < 200 && !(solvent && bust); s++) {
            double close = pool.season(new OddsRng(s));
            solvent |= close >= 0;
            bust |= close < 0;
        }
        assertThat(solvent).isTrue();
        assertThat(bust).isTrue();
    }
}
