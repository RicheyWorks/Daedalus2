// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.companion.KennelBond;
import com.daedalus.world.companion.KennelGrowth;
import com.daedalus.world.companion.KennelTraining;

import java.util.Collections;
import java.util.List;

import org.junit.jupiter.api.Test;

class KennelCareAdaptersTest {
    static final ActivityParticipant PIP =
            new ActivityParticipant("life:kennel-pip", ActivityParticipant.Kind.LIFE, "animal", "companion");
    static final KennelBond.Care FULL = new KennelBond.Care(true, true, true, 5);
    static final KennelBond.Care BASIC = new KennelBond.Care(true, true, false, 0);

    static ActivityResultAdapter.Session session(String id) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(PIP), List.of("evt:" + id), 1_760_872_000_000L);
    }

    @Test
    void keepersMarkReceipt() {
        KennelBond.QuestResult q = KennelBond.keepersMark(Collections.nCopies(7, FULL), KennelBond.Rules.defaults());
        assertThat(q.complete()).isTrue();
        KennelCareAdapters.BondAdapter.Mark m = KennelCareAdapters.BondAdapter.Mark.of(q, false);
        ActivityResultReceipt r = new KennelCareAdapters.BondAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(session("km"), m);
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("days", (long) q.dayReached());
        KennelBond.QuestResult fail = KennelBond.keepersMark(Collections.nCopies(7, BASIC), KennelBond.Rules.defaults());
        assertThat(new KennelCareAdapters.BondAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(session("km2"), KennelCareAdapters.BondAdapter.Mark.of(fail, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new KennelCareAdapters.BondAdapter.Mark(true, 1, 101, false))
                .hasMessageContaining("add up");
    }

    @Test
    void firstWordsReceipt() {
        KennelTraining.QuestResult q = KennelTraining.firstWords(KennelTraining.Trainee.fresh("pip", 20), 1);
        KennelCareAdapters.TrainingAdapter.Words w = KennelCareAdapters.TrainingAdapter.Words.of(q, true);
        ActivityResultReceipt r = new KennelCareAdapters.TrainingAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(session("fw"), w);
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThat(r.measures()).containsEntry("learned", 0L).containsEntry("final_bond", 20L);
        assertThatThrownBy(() -> new KennelCareAdapters.TrainingAdapter.Words(true, 9, 0, 0, false))
                .hasMessageContaining("add up");
    }

    @Test
    void growingUpReceipt() {
        KennelGrowth.QuestResult q = KennelGrowth.growingUp(KennelGrowth.Pup.newborn("pip", 10),
                Collections.nCopies(14, BASIC), 3L);
        KennelCareAdapters.GrowthAdapter.Growth g = KennelCareAdapters.GrowthAdapter.Growth.of(q, false);
        assertThat(g.stage()).isEqualTo(KennelGrowth.Stage.JUVENILE.ordinal());
        ActivityResultReceipt r = new KennelCareAdapters.GrowthAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(session("gu"), g);
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("days", 10L);
    }

    @Test
    void registerAllRoutesThroughARouter() {
        ActivityRouter router = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        KennelCareAdapters.registerAll(router, ActivityMode.AUTHORITATIVE);
        assertThat(router.activities()).contains(KennelCareAdapters.BOND_ID, KennelCareAdapters.TRAINING_ID,
                KennelCareAdapters.GROWTH_ID);
        ActivityResultReceipt r = router.receipt(KennelCareAdapters.GROWTH_ID, session("rt"),
                new KennelCareAdapters.GrowthAdapter.Growth(false, 14, 1, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.FAILED);
    }
}