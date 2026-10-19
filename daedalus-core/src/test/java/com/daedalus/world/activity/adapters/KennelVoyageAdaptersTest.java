// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.companion.KennelArkLandfall;
import com.daedalus.world.companion.KennelArkVoyage;
import com.daedalus.world.companion.KennelGrowth.Pup;

import java.util.List;

import org.junit.jupiter.api.Test;

class KennelVoyageAdaptersTest {
    static final List<Pup> CREW = KennelArkAdaptersTest.CREW;

    @Test
    void crossingReceiptMatchesTheChapter() {
        int arrived = 0;
        int lost = 0;
        for (long s = 0; s < 40; s++) {
            KennelArkVoyage.Voyage v = KennelArkVoyage.crossingTheStormBelt(CREW, s);
            KennelVoyageAdapters.CrossingAdapter.Crossing c = KennelVoyageAdapters.CrossingAdapter.Crossing.of(v, false);
            ActivityResultReceipt r = new KennelVoyageAdapters.CrossingAdapter(ActivityMode.AUTHORITATIVE)
                    .toReceipt(KennelArkAdaptersTest.session("cs" + s), c);
            assertThat(r.outcome()).isEqualTo(v.arrived() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            assertThat(r.measures()).containsEntry("legs", (long) v.legs().size()).containsEntry("hull", (long) v.hull())
                    .containsEntry("water", (long) v.water())
                    .containsEntry("answered", v.legs().stream().filter(KennelArkVoyage.Leg::answered).count());
            arrived += v.arrived() ? 1 : 0;
            lost += v.arrived() ? 0 : 1;
        }
        assertThat(arrived).isPositive();
        assertThat(lost).isPositive();
        assertThatThrownBy(() -> new KennelVoyageAdapters.CrossingAdapter.Crossing(true, 6, 3, 0, 4, false))
                .hasMessageContaining("add up");
        assertThatThrownBy(() -> new KennelVoyageAdapters.CrossingAdapter.Crossing(false, 3, 4, 2, 0, false))
                .hasMessageContaining("add up");
        assertThatThrownBy(() -> new KennelVoyageAdapters.CrossingAdapter.Crossing(false, 2, 1, 5, 5, false))
                .hasMessageContaining("add up");
    }

    @Test
    void shoreReceiptMatchesTheChapter() {
        int seaworthy = 0;
        int neverLanded = 0;
        for (long s = 0; s < 60; s++) {
            KennelArkLandfall.Chapter c = KennelArkLandfall.landfallOnTheCinderShelf(CREW, s);
            KennelVoyageAdapters.ShoreAdapter.Shore sh = KennelVoyageAdapters.ShoreAdapter.Shore.of(c, false);
            ActivityResultReceipt r = new KennelVoyageAdapters.ShoreAdapter(ActivityMode.AUTHORITATIVE)
                    .toReceipt(KennelArkAdaptersTest.session("sh" + s), sh);
            assertThat(r.outcome()).isEqualTo(c.complete() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            if (c.landfall() == null) {
                neverLanded++;
                assertThat(r.measures()).containsEntry("days", 0L).containsEntry("hull", (long) c.voyage().hull());
                continue;
            }
            KennelArkLandfall.Landfall l = c.landfall();
            assertThat(r.measures()).containsEntry("days", (long) l.days().size()).containsEntry("hull", (long) l.hull())
                    .containsEntry("water", (long) l.water()).containsEntry("rescued", (long) l.rescued().size())
                    .containsEntry("planks", (long) l.days().stream().mapToInt(KennelArkLandfall.Day::planks).sum());
            seaworthy += c.complete() ? 1 : 0;
        }
        assertThat(seaworthy).isPositive();
        assertThat(neverLanded).isPositive();
        ActivityResultReceipt a = new KennelVoyageAdapters.ShoreAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(KennelArkAdaptersTest.session("sha"), new KennelVoyageAdapters.ShoreAdapter.Shore(false, 2, 3, 6, 4, 1, true));
        assertThat(a.outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new KennelVoyageAdapters.ShoreAdapter.Shore(true, 2, 4, 9, 3, 0, false))
                .hasMessageContaining("add up");
        assertThatThrownBy(() -> new KennelVoyageAdapters.ShoreAdapter.Shore(false, 1, 2, 5, 5, 2, false))
                .hasMessageContaining("add up");
        assertThatThrownBy(() -> new KennelVoyageAdapters.ShoreAdapter.Shore(false, 6, 2, 5, 5, 0, false))
                .hasMessageContaining("add up");
    }

    @Test
    void registerAllRoutesThroughARouter() {
        ActivityRouter router = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        KennelVoyageAdapters.registerAll(router, ActivityMode.AUTHORITATIVE);
        assertThat(router.activities()).contains(KennelVoyageAdapters.CROSSING_ID, KennelVoyageAdapters.SHORE_ID);
        ActivityResultReceipt r = router.receipt(KennelVoyageAdapters.SHORE_ID, KennelArkAdaptersTest.session("rt"),
                new KennelVoyageAdapters.ShoreAdapter.Shore(true, 3, 6, 10, 2, 2, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        ActivityResultReceipt c = router.receipt(KennelVoyageAdapters.CROSSING_ID, KennelArkAdaptersTest.session("rt2"),
                new KennelVoyageAdapters.CrossingAdapter.Crossing(true, 6, 4, 7, 6, false));
        assertThat(c.measures()).containsEntry("answered", 4L);
    }
}
