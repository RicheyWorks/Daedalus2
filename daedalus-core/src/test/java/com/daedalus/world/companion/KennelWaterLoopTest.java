// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelWaterLoop.Animal;
import com.daedalus.world.companion.KennelWaterLoop.Day;
import com.daedalus.world.companion.KennelWaterLoop.DayReport;
import com.daedalus.world.companion.KennelWaterLoop.State;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class KennelWaterLoopTest {
    private static final List<Animal> ROSTER = List.of(
        new Animal("rex", "dog"), new Animal("bo", "dog"), new Animal("tank", "cane_corso"),
        new Animal("g1", "goat"), new Animal("g2", "goat"), new Animal("capy", "capybara"));
    private static KennelWaterLoop w;

    @BeforeAll
    static void load() throws Exception {
        Path p = Path.of("..", "data", "islands", "kennel-water-v1.json");
        w = KennelWaterLoop.load(Files.exists(p) ? p : Path.of("data", "islands", "kennel-water-v1.json"));
    }

    @Test
    void rosterNeed() {
        assertThat(w.need(ROSTER)).isEqualTo(2 + 2 + 3 + 4 + 4 + 3);
        assertThatThrownBy(() -> w.need(List.of(new Animal("x", "dragon")))).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void springDayFillsCisternAndSpillsPastFilterCap() {
        DayReport d = w.day(w.start(0), new Day(false, true, false, false, 0), ROSTER, 60);
        assertThat(d.inflowL()).isEqualTo(3000 + 5);
        assertThat(d.spilledL()).isEqualTo(1005);
        assertThat(d.drunkL()).isEqualTo(18);
        assertThat(d.herbL()).isEqualTo(30);
        assertThat(d.state().cisternL()).isEqualTo(2000 - 18 - 30);
        assertThat(d.thirsty()).isEmpty();
    }

    @Test
    void rainCatchersAloneCarryTheIsland() {
        DayReport d = w.day(w.start(0), new Day(true, false, true, false, 0), ROSTER, 0);
        assertThat(d.inflowL()).isEqualTo(3 * 15 * 24);
        assertThat(d.thirsty()).isEmpty();
    }

    @Test
    void clogFilterMeansOnlyStillWater() {
        DayReport d = w.day(w.start(0), new Day(false, true, false, true, 10), ROSTER, 0);
        assertThat(d.inflowL()).isEqualTo(5);
        assertThat(d.thirsty()).hasSize(ROSTER.size());
        assertThat(d.drunkL()).isEqualTo(5);
    }

    @Test
    void thirstStagesDrainAndReset() {
        State s = w.start(0);
        for (int i = 0; i < 7; i++) {
            s = w.day(s, Day.dry(0), ROSTER, 0).state();
        }
        assertThat(s.thirst().get("tank")).isEqualTo(7);
        assertThat(s.drainPct(w.rules(), "tank")).isEqualTo(50);
        s = w.day(s, new Day(false, true, false, false, 0), ROSTER, 0).state();
        assertThat(s.thirst()).isEmpty();
        assertThat(s.drainPct(w.rules(), "tank")).isZero();
    }

    @Test
    void herbsAreWateredLast() {
        DayReport d = w.day(w.start(20), Day.dry(0), ROSTER, 60);
        assertThat(d.drunkL()).isEqualTo(18);
        assertThat(d.herbL()).isEqualTo(2 + 5);
    }

    @Test
    void wellHaulsClampToMax() {
        DayReport d = w.day(w.start(0), new Day(false, false, true, false, 999), List.of(), 0);
        assertThat(d.inflowL()).isEqualTo(40 * 10);
    }

    @Test
    void quietSpringNeedsEnoughHauls() {
        // 18 L/day, still gives 5, so 13 L must be hauled: 2 buckets.
        assertThat(w.minHauls(ROSTER, 0)).isEqualTo(2);
        assertThat(w.quietSpring(ROSTER, 0, List.of(1)).passed()).isFalse();
        var ok = w.quietSpring(ROSTER, 0, List.of(2));
        assertThat(ok.passed()).isTrue();
        assertThat(ok.log()).hasSize(3);
        assertThat(ok.questId()).isEqualTo("kennel_quiet_spring");
    }

    @Test
    void quietSpringBankingWaterEarlyCarriesLaterDays() {
        assertThat(w.quietSpring(ROSTER, 0, List.of(3, 0)).passed()).isFalse();
        assertThat(w.quietSpring(ROSTER, 0, List.of(5, 1)).passed()).isTrue();
    }

    @Test
    void hugeRosterCannotPass() {
        List<Animal> herd = new java.util.ArrayList<>();
        for (int i = 0; i < 200; i++) {
            herd.add(new Animal("goat" + i, "goat"));
        }
        assertThat(w.minHauls(herd, 0)).isEqualTo(-1);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> KennelWaterLoop.parse("{\"version\":3}")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> w.quietSpring(ROSTER, 0, List.of())).isInstanceOf(IllegalArgumentException.class);
        assertThat(w.start(99_999).cisternL()).isEqualTo(2000);
    }
}
