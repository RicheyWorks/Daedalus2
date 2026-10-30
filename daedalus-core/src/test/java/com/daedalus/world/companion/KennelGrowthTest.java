// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelBond.Care;
import com.daedalus.world.companion.KennelGrowth.Day;
import com.daedalus.world.companion.KennelGrowth.Pup;
import com.daedalus.world.companion.KennelGrowth.QuestResult;
import com.daedalus.world.companion.KennelGrowth.Stage;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.junit.jupiter.api.Test;

class KennelGrowthTest {
    private static final Care FULL = new Care(true, true, true, 3);
    private static final Care BASIC = new Care(true, true, false, 0);
    private static final Care NEGLECT = new Care(false, true, false, 0);

    @Test
    void stagesFollowCareDays() {
        assertThat(Stage.of(0)).isEqualTo(Stage.NEWBORN);
        assertThat(Stage.of(3)).isEqualTo(Stage.PUP);
        assertThat(Stage.of(9)).isEqualTo(Stage.PUP);
        assertThat(Stage.of(10)).isEqualTo(Stage.JUVENILE);
        assertThat(Stage.of(21)).isEqualTo(Stage.ADULT);
        assertThat(Stage.of(60)).isEqualTo(Stage.ELDER);
        assertThat(Stage.ADULT.scale()).isEqualTo(1.0);
        assertThat(Stage.ELDER.commands()).doesNotContain("rescue");
    }

    @Test
    void careDaysGrowAndNeglectStalls() {
        Day a = KennelGrowth.day(Pup.newborn("pip", 30), BASIC, 0);
        assertThat(a.grew()).isTrue();
        assertThat(a.spurt()).isFalse();
        assertThat(a.after().careDays()).isEqualTo(1);
        Day n = KennelGrowth.day(a.after(), NEGLECT, 0);
        assertThat(n.grew()).isFalse();
        assertThat(n.after().careDays()).isEqualTo(1);
        assertThat(n.after().ageDays()).isEqualTo(2);
        assertThat(n.after().neglectDays()).isEqualTo(1);
        assertThat(n.after().bond()).isLessThan(a.after().bond());
    }

    @Test
    void bondedCareDaysCanSpurt() {
        Day s = KennelGrowth.day(Pup.newborn("pip", 30), FULL, 5);
        assertThat(s.spurt()).isTrue();
        assertThat(s.after().careDays()).isEqualTo(2);
        Day none = KennelGrowth.day(Pup.newborn("pip", 30), FULL, 50);
        assertThat(none.spurt()).isFalse();
        Day pc = KennelGrowth.day(new Pup("pip", 2, 2, 30, 0), BASIC, 0);
        assertThat(pc.stagedUp()).isTrue();
        assertThat(pc.stageAfter()).isEqualTo(Stage.PUP);
        assertThat(KennelGrowth.day(Pup.newborn("a", 30), FULL, 7L))
            .isEqualTo(KennelGrowth.day(Pup.newborn("a", 30), FULL, 7L));
    }

    @Test
    void stageGatesTraining() {
        Pup young = new Pup("pip", 4, 4, 90, 0);
        assertThat(KennelGrowth.canTrain(young, "come")).isTrue();
        assertThat(KennelGrowth.canTrain(young, "stay")).isFalse();
        assertThat(KennelGrowth.canTrain(new Pup("pip", 12, 12, 90, 0), "stay")).isTrue();
        assertThat(KennelGrowth.canTrain(new Pup("pip", 12, 12, 10, 0), "come")).isFalse();
        KennelTraining.Drill d = KennelGrowth.drill(young, KennelTraining.Trainee.fresh("pip", 90), "stay", 1L);
        assertThat(d.blockedReason()).isEqualTo("too young");
        assertThatThrownBy(() -> KennelGrowth.canTrain(young, "sit")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void growingUpQuest() {
        QuestResult ok = KennelGrowth.growingUp(Pup.newborn("pip", 10), Collections.nCopies(14, BASIC), 3L);
        assertThat(ok.complete()).isTrue();
        assertThat(ok.dayReached()).isEqualTo(10);
        assertThat(ok.trail()).contains(Stage.PUP).endsWith(Stage.JUVENILE);
        List<Care> sloppy = new ArrayList<>(Collections.nCopies(14, BASIC));
        sloppy.set(0, NEGLECT);
        sloppy.set(1, NEGLECT);
        sloppy.set(2, NEGLECT);
        QuestResult bad = KennelGrowth.growingUp(Pup.newborn("pip", 10), sloppy, 3L);
        assertThat(bad.complete()).isFalse();
        assertThat(bad.failReason()).isEqualTo("too many neglect days");
        List<Care> late = new ArrayList<>(Collections.nCopies(14, BASIC));
        for (int i = 0; i < 5; i++) {
            late.set(i * 2, NEGLECT);
        }
        assertThat(KennelGrowth.growingUp(Pup.newborn("pip", 10), late, 3L).complete()).isFalse();
    }

    @Test
    void spurtsShortenTheQuest() {
        int faster = 0;
        for (long s = 0; s < 100; s++) {
            QuestResult q = KennelGrowth.growingUp(Pup.newborn("pip", 10), Collections.nCopies(14, FULL), s);
            assertThat(q.complete()).isTrue();
            assertThat(q.dayReached()).isBetween(5, 10);
            if (q.dayReached() < 10) {
                faster++;
            }
        }
        assertThat(faster).isGreaterThan(50);
    }
}