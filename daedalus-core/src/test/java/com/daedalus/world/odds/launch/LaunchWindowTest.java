// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.launch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.route.ArkRoute;
import com.daedalus.world.odds.weather.Sky;
import com.daedalus.world.odds.weather.StormGlass;
import com.daedalus.world.odds.weather.StormGlass.Reading;
import java.util.List;
import org.junit.jupiter.api.Test;

class LaunchWindowTest {

    private static final LaunchPlanner P = LaunchPlanner.ODDSREAPER;

    @Test
    void expectedLifeMixesForecastAndWaitCost() {
        double[] dist = P.forecast(Reading.LOW, 2);
        ArkRoute lanes = P.routes().get(1);
        double manual = 0;
        for (Sky s : Sky.values()) {
            manual += dist[s.ordinal()] * lanes.expectedLifeHome(s);
        }
        assertThat(P.expectedLife(Reading.LOW, 1, 2)).isCloseTo(manual * 0.98 * 0.98, within(1e-9));
        assertThat(dist[0] + dist[1] + dist[2]).isCloseTo(1.0, within(1e-9));
    }

    @Test
    void optionsCoverEveryRouteAndDay() {
        List<LaunchOption> opts = P.options(Reading.FALLING);
        assertThat(opts).hasSize(3 * (P.maxDays() + 1));
        LaunchOption best = P.best(Reading.FALLING);
        assertThat(opts).allSatisfy(o -> assertThat(o.expectedLife()).isLessThanOrEqualTo(best.expectedLife()));
    }

    @Test
    void lowGlassKeepsArksOffTheSquallLanesToday() {
        assertThat(P.expectedLife(Reading.LOW, 1, 0)).isLessThan(P.expectedLife(Reading.HIGH, 1, 0));
        LaunchOption low = P.best(Reading.LOW);
        assertThat(low.route() == 1 && low.day() == 0).isFalse();
    }

    @Test
    void driftAndDebrisIgnoreTheGlass() {
        assertThat(P.expectedLife(Reading.LOW, 0, 0)).isCloseTo(P.expectedLife(Reading.HIGH, 0, 0), within(1e-9));
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new LaunchPlanner(StormGlass.ODDSREAPER, List.of(), 1, 0.9))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LaunchPlanner(StormGlass.ODDSREAPER, P.routes(), -1, 0.9))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LaunchPlanner(StormGlass.ODDSREAPER, P.routes(), 1, 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> P.expectedLife(Reading.LOW, 0, 9)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> P.expectedLife(Reading.LOW, 7, 0)).isInstanceOf(IndexOutOfBoundsException.class);
        assertThatThrownBy(() -> new LaunchOption(-1, "x", 0, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void wiseChoiceAndSeededSail() {
        LaunchWindowQuest q = new LaunchWindowQuest(P, Reading.LOW);
        assertThat(q.stage()).isEqualTo(LaunchWindowQuest.Stage.FORECAST);
        assertThat(q.keeperLine()).contains("Glass reads LOW").contains(q.best().routeName());
        assertThatThrownBy(() -> q.sail(1)).isInstanceOf(IllegalStateException.class);
        q.choose(q.best().route(), q.best().day());
        assertThat(q.wise()).isTrue();
        assertThat(q.keeperLine()).contains("fair launch");
        assertThatThrownBy(() -> q.choose(0, 0)).isInstanceOf(IllegalStateException.class);
        double home = q.sail(42);
        assertThat(q.stage()).isEqualTo(LaunchWindowQuest.Stage.SAILED);
        assertThat(home).isEqualTo(q.lifeHome()).isBetween(0.0, 120.0);
        assertThat(q.launchSky()).isNotNull();
        assertThat(q.keeperLine()).contains("souls home");
        LaunchWindowQuest again = new LaunchWindowQuest(P, Reading.LOW);
        again.choose(q.best().route(), q.best().day());
        assertThat(again.sail(42)).isEqualTo(home);
        assertThat(again.launchSky()).isEqualTo(q.launchSky());
    }

    @Test
    void poorChoiceGetsTheKeepersWarning() {
        LaunchWindowQuest q = new LaunchWindowQuest(P, Reading.LOW);
        assertThat(q.wise()).isFalse();
        q.choose(1, 0);
        assertThat(q.wise()).isFalse();
        assertThat(q.keeperLine()).contains("Your call, captain");
        assertThat(q.chosen().routeName()).isEqualTo("Squall Lanes");
    }

    @Test
    void waitingCostsLifeWhenTheSkyIsAlreadyKnown() {
        LaunchPlanner sure = new LaunchPlanner(StormGlass.ODDSREAPER, P.routes().subList(0, 1), 2, 0.9);
        assertThat(sure.best(Reading.HIGH).day()).isZero();
        assertThat(sure.expectedLife(Reading.HIGH, 0, 2))
                .isCloseTo(sure.expectedLife(Reading.HIGH, 0, 0) * 0.81, within(1e-9));
    }
}
