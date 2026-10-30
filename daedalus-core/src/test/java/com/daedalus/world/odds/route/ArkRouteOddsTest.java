// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.route;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.BalanceLimits;
import com.daedalus.world.odds.OddsRng;
import com.daedalus.world.odds.weather.Sky;
import java.util.List;
import org.junit.jupiter.api.Test;

class ArkRouteOddsTest {

    private static final List<ArkRoute> ROUTES = ArkRouteWager.ODDSREAPER_ROUTES;

    @Test
    void onlySquallsFollowTheSky() {
        RouteLeg squall = new RouteLeg("s", Hazard.SQUALL, 0.6);
        assertThat(squall.strike(Sky.CALM)).isEqualTo(0.3);
        assertThat(squall.strike(Sky.SQUALL)).isEqualTo(0.6);
        assertThat(squall.strike(Sky.STORM)).isEqualTo(RouteLeg.MAX_STRIKE);
        RouteLeg debris = new RouteLeg("d", Hazard.DEBRIS, 0.3);
        assertThat(debris.strike(Sky.CALM)).isEqualTo(debris.strike(Sky.STORM)).isEqualTo(0.3);
        assertThat(debris.expectedKeep(Sky.CALM)).isCloseTo(0.85, within(1e-12));
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new RouteLeg("x", Hazard.DRIFT, 0.96)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new RouteLeg("x", Hazard.DRIFT, Double.NaN))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ArkRoute("x", List.of(), 10)).isInstanceOf(IllegalArgumentException.class);
        RouteLeg leg = new RouteLeg("x", Hazard.DRIFT, 0.1);
        assertThatThrownBy(() -> new ArkRoute("x", List.of(leg), 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RouteOddsBoard.simulate(ROUTES.subList(0, 1), Sky.CALM, 1, 10))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RouteOddsBoard.simulate(ROUTES, Sky.CALM, 1, 0))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void exactExpectationsMatchClosedForm() {
        ArkRoute shard = ROUTES.get(0);
        assertThat(shard.expectedLifeHome(Sky.SQUALL)).isCloseTo(120 * 0.85 * 0.90, within(1e-9));
        assertThat(shard.cleanChance(Sky.STORM)).isCloseTo(0.7 * 0.8, within(1e-12));
        ArkRoute lanes = ROUTES.get(1);
        assertThat(lanes.expectedLifeHome(Sky.STORM)).isLessThan(lanes.expectedLifeHome(Sky.CALM));
    }

    @Test
    void sailingIsSeededAndLosesLifePerStrike() {
        ArkRoute.Voyage a = ROUTES.get(1).sail(Sky.STORM, new OddsRng(7));
        ArkRoute.Voyage b = ROUTES.get(1).sail(Sky.STORM, new OddsRng(7));
        assertThat(a).isEqualTo(b);
        assertThat(a.lifeHome()).isLessThanOrEqualTo(120.0);
        assertThat(a.clean()).isEqualTo(a.lifeHome() == 120.0);
    }

    @Test
    void boardConvergesToExactOddsAndIsDeterministic() {
        RouteOddsBoard board = RouteOddsBoard.simulate(ROUTES, Sky.SQUALL, 2026, 20_000);
        RouteOddsBoard again = RouteOddsBoard.simulate(ROUTES, Sky.SQUALL, 2026, 20_000);
        int total = 0;
        for (int i = 0; i < ROUTES.size(); i++) {
            assertThat(board.wins(i)).isEqualTo(again.wins(i));
            total += board.wins(i);
            ArkRoute r = ROUTES.get(i);
            assertThat(board.meanLifeHome(i)).isCloseTo(r.expectedLifeHome(Sky.SQUALL), within(1.0));
            double[] ci = board.cleanInterval(i);
            assertThat(r.cleanChance(Sky.SQUALL)).isBetween(ci[0] - 0.005, ci[1] + 0.005);
            assertThat(board.cleanChance(i)).isBetween(ci[0], ci[1]);
        }
        assertThat(total).isEqualTo(board.trials());
        assertThat(board.sky()).isEqualTo(Sky.SQUALL);
    }

    @Test
    void stormShiftsTheFavouriteOffTheSquallLanes() {
        RouteOddsBoard calm = RouteOddsBoard.simulate(ROUTES, Sky.CALM, 11, 5_000);
        RouteOddsBoard storm = RouteOddsBoard.simulate(ROUTES, Sky.STORM, 11, 5_000);
        assertThat(storm.bestChance(1)).isLessThan(calm.bestChance(1));
        assertThat(storm.favourite()).isNotEqualTo(1);
    }

    @Test
    void postedOddsShadeFairByClampedEdge() {
        RouteOddsBoard board = RouteOddsBoard.simulate(ROUTES, Sky.SQUALL, 3, 4_000);
        int fav = board.favourite();
        double fair = board.fairOdds(fav);
        assertThat(board.postedOdds(fav, 0.05)).isCloseTo(Math.max(1.0, fair * 0.95), within(1e-12));
        assertThat(board.postedOdds(fav, 0.5)).isEqualTo(board.postedOdds(fav, RouteOddsBoard.MAX_EDGE));
        assertThat(RouteOddsBoard.clampEdge(-1)).isEqualTo(RouteOddsBoard.MIN_EDGE);
        assertThat(RouteOddsBoard.clampEdge(Double.NaN)).isEqualTo(RouteOddsBoard.MIN_EDGE);
    }

    @Test
    void neverWinningRouteIsOffTheBoardAndLocksAreNotPostable() {
        ArkRoute safe = new ArkRoute("Safe", List.of(new RouteLeg("a", Hazard.DRIFT, 0.0)), 100);
        ArkRoute doomed = new ArkRoute("Doomed", List.of(new RouteLeg("b", Hazard.DEBRIS, 0.95)), 100);
        RouteOddsBoard lock = RouteOddsBoard.simulate(List.of(safe, doomed), Sky.CALM, 5, 500);
        assertThat(lock.fairOdds(1)).isInfinite();
        assertThat(lock.postedOdds(1, 0.05)).isZero();
        assertThat(lock.postable(BalanceLimits.FAIR)).isFalse();
        assertThat(RouteOddsBoard.simulate(ROUTES, Sky.SQUALL, 2026, 5_000).postable(BalanceLimits.FAIR)).isTrue();
    }

    @Test
    void wagerQuestPaysPostedOddsOnTheWinningRoute() {
        ArkRouteWager q = new ArkRouteWager(ROUTES, Sky.SQUALL, 2026, 5_000);
        assertThat(q.stage()).isEqualTo(ArkRouteWager.Stage.ODDS_POSTED);
        assertThat(q.keeperLine()).contains("Chalk favours");
        assertThat(q.postable(BalanceLimits.FAIR)).isTrue();
        assertThatThrownBy(() -> q.sail(1)).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> q.stake(0, 0)).isInstanceOf(IllegalArgumentException.class);
        q.stake(2, 10);
        assertThat(q.stage()).isEqualTo(ArkRouteWager.Stage.STAKED);
        assertThat(q.keeperLine()).contains("ark bell");
        assertThatThrownBy(() -> q.stake(1, 10)).isInstanceOf(IllegalStateException.class);
        int expectedWinner = RouteOddsBoard.race(ROUTES, Sky.SQUALL, new OddsRng(99), null, null);
        int paid = q.sail(99);
        assertThat(q.winner()).isEqualTo(expectedWinner);
        if (expectedWinner == 2) {
            assertThat(q.stage()).isEqualTo(ArkRouteWager.Stage.BACKED_WINNER);
            assertThat(paid).isEqualTo((int) Math.floor(10 * q.board().postedOdds(2, ArkRouteWager.EDGE)));
            assertThat(q.keeperLine()).contains("most souls home");
        } else {
            assertThat(q.stage()).isEqualTo(ArkRouteWager.Stage.BACKED_LOSER);
            assertThat(paid).isZero();
            assertThat(q.keeperLine()).contains(ROUTES.get(expectedWinner).name());
        }
        assertThat(q.backed()).isEqualTo(2);
    }

    @Test
    void bothQuestOutcomesAreReachable() {
        boolean won = false;
        boolean lost = false;
        for (long s = 0; s < 50 && !(won && lost); s++) {
            ArkRouteWager q = new ArkRouteWager(ROUTES, Sky.SQUALL, 1, 500);
            q.stake(0, 5);
            int paid = q.sail(s);
            won |= paid > 0;
            lost |= paid == 0;
        }
        assertThat(won).isTrue();
        assertThat(lost).isTrue();
    }

    @Test
    void offBoardRouteCannotBeBacked() {
        ArkRoute safe = new ArkRoute("Safe", List.of(new RouteLeg("a", Hazard.DRIFT, 0.0)), 100);
        ArkRoute doomed = new ArkRoute("Doomed", List.of(new RouteLeg("b", Hazard.DEBRIS, 0.95)), 100);
        ArkRouteWager q = new ArkRouteWager(List.of(safe, doomed), Sky.CALM, 1, 200);
        assertThatThrownBy(() -> q.stake(1, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> q.stake(5, 5)).isInstanceOf(IndexOutOfBoundsException.class);
    }
}
