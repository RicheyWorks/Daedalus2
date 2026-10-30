// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.companion.KennelSeason.Member;
import com.daedalus.world.companion.KennelSeason.SeasonDay;
import com.daedalus.world.companion.KennelSeason.SeasonResult;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class KennelSeasonTest {
    private static final List<Member> ROSTER = List.of(new Member("tank", "cane_corso", "cane_corso", 20),
        new Member("rex", "dog", "dog", 30), new Member("bo", "dog", "dog", 25), new Member("pip", "dog", "pup", 20));
    private static final KennelWaterLoop.Day CLEAR = new KennelWaterLoop.Day(false, true, false, false, 0);
    private static final KennelPantry.Day PLENTY = new KennelPantry.Day(4, 4, 6);
    private static final KennelPantry.Day NO_GRAZING = new KennelPantry.Day(4, 0, 0);
    private static KennelSeason season;

    private static Path data(String f) {
        Path p = Path.of("..", "data", "islands", f);
        return Files.exists(p) ? p : Path.of("data", "islands", f);
    }

    @BeforeAll
    static void load() throws Exception {
        season = new KennelSeason(KennelWaterLoop.load(data("kennel-water-v1.json")),
            KennelPantry.load(data("kennel-food-v1.json")), KennelBond.Rules.defaults());
    }

    @Test
    void clearDaysWithPlentyRaiseEveryBondByBasicCare() {
        SeasonResult r = season.run(ROSTER, Collections.nCopies(3, SeasonDay.plain(CLEAR, PLENTY)), 0);
        assertThat(r.neglectDays().values()).containsOnly(0);
        assertThat(r.finalBonds()).containsEntry("tank", 35).containsEntry("rex", 45).containsEntry("pip", 35);
        assertThat(r.days()).hasSize(3);
        assertThat(r.days().get(0).cisternL()).isGreaterThan(0);
    }

    @Test
    void tonicAndFetchAddToOnePet() {
        SeasonDay d = new SeasonDay(CLEAR, PLENTY, Set.of("pip"), Map.of("pip", 3));
        SeasonResult r = season.run(ROSTER, List.of(d), 0);
        assertThat(r.finalBonds()).containsEntry("pip", 31).containsEntry("bo", 30);
    }

    @Test
    void unpreparedStormStarvesThePackAndFails() {
        SeasonResult r = season.run(ROSTER, KennelSeason.stormWeek(NO_GRAZING, NO_GRAZING), 0);
        assertThat(r.neglectDays().values()).allMatch(n -> n > 0);
        assertThat(KennelSeason.stormSeason(r)).isFalse();
    }

    @Test
    void stockpiledKibbleAndCisternCarryThePackThroughTheStorm() {
        SeasonResult r = season.run(ROSTER, KennelSeason.stormWeek(PLENTY, NO_GRAZING), 0);
        assertThat(r.days().get(1).kibble()).isGreaterThan(r.days().get(4).kibble());
        assertThat(r.days().subList(2, 5)).allMatch(l -> l.thirsty().isEmpty() && l.hungry().isEmpty());
        assertThat(r.neglectDays().values()).containsOnly(0);
        assertThat(KennelSeason.stormSeason(r)).isTrue();
    }

    @Test
    void stormWithAnEmptyCisternLeavesEveryoneThirsty() {
        KennelWaterLoop.Day storm = new KennelWaterLoop.Day(true, false, true, true, 0);
        SeasonResult r = season.run(ROSTER, List.of(SeasonDay.plain(storm, PLENTY)), 0);
        assertThat(r.days().get(0).thirsty()).containsExactlyInAnyOrder("tank", "rex", "bo", "pip");
        assertThat(r.finalBonds()).containsEntry("rex", 19);
    }

    @Test
    void stormWeekShape() {
        List<SeasonDay> w = KennelSeason.stormWeek(PLENTY, NO_GRAZING);
        assertThat(w).hasSize(7);
        assertThat(w.get(2).water().filterClogged()).isTrue();
        assertThat(w.get(5).water().filterClogged()).isFalse();
        assertThat(w.get(3).food()).isEqualTo(NO_GRAZING);
    }
}