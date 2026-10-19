// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.companion.KennelArkPens;

import java.util.List;

import org.junit.jupiter.api.Test;

class KennelPensAdapterTest {
    @Test
    void receiptMatchesTheChapterOverManySeeds() {
        int done = 0;
        int failed = 0;
        for (long s = 0; s < 80; s++) {
            KennelArkPens.WarmCrates w = KennelArkPens.theWarmCrates(KennelArkAdaptersTest.CREW, s);
            ActivityResultReceipt r = new KennelPensAdapter(ActivityMode.AUTHORITATIVE)
                    .toReceipt(KennelArkAdaptersTest.session("wc" + s), KennelPensAdapter.Pens.of(w, false));
            assertThat(r.outcome()).isEqualTo(w.complete() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            if (w.plan() == null) {
                assertThat(r.measures()).containsEntry("animals", 0L).containsEntry("planks_used", 0L);
            } else {
                KennelArkPens.Plan p = w.plan();
                assertThat(r.measures()).containsEntry("penned", (long) p.penned().size())
                        .containsEntry("animals", (long) (p.penned().size() + p.unpenned().size()))
                        .containsEntry("pens", (long) p.built().size())
                        .containsEntry("planks_used", (long) p.planksUsed())
                        .containsEntry("planks_left", (long) p.planksLeft());
            }
            done += w.complete() ? 1 : 0;
            failed += w.complete() ? 0 : 1;
        }
        assertThat(done).isPositive();
        assertThat(failed).isPositive();
    }

    @Test
    void sharedWarmCrateCountsOnePenAndFactsMustAddUp() {
        KennelArkPens.Plan p = KennelArkPens.plan(List.of("ember fox", "ark cat"), 1);
        KennelArkPens.WarmCrates w = new KennelArkPens.WarmCrates(null, p, true, null);
        ActivityResultReceipt r = new KennelPensAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(KennelArkAdaptersTest.session("crate"), KennelPensAdapter.Pens.of(w, false));
        assertThat(r.measures()).containsEntry("penned", 2L).containsEntry("pens", 1L).containsEntry("planks_used", 1L);
        ActivityResultReceipt a = new KennelPensAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(KennelArkAdaptersTest.session("ab"), new KennelPensAdapter.Pens(false, 3, 1, 1, 2, 0, true));
        assertThat(a.outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new KennelPensAdapter.Pens(true, 3, 2, 2, 3, 0, false)).hasMessageContaining("add up");
        assertThatThrownBy(() -> new KennelPensAdapter.Pens(false, 2, 2, 0, 0, 1, false)).hasMessageContaining("add up");
        assertThatThrownBy(() -> new KennelPensAdapter.Pens(false, 7, 0, 0, 0, 0, false)).hasMessageContaining("add up");
        assertThatThrownBy(() -> new KennelPensAdapter.Pens(true, 0, 0, 0, 0, 4, false)).hasMessageContaining("add up");
    }

    @Test
    void registerRoutesThroughARouter() {
        ActivityRouter router = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        KennelPensAdapter.register(router, ActivityMode.AUTHORITATIVE);
        assertThat(router.activities()).contains(KennelPensAdapter.ID);
        ActivityResultReceipt r = router.receipt(KennelPensAdapter.ID, KennelArkAdaptersTest.session("rt"),
                new KennelPensAdapter.Pens(true, 2, 2, 2, 4, 3, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("planks_left", 3L);
    }
}
