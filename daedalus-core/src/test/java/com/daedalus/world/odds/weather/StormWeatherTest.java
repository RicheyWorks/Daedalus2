// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.weather;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.fishing.Conditions;
import com.daedalus.world.fishing.FishTable;
import com.daedalus.world.odds.OddsRng;
import com.daedalus.world.odds.parlay.ParlayTicket;
import com.daedalus.world.odds.weather.StormGlass.Reading;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;

class StormWeatherTest {

    private final StormChain chain = StormChain.ODDSREAPER;
    private final StormGlass glass = StormGlass.ODDSREAPER;

    @Test
    void chainStepsByItsMatrix() {
        assertThat(chain.p(Sky.STORM, Sky.STORM)).isEqualTo(0.50);
        assertThat(chain.next(Sky.CALM, 0.0)).isEqualTo(Sky.CALM);
        assertThat(chain.next(Sky.CALM, 0.69)).isEqualTo(Sky.CALM);
        assertThat(chain.next(Sky.CALM, 0.71)).isEqualTo(Sky.SQUALL);
        assertThat(chain.next(Sky.CALM, 0.95)).isEqualTo(Sky.STORM);
        assertThat(chain.next(Sky.STORM, Math.nextDown(1.0))).isEqualTo(Sky.STORM);
        assertThatThrownBy(() -> chain.next(Sky.CALM, 1.0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> chain.next(Sky.CALM, Double.NaN)).isInstanceOf(IllegalArgumentException.class);
        double[] d = chain.step(StormChain.certain(Sky.SQUALL));
        assertThat(d).containsExactly(new double[] {0.30, 0.40, 0.30}, within(1e-12));
        assertThat(chain.after(StormChain.certain(Sky.CALM), 0)).containsExactly(1.0, 0.0, 0.0);
    }

    @Test
    void leftoverRoundingFallsToTheLastSky() {
        StormChain tiny = new StormChain(new double[][] {{0.1, 0.2, 0.7}, {0.1, 0.2, 0.7}, {0.1, 0.2, 0.7}});
        assertThat(tiny.next(Sky.CALM, Math.nextDown(1.0))).isEqualTo(Sky.STORM);
    }

    @Test
    void climateIsStationaryAndStormy() {
        double[] c = chain.climate();
        assertThat(c[0] + c[1] + c[2]).isCloseTo(1.0, within(1e-9));
        assertThat(chain.step(c)).containsExactly(c, within(1e-9));
        assertThat(c[Sky.STORM.ordinal()]).isBetween(0.15, 0.35);
    }

    @Test
    void seasonsAreSeededAndMatchTheClimate() {
        List<Sky> a = chain.season(42, Sky.CALM, 4000);
        assertThat(chain.season(42, Sky.CALM, 4000)).isEqualTo(a);
        assertThat(a.get(0)).isEqualTo(Sky.CALM);
        assertThat(chain.skyOn(42, Sky.CALM, 123)).isEqualTo(a.get(123));
        long storms = a.stream().filter(s -> s == Sky.STORM).count();
        assertThat(storms / 4000.0).isCloseTo(chain.climate()[2], within(0.03));
        assertThat(chain.season(43, Sky.CALM, 50)).isNotEqualTo(a.subList(0, 50));
        assertThatThrownBy(() -> chain.season(1, Sky.CALM, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> chain.skyOn(1, Sky.CALM, -1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void badMatricesAndDistributionsAreRefused() {
        assertThatThrownBy(() -> new StormChain(null)).hasMessageContaining("3x3");
        assertThatThrownBy(() -> new StormChain(new double[2][3])).hasMessageContaining("3x3");
        assertThatThrownBy(() -> new StormChain(new double[][] {{1, 0, 0}, {1, 0}, {1, 0, 0}})).hasMessageContaining("3x3");
        assertThatThrownBy(() -> new StormChain(new double[][] {{1, 0, 0}, null, {1, 0, 0}})).hasMessageContaining("3x3");
        assertThatThrownBy(() -> new StormChain(new double[][] {{0.5, 0.4, 0}, {1, 0, 0}, {1, 0, 0}})).hasMessageContaining("sums");
        assertThatThrownBy(() -> new StormChain(new double[][] {{1.5, -0.5, 0}, {1, 0, 0}, {1, 0, 0}}))
                .hasMessageContaining("[0, 1]");
        assertThatThrownBy(() -> chain.step(new double[] {0.5, 0.5})).hasMessageContaining("3 entries");
        assertThatThrownBy(() -> chain.step(null)).hasMessageContaining("3 entries");
        assertThatThrownBy(() -> chain.step(new double[] {0.5, 0.6, -0.1})).hasMessageContaining(">= 0");
        assertThatThrownBy(() -> chain.step(new double[] {0.5, 0.6, 0.1})).hasMessageContaining("sum to 1");
        assertThatThrownBy(() -> chain.after(StormChain.certain(Sky.CALM), -1)).hasMessageContaining("steps");
        double[][] m = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}};
        StormChain stuck = new StormChain(m);
        m[0][0] = 0;
        assertThat(stuck.p(Sky.CALM, Sky.CALM)).isEqualTo(1.0);
    }

    @Test
    void glassUpdatesByBayes() {
        double[] prior = {1.0 / 3, 1.0 / 3, 1.0 / 3};
        double[] low = glass.posterior(prior, Reading.LOW);
        assertThat(low[2]).isCloseTo(0.70 / 0.95, within(1e-12));
        assertThat(low[0] + low[1] + low[2]).isCloseTo(1.0, within(1e-12));
        assertThat(glass.likelihood(Sky.CALM, Reading.HIGH)).isEqualTo(0.75);
        assertThat(glass.stormChance(Reading.LOW, 0)).isGreaterThan(glass.stormChance(Reading.FALLING, 0));
        assertThat(glass.stormChance(Reading.FALLING, 0)).isGreaterThan(glass.stormChance(Reading.HIGH, 0));
        assertThat(glass.stormChance(Reading.LOW, 30)).isCloseTo(chain.climate()[2], within(1e-6));
        assertThat(glass.stormChance(Reading.LOW, 1)).isLessThan(glass.stormChance(Reading.LOW, 0));
        assertThat(glass.forecast(prior, Reading.HIGH, 1)).hasSize(3);
        assertThat(glass.chain()).isSameAs(chain);
        StormGlass blind = new StormGlass(chain, new double[][] {{1, 0, 0}, {1, 0, 0}, {1, 0, 0}});
        assertThatThrownBy(() -> blind.posterior(prior, Reading.LOW)).hasMessageContaining("impossible");
        assertThatThrownBy(() -> new StormGlass(null, new double[3][3])).hasMessageContaining("chain");
    }

    @Test
    void glassReadingsAreNoisyButHonest() {
        assertThat(glass.read(Sky.CALM, 0.1)).isEqualTo(Reading.HIGH);
        assertThat(glass.read(Sky.CALM, 0.8)).isEqualTo(Reading.FALLING);
        assertThat(glass.read(Sky.STORM, 0.5)).isEqualTo(Reading.LOW);
        assertThat(glass.read(Sky.STORM, Math.nextDown(1.0))).isEqualTo(Reading.LOW);
        assertThatThrownBy(() -> glass.read(Sky.CALM, -0.1)).isInstanceOf(IllegalArgumentException.class);
        OddsRng rng = new OddsRng(3);
        int lows = 0;
        for (int i = 0; i < 10000; i++) {
            if (glass.read(Sky.STORM, rng.nextDouble()) == Reading.LOW) {
                lows++;
            }
        }
        assertThat(lows / 10000.0).isCloseTo(0.70, within(0.02));
        assertThat(glass.readOn(9, Sky.CALM, 5)).isEqualTo(glass.readOn(9, Sky.CALM, 5));
    }

    @Test
    void forecastsFromTheGlassBeatTheAlmanac() {
        ForecastScore glassScore = new ForecastScore();
        ForecastScore almanac = new ForecastScore();
        double climateStorm = chain.climate()[2];
        List<Sky> season = chain.season(17, Sky.CALM, 3000);
        for (int d = 0; d < season.size(); d++) {
            boolean storm = season.get(d) == Sky.STORM;
            glassScore.add(glass.stormChance(glass.readOn(17, Sky.CALM, d), 0), storm);
            almanac.add(climateStorm, storm);
        }
        assertThat(glassScore.mean()).isLessThan(almanac.mean());
        assertThat(glassScore.skill(climateStorm)).isGreaterThan(0.1);
        assertThat(almanac.skill(climateStorm)).isCloseTo(0.0, within(1e-9));
    }

    @Test
    void brierScoringAndTheReadTheGlassQuest() {
        assertThat(ForecastScore.brier(0.8, true)).isCloseTo(0.04, within(1e-12));
        assertThat(ForecastScore.brier(0.8, false)).isCloseTo(0.64, within(1e-12));
        assertThatThrownBy(() -> ForecastScore.brier(1.2, true)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ForecastScore.brier(Double.NaN, true)).isInstanceOf(IllegalArgumentException.class);
        ForecastScore s = new ForecastScore();
        assertThat(s.mean()).isZero();
        assertThat(s.skill(0.3)).isNaN();
        for (int i = 0; i < 4; i++) {
            s.add(0.9, true);
        }
        assertThat(s.questPassed()).isFalse();
        assertThat(s.add(0.1, false)).isCloseTo(0.01, within(1e-12));
        assertThat(s.count()).isEqualTo(5);
        assertThat(s.questPassed()).isTrue();
        s.add(1.0, false);
        s.add(1.0, false);
        assertThat(s.questPassed()).isFalse();
        ForecastScore sure = new ForecastScore();
        sure.add(1.0, true);
        assertThat(sure.skill(1.0)).isEqualTo(1.0);
        ForecastScore wrong = new ForecastScore();
        wrong.add(0.0, true);
        assertThat(wrong.skill(1.0)).isNegative().isInfinite();
    }

    @Test
    void stormDaysDriveFishingAndTheParlayBoard() throws IOException {
        assertThat(StormDay.conditions(Sky.STORM, 8)).isEqualTo(Conditions.STORM);
        assertThat(StormDay.conditions(Sky.SQUALL, 20)).isEqualTo(Conditions.NIGHT);
        assertThat(StormDay.sky(5, 0)).isEqualTo(Sky.CALM);
        FishTable pond = FishTable.fromJson(Files.readString(Path.of("..", "data", "rpg", "prism-fish.json"), StandardCharsets.UTF_8));
        int stormDay = -1;
        for (int d = 1; d < 60 && stormDay < 0; d++) {
            if (StormDay.sky(5, d) == Sky.STORM) {
                stormDay = d;
            }
        }
        assertThat(stormDay).isPositive();
        List<ParlayTicket> board = StormDay.board(pond, 5, stormDay, 4, 2);
        assertThat(board).isNotEmpty().allSatisfy(t -> assertThat(t.conditions().storm()).isTrue());
        assertThat(StormDay.board(pond, 5, 0, 4, 2)).allSatisfy(t -> assertThat(t.conditions().storm()).isFalse());
    }
}
