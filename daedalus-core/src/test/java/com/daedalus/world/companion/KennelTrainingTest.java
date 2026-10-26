// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelTraining.Drill;
import com.daedalus.world.companion.KennelTraining.QuestResult;
import com.daedalus.world.companion.KennelTraining.Trainee;

import org.junit.jupiter.api.Test;

class KennelTrainingTest {
    @Test
    void oddsScaleWithBondAndDifficulty() {
        assertThat(KennelTraining.successPct(30, "come")).isEqualTo(55);
        assertThat(KennelTraining.successPct(60, "stay")).isEqualTo(60);
        assertThat(KennelTraining.successPct(100, "come")).isEqualTo(90);
        assertThat(KennelTraining.successPct(0, "rescue")).isEqualTo(5);
        assertThatThrownBy(() -> KennelTraining.successPct(50, "sit")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void threeStraightSuccessesTeachAndAddBond() {
        Trainee t = Trainee.fresh("pip", 60);
        Drill a = KennelTraining.drill(t, "stay", 0.0);
        Drill b = KennelTraining.drill(a.after(), "stay", 10.0);
        assertThat(b.after().streak()).containsEntry("stay", 2);
        Drill c = KennelTraining.drill(b.after(), "stay", 59.0);
        assertThat(c.learnedNow()).isTrue();
        assertThat(c.after().learned()).containsExactly("stay");
        assertThat(c.after().bond()).isEqualTo(62);
        assertThat(KennelTraining.drill(c.after(), "stay", 0.0).blockedReason()).isEqualTo("already learned");
    }

    @Test
    void aMissResetsTheStreak() {
        Trainee t = Trainee.fresh("pip", 60);
        Drill a = KennelTraining.drill(KennelTraining.drill(t, "come", 1.0).after(), "come", 1.0);
        Drill miss = KennelTraining.drill(a.after(), "come", 99.0);
        assertThat(miss.success()).isFalse();
        assertThat(miss.after().streak()).doesNotContainKey("come");
        assertThat(miss.after().learned()).isEmpty();
    }

    @Test
    void lockedCommandsCannotBeDrilled() {
        Drill d = KennelTraining.drill(Trainee.fresh("pip", 30), "stay", 0.0);
        assertThat(d.blockedReason()).isEqualTo("bond too low");
        assertThat(d.after()).isEqualTo(Trainee.fresh("pip", 30));
    }

    @Test
    void seededDrillsMatchTheOdds() {
        int ok = 0;
        for (long s = 0; s < 4000; s++) {
            if (KennelTraining.drill(Trainee.fresh("rex", 60), "stay", s).success()) {
                ok++;
            }
        }
        assertThat(ok / 4000.0).isBetween(0.56, 0.64);
        assertThat(KennelTraining.drill(Trainee.fresh("rex", 60), "stay", 42L))
            .isEqualTo(KennelTraining.drill(Trainee.fresh("rex", 60), "stay", 42L));
    }

    @Test
    void firstWordsQuest() {
        QuestResult wary = KennelTraining.firstWords(Trainee.fresh("pip", 20), 1);
        assertThat(wary.complete()).isFalse();
        assertThat(wary.failReason()).contains("bond too low");
        int passed = 0;
        for (long s = 0; s < 200; s++) {
            QuestResult q = KennelTraining.firstWords(Trainee.fresh("pip", 90), s);
            if (q.complete()) {
                passed++;
                assertThat(q.after().learned()).contains("come", "stay");
                assertThat(q.sessionsUsed()).isBetween(1, KennelTraining.QUEST_SESSIONS);
            }
        }
        assertThat(passed).isGreaterThan(150);
        int loyalPassed = 0;
        for (long s = 0; s < 200; s++) {
            if (KennelTraining.firstWords(Trainee.fresh("pip", 50), s).complete()) {
                loyalPassed++;
            }
        }
        assertThat(loyalPassed).isLessThan(passed);
    }
}