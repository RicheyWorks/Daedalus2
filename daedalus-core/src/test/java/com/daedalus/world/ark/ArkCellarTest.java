// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.ArkCellar.Day;
import com.daedalus.world.ark.ArkCellar.DayReport;
import com.daedalus.world.ark.ArkCellar.QuestResult;
import com.daedalus.world.ark.ArkCellar.Rules;
import com.daedalus.world.ark.ArkCellar.State;
import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import org.junit.jupiter.api.Test;

class ArkCellarTest {

    private final ArkCellar cellar = new ArkCellar(Rules.defaults());

    @Test
    void waterIsConservedEveryDayOverSeededPlans() {
        for (long seed = 1; seed <= 200; seed++) {
            Random rnd = new Random(seed);
            State s = cellar.start(rnd.nextInt(401));
            for (int day = 0; day < 40; day++) {
                DayReport r = cellar.day(s, day, randomDay(rnd));
                double expected = s.cisternL() + r.inflowL() - r.spilledL() - r.crewL() - r.bottlingL();
                assertThat(r.state().cisternL()).isCloseTo(Math.max(0, expected),
                        org.assertj.core.data.Offset.offset(1e-6));
                assertThat(r.state().cisternL()).isLessThanOrEqualTo(400 + 1e-9);
                assertThat(r.state().cellar().size())
                        .isEqualTo(s.cellar().size() - r.expired() + r.bottled());
                s = r.state();
            }
        }
    }

    @Test
    void bottlingNeverDrawsBelowReserve() {
        State s = cellar.start(100);
        DayReport r = cellar.day(s, 0, new Day(false, Map.of(Tier.T4, 50)));
        // 100 + 20 spring - 25 crew = 95 L; 80 L reserve leaves room for 15 one-litre T4 bottles
        assertThat(r.bottled()).isEqualTo(15);
        assertThat(r.refused()).isEqualTo(35);
        assertThat(r.state().cisternL()).isCloseTo(80.0, org.assertj.core.data.Offset.offset(1e-9));
        assertThat(r.belowReserve()).isFalse();
    }

    @Test
    void rainFillsUpToCapAndSpills() {
        DayReport r = cellar.day(cellar.start(390), 0, new Day(true, Map.of()));
        assertThat(r.inflowL()).isEqualTo(80.0);
        assertThat(r.spilledL()).isEqualTo(70.0);
        assertThat(r.state().cisternL()).isEqualTo(375.0);
    }

    @Test
    void bottlesLeaveTheShelfAfterTheirTierShelfDays() {
        State s = cellar.day(cellar.start(300), 0,
                new Day(false, Map.of(Tier.T1, 1, Tier.T4, 1))).state();
        int t1Days = Tier.T1.shelfDays();
        for (int day = 1; day <= t1Days; day++) {
            s = cellar.day(s, day, Day.dry()).state();
        }
        assertThat(s.cellar()).hasSize(2);
        DayReport after = cellar.day(s, t1Days + 1, Day.dry());
        assertThat(after.expired()).isEqualTo(1);
        assertThat(after.state().cellar()).extracting(ArkCellar.Lot::tier).containsExactly(Tier.T4);
    }

    @Test
    void questPassesWithSteadyBottlingAndFailsWhenTheCisternRunsLow() {
        List<Day> steady = new ArrayList<>();
        for (int i = 0; i < 7; i++) {
            steady.add(new Day(i % 3 == 0, Map.of(Tier.T3, 2, Tier.T4, 1)));
        }
        QuestResult ok = cellar.quest(200, steady, 12, Tier.T3.level());
        assertThat(ok.questId()).isEqualTo(ArkCellar.QUEST_ID);
        assertThat(ok.passed()).isTrue();
        assertThat(ok.bottlesOnShelf()).isEqualTo(21);

        List<Day> drought = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            drought.add(Day.dry());
        }
        QuestResult dry = cellar.quest(100, drought, 0, Tier.T1.level());
        assertThat(dry.passed()).isFalse();
        assertThat(dry.log()).anyMatch(DayReport::belowReserve);
    }

    @Test
    void replayIsDeterministicAndRulesAreValidated() {
        List<Day> plan = new ArrayList<>();
        Random rnd = new Random(196);
        for (int i = 0; i < 30; i++) {
            plan.add(randomDay(rnd));
        }
        assertThat(cellar.quest(150, plan, 5, 1)).isEqualTo(cellar.quest(150, plan, 5, 1));
        assertThatThrownBy(() -> new Rules(10, 1, 1, 1, 20, Rules.defaults().waterPerBottleL()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Day(false, Map.of(Tier.T1, -1)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static Day randomDay(Random rnd) {
        Map<Tier, Integer> b = new EnumMap<>(Tier.class);
        for (Tier t : Tier.values()) {
            b.put(t, rnd.nextInt(6));
        }
        return new Day(rnd.nextInt(3) == 0, b);
    }
}
