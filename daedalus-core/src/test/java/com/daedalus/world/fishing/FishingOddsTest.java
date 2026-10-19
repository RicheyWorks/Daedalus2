// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class FishingOddsTest {

    private final FishTable pond = FishTestData.prism();

    @Test
    void exactOddsMultiplyBiteShareByCatchChance() {
        FishTable pair = FishTestData.pair();
        AnglerSkill skill = new AnglerSkill(0.7, 0);
        FishingOdds.Breakdown b = FishingOdds.exact(pair, Conditions.DAY, skill);
        assertThat(b.catchShare("minnow")).isEqualTo(0.75);
        assertThat(b.catchShare("moonfish")).isZero();
        assertThat(b.landChance()).isEqualTo(0.75);
        assertThat(b.expectedValue()).isEqualTo(0.75 * 5);
        assertThat(b.rareShare()).isZero();
        assertThat(b.castsToLand("minnow")).isCloseTo(4.0 / 3, within(1e-12));
        assertThat(b.castsToLand("moonfish")).isInfinite();
        assertThat(b.conditions()).isEqualTo(Conditions.DAY);
        assertThat(b.skill()).isEqualTo(skill);
        assertThat(b.lines()).hasSize(2);
        assertThatThrownBy(() -> b.catchShare("nope")).hasMessageContaining("nope");

        FishingOdds.Breakdown night = FishingOdds.exact(pair, Conditions.NIGHT, new AnglerSkill(0.2, 0));
        assertThat(night.catchShare("moonfish")).isEqualTo(0.5);
        assertThat(night.rareShare()).isEqualTo(0.5);
        assertThat(night.expectedValue()).isEqualTo(0.5 * 5 + 0.5 * 100);
    }

    @Test
    void stormRaisesRareOddsButCostsCommonLandings() {
        FishingOdds.Breakdown day = FishingOdds.exact(pond, Conditions.DAY, AnglerSkill.STEADY);
        FishingOdds.Breakdown storm = FishingOdds.exact(pond, Conditions.STORM, AnglerSkill.STEADY);
        assertThat(storm.rareShare()).isGreaterThan(day.rareShare());
        assertThat(storm.landChance()).isLessThan(day.landChance());
        assertThat(FishingOdds.exact(pond, Conditions.DAY, AnglerSkill.OLD_HAND).expectedValue())
                .isGreaterThan(FishingOdds.exact(pond, Conditions.DAY, AnglerSkill.NOVICE).expectedValue());
    }

    @Test
    void simulationAgreesWithTheExactOdds() {
        for (Conditions c : List.of(Conditions.DAY, Conditions.NIGHT, Conditions.STORM)) {
            FishingOdds.Breakdown b = FishingOdds.exact(pond, c, AnglerSkill.STEADY);
            FishingOdds.Simulation s = FishingOdds.simulate(pond, c, AnglerSkill.STEADY, 11, 6000);
            assertThat(s.casts()).isEqualTo(6000);
            assertThat(s.seed()).isEqualTo(11);
            assertThat(s.low()).as(c.label()).isLessThanOrEqualTo(b.landChance() + 0.01);
            assertThat(s.high()).as(c.label()).isGreaterThanOrEqualTo(b.landChance() - 0.01);
            assertThat(s.landRate()).isBetween(s.low(), s.high());
            assertThat(s.meanValue()).isCloseTo(b.expectedValue(), within(b.expectedValue() * 0.2));
            int sum = s.catches().values().stream().mapToInt(Integer::intValue).sum();
            assertThat(sum).isEqualTo(s.landed());
        }
    }

    @Test
    void simulationIsDeterministicAndReadOnly() {
        FishingOdds.Simulation a = FishingOdds.simulate(pond, Conditions.NIGHT, AnglerSkill.NOVICE, 5, 500);
        FishingOdds.Simulation b = FishingOdds.simulate(pond, Conditions.NIGHT, AnglerSkill.NOVICE, 5, 500);
        assertThat(a.landed()).isEqualTo(b.landed());
        assertThat(a.catches()).isEqualTo(b.catches());
        Map<String, Integer> copy = a.catches();
        copy.clear();
        assertThat(a.catches()).hasSize(6);
        assertThatThrownBy(() -> FishingOdds.simulate(pond, Conditions.DAY, AnglerSkill.NOVICE, 5, 0))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void stormParlayPricesConsecutiveCatchesAtFairOdds() {
        FishTable pair = FishTestData.pair();
        AnglerSkill sure = new AnglerSkill(0.1, 0);
        FishingOdds.Parlay p = FishingOdds.parlay(pair, Conditions.DAY, sure, List.of("minnow", "moonfish"));
        assertThat(p.legs()).isEqualTo(2);
        assertThat(p.probability()).isCloseTo(0.75 * 0.25, within(1e-12));
        assertThat(p.fairMultiplier()).isCloseTo(1 / (0.75 * 0.25), within(1e-9));
        assertThat(p.expectedProfit(10, p.fairMultiplier())).isCloseTo(0, within(1e-9));
        assertThat(p.expectedProfit(10, 2)).isNegative();
        assertThat(p.fair(p.fairMultiplier())).isTrue();
        assertThat(p.fair(3)).isFalse();

        FishingOdds.Parlay storm = FishingOdds.parlay(pair, Conditions.STORM, sure, List.of("moonfish"));
        assertThat(storm.probability()).isGreaterThan(0.25);

        FishingOdds.Parlay never = FishingOdds.parlay(pair, Conditions.DAY, new AnglerSkill(0.7, 0), List.of("moonfish"));
        assertThat(never.probability()).isZero();
        assertThat(never.fairMultiplier()).isInfinite();
        assertThatThrownBy(() -> FishingOdds.parlay(pair, Conditions.DAY, sure, List.of())).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FishingOdds.parlay(pair, Conditions.DAY, sure, null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FishingOdds.parlay(pair, Conditions.DAY, sure, List.of("eel"))).hasMessageContaining("eel");
    }

    @Test
    void describeListsEveryFish() {
        String text = FishingOdds.describe(FishingOdds.exact(pond, Conditions.NIGHT, AnglerSkill.STEADY));
        assertThat(text).startsWith("night, reaction 0.40s");
        for (FishSpecies f : pond.fish()) {
            assertThat(text).contains(f.name());
        }
    }
}
