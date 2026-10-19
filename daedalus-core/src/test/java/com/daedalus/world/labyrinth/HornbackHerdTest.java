// SPDX-License-Identifier: MIT

package com.daedalus.world.labyrinth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.battlefield.BattlefieldDemo;
import com.daedalus.world.battlefield.BattlefieldEcology;
import com.daedalus.world.companion.TonicBook;
import com.daedalus.world.companion.TroughBrew;
import com.daedalus.world.labyrinth.HornbackHerd.Outcome;
import com.daedalus.world.labyrinth.HornbackHerd.Report;
import com.daedalus.world.labyrinth.HornbackHerd.Settings;
import com.daedalus.world.labyrinth.HornbackHerd.Trough;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.api.Test;

/** LAB06 Calm the Hornbacks on the BattlefieldDemo meadow (40 x 30 m, oak wood mid-field): water and space rules. */
class HornbackHerdTest {

    static final double SX = 300, SY = 1500, EX = 3700, EY = 1500;

    static Report run(long seed, List<Trough> route, BattlefieldEcology e, Settings s) {
        return HornbackHerd.run(seed, 12, SX, SY, EX, EY, route, HornbackHerd.of(e), s, 180);
    }

    static List<Trough> threeTroughs(int drinksEach) {
        return List.of(new Trough(1000, 1500, HornbackHerd.water(drinksEach)),
                new Trough(1800, 1500, HornbackHerd.water(drinksEach)),
                new Trough(2600, 1500, HornbackHerd.water(drinksEach)));
    }

    static Settings with(double crowdStress, double fireFearCm) {
        Settings d = Settings.DEFAULT;
        return new Settings(d.personalSpaceCm(), d.crowdLimit(), crowdStress, d.panicSpread(), fireFearCm,
                d.fireStress(), d.drinkCalm(), d.drinkRadiusCm(), d.lureCm(), d.calmSpeedCmS(), d.stampedeSpeedCmS(),
                d.stampedeAt(), d.spaceCalm(), d.exitRadiusCm(), d.startStress());
    }

    @ParameterizedTest
    @ValueSource(longs = {1, 2, 3, 42})
    void withoutWaterTheStampedeNeverCalms(long seed) {
        Report r = run(seed, List.of(), BattlefieldDemo.scene(7), Settings.DEFAULT);
        assertThat(r.outcome()).isEqualTo(Outcome.STAMPEDE);
        assertThat(r.calmArrived()).isZero();
        assertThat(r.drinks()).isZero();
    }

    @ParameterizedTest
    @ValueSource(longs = {1, 2, 3, 42})
    void enoughWaterOnTheRouteGuidesTheWholeHerd(long seed) {
        Report r = run(seed, threeTroughs(40), BattlefieldDemo.scene(7), Settings.DEFAULT);
        assertThat(r.outcome()).isEqualTo(Outcome.GUIDED);
        assertThat(r.calmArrived()).isEqualTo(12);
        assertThat(r.burned()).isZero();
        assertThat(r.lost()).isZero();
    }

    @Test
    void aShortTroughCalmsOnlyAsManyAsItHasDrinks() {
        Report r = run(1, List.of(new Trough(1000, 1500, HornbackHerd.water(3))), BattlefieldDemo.scene(7), Settings.DEFAULT);
        assertThat(r.drinks()).isEqualTo(3);
        assertThat(r.calmArrived()).isLessThanOrEqualTo(3);
        assertThat(r.outcome()).isEqualTo(Outcome.STAMPEDE);
    }

    @Test
    void spaceMatters_aHerdThatCannotStandCrowdingStampedesAgainAfterDrinking() {
        Report calm = run(2, List.of(new Trough(1000, 1500, HornbackHerd.water(40))), BattlefieldDemo.scene(7), Settings.DEFAULT);
        Report tight = run(2, List.of(new Trough(1000, 1500, HornbackHerd.water(40))), BattlefieldDemo.scene(7), with(0.05, 400));
        assertThat(calm.outcome()).isEqualTo(Outcome.GUIDED);
        assertThat(tight.drinks()).isEqualTo(12);
        assertThat(tight.outcome()).isEqualTo(Outcome.STAMPEDE);
        assertThat(tight.calmArrived()).isLessThan(calm.calmArrived());
    }

    @ParameterizedTest
    @ValueSource(longs = {1, 2, 3})
    void fireOnTheRouteIsAvoided_andARouteAroundItStillGuides(long seed) {
        BattlefieldEcology burning = BattlefieldDemo.scene(7);
        burning.apply(BattlefieldEcology.EventKind.IGNITE, 2200, 1500, 300);
        assertThat(burning.burningAt(2200, 1500)).isTrue();
        Report fearless = run(seed, List.of(), copyWithFire(), with(Settings.DEFAULT.crowdStress(), 0));
        assertThat(fearless.burned()).as("without fire fear some run into the flames").isPositive();
        Report fearful = run(seed, List.of(), copyWithFire(), Settings.DEFAULT);
        assertThat(fearful.burned()).isZero();
        List<Trough> around = List.of(new Trough(1000, 1500, HornbackHerd.water(40)),
                new Trough(1800, 2600, HornbackHerd.water(40)), new Trough(2800, 2600, HornbackHerd.water(40)));
        Report guided = run(seed, around, burning, Settings.DEFAULT);
        assertThat(guided.outcome()).isEqualTo(Outcome.GUIDED);
        assertThat(guided.burned()).isZero();
    }

    static BattlefieldEcology copyWithFire() {
        BattlefieldEcology e = BattlefieldDemo.scene(7);
        e.apply(BattlefieldEcology.EventKind.IGNITE, 2200, 1500, 300);
        return e;
    }

    @Test
    void sameSeedSameRun_differentSeedDifferentHerd() {
        Report a = run(9, threeTroughs(40), BattlefieldDemo.scene(7), Settings.DEFAULT);
        Report b = run(9, threeTroughs(40), BattlefieldDemo.scene(7), Settings.DEFAULT);
        Report c = run(10, threeTroughs(40), BattlefieldDemo.scene(7), Settings.DEFAULT);
        assertThat(a).isEqualTo(b);
        assertThat(c.steps() != a.steps() || c.peakStress() != a.peakStress()).isTrue();
    }

    @Test
    void denseCoverSlowsTheHerd() {
        BattlefieldEcology meadow = new BattlefieldEcology(40, 30, 100, 0, 0, 1);
        BattlefieldEcology oak = new BattlefieldEcology(40, 30, 100, 0, 0, 1);
        for (int j = 0; j < 30; j++) {
            for (int i = 0; i < 40; i++) {
                meadow.set(i, j, com.daedalus.world.battlefield.Vegetation.MEADOW);
                oak.set(i, j, com.daedalus.world.battlefield.Vegetation.OAK);
            }
        }
        Report open = run(4, List.of(), meadow, Settings.DEFAULT);
        Report wood = run(4, List.of(), oak, Settings.DEFAULT);
        assertThat(wood.steps()).isGreaterThan(open.steps());
    }

    @Test
    void aKennelTroughBrewIsUsableWaterAndSpendsItsDrinks() throws IOException {
        Path p = Path.of("..", "tools", "islands", "kennel-isle", "tonics.json");
        if (!Files.exists(p)) {
            p = Path.of("tools", "islands", "kennel-isle", "tonics.json");
        }
        TonicBook book = TonicBook.load(p);
        TroughBrew brew = new TroughBrew(book, book.recipes().get(0), 0);
        int before = brew.drinksLeft();
        Report r = run(1, List.of(new Trough(1000, 1500, HornbackHerd.of(brew))), BattlefieldDemo.scene(7), Settings.DEFAULT);
        assertThat(r.drinks()).isEqualTo(Math.min(12, before));
        assertThat(brew.drinksLeft()).isEqualTo(before - r.drinks());
    }

    @Test
    void refusesBadInput() {
        BattlefieldEcology e = BattlefieldDemo.scene(7);
        assertThatThrownBy(() -> HornbackHerd.run(1, 0, SX, SY, EX, EY, List.of(), HornbackHerd.of(e), Settings.DEFAULT, 10))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HornbackHerd.run(1, 65, SX, SY, EX, EY, List.of(), HornbackHerd.of(e), Settings.DEFAULT, 10))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Trough(Double.NaN, 0, HornbackHerd.water(1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HornbackHerd.water(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> with(-1, 400)).isInstanceOf(IllegalArgumentException.class);
    }
}