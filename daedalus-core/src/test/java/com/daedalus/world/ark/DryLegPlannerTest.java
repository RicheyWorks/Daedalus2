// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.ArkCellar.Day;
import com.daedalus.world.ark.ArkCellar.Rules;
import com.daedalus.world.ark.DryLegPlanner.Plan;
import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

class DryLegPlannerTest {

    private static final Rules SMALL = new Rules(40, 2, 15, 4, 10,
            Map.of(Tier.T1, 0.5, Tier.T2, 0.5, Tier.T3, 0.75, Tier.T4, 1.0));

    private final ArkCellar big = new ArkCellar(Rules.defaults());
    private final DryLegPlanner planner = new DryLegPlanner(big);

    @Test
    void plannedLegsAreAlwaysSafeOnSeededForecasts() {
        for (long seed = 1; seed <= 150; seed++) {
            List<Boolean> rain = DryLegPlanner.forecast(seed, 20, 30);
            for (Tier t : Tier.values()) {
                Plan p = planner.plan(200 + seed, rain, t);
                assertThat(planner.safe(200 + seed, p.days())).isTrue();
                assertThat(p.bottlesPerDay()).hasSize(20).allMatch(n -> n >= 0);
            }
        }
    }

    @Test
    void plannerMatchesExhaustiveSearchOnShortLegs() {
        DryLegPlanner small = new DryLegPlanner(new ArkCellar(SMALL));
        for (long seed = 1; seed <= 20; seed++) {
            List<Boolean> rain = DryLegPlanner.forecast(seed, 3, 40);
            double start = 20 + (seed % 15);
            int best = bruteForce(small, start, rain, new ArrayList<>(), 30);
            if (best < 0) {
                continue;
            }
            assertThat(small.plan(start, rain, Tier.T4).total()).as("seed %d", seed).isEqualTo(best);
        }
    }

    @Test
    void naiveDailyBottlingRunsDryWherePlannerDoesNot() {
        List<Boolean> drought = Collections.nCopies(10, false);
        List<Day> naive = DryLegPlanner.days(drought, Tier.T4, Collections.nCopies(10, 5));
        assertThat(planner.safe(150, naive)).isFalse();
        Plan p = planner.plan(150, drought, Tier.T4);
        assertThat(planner.safe(150, p.days())).isTrue();
        assertThat(p.total()).isGreaterThan(0);
    }

    @Test
    void questUsesThePlanAndReportsItsOwnId() {
        List<Boolean> rain = DryLegPlanner.forecast(201, 12, 35);
        Plan p = planner.plan(200, rain, Tier.T3);
        var ok = planner.quest(200, rain, Tier.T3, p.total());
        assertThat(ok.questId()).isEqualTo(DryLegPlanner.QUEST_ID);
        assertThat(ok.passed()).isTrue();
        assertThat(planner.quest(200, rain, Tier.T3, p.total() + 1).passed()).isFalse();
    }

    @Test
    void forecastIsSeededAndInputsAreValidated() {
        assertThat(DryLegPlanner.forecast(7, 30, 50)).isEqualTo(DryLegPlanner.forecast(7, 30, 50));
        assertThat(DryLegPlanner.forecast(7, 30, 0)).containsOnly(false);
        assertThatThrownBy(() -> DryLegPlanner.forecast(1, 3, 101))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DryLegPlanner.days(List.of(true), Tier.T1, List.of()))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static int bruteForce(DryLegPlanner p, double start, List<Boolean> rain,
                                  List<Integer> prefix, int maxPerDay) {
        if (prefix.size() == rain.size()) {
            List<Day> plan = DryLegPlanner.days(rain, Tier.T4, prefix);
            return p.safe(start, plan) ? prefix.stream().mapToInt(Integer::intValue).sum() : -1;
        }
        int best = -1;
        for (int k = 0; k <= maxPerDay; k++) {
            prefix.add(k);
            best = Math.max(best, bruteForce(p, start, rain, prefix, maxPerDay));
            prefix.remove(prefix.size() - 1);
        }
        return best;
    }
}
