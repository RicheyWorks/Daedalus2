// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.companion.KennelArkLogs;
import com.daedalus.world.companion.KennelArkMuster;
import com.daedalus.world.companion.KennelGrowth.Pup;
import com.daedalus.world.companion.KennelRescue;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;

class KennelArkAdaptersTest {
    static final ActivityParticipant TANK_P =
            new ActivityParticipant("life:kennel-tank", ActivityParticipant.Kind.LIFE, "animal", "companion");
    static final Pup JUVENILE = new Pup("pip", 12, 12, 60, 0);
    static final List<Pup> CREW = List.of(new Pup("greymuzzle", 90, 70, 95, 0), new Pup("tank", 30, 25, 85, 0),
            JUVENILE, new Pup("wick", 14, 13, 55, 0));

    static ActivityResultAdapter.Session session(String id) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(TANK_P), List.of("evt:" + id), 1_760_872_000_000L);
    }

    @Test
    void lastArkBellReceiptMatchesTheChapter() {
        KennelRescue.Rescuer tank = new KennelRescue.Rescuer("tank", 85, Optional.empty());
        KennelRescue.Rescuer luna = new KennelRescue.Rescuer("luna", 90, Optional.empty());
        for (List<KennelRescue.Rescuer> team : List.of(List.of(tank), List.of(tank, luna))) {
            KennelArkAdapters.RescueAdapter.Rescue r = KennelArkAdapters.RescueAdapter.Rescue.of(KennelRescue.KEPLER, team, 0, false);
            KennelRescue.Plan p = KennelRescue.plan(KennelRescue.KEPLER, team, 0);
            assertThat(r.complete()).isEqualTo(KennelRescue.lastArkBell(team, 0));
            ActivityResultReceipt rc = new KennelArkAdapters.RescueAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("rb"), r);
            assertThat(rc.outcome()).isEqualTo(r.complete() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            assertThat(rc.measures()).containsEntry("saved", (long) p.saved()).containsEntry("lost", (long) p.lost())
                    .containsEntry("trips", (long) p.trips());
        }
        assertThatThrownBy(() -> new KennelArkAdapters.RescueAdapter.Rescue(true, 0, 3, 1, false)).hasMessageContaining("add up");
        assertThatThrownBy(() -> new KennelArkAdapters.RescueAdapter.Rescue(false, 1, -1, 1, false)).hasMessageContaining("add up");
    }

    @Test
    void lastKennelLogReceipt() {
        List<KennelArkLogs.Fragment> f = KennelArkLogs.scatter(7L);
        KennelArkLogs.Hunt h = KennelArkLogs.hunt(JUVENILE, f, KennelArkLogs.plan(JUVENILE, f));
        KennelArkAdapters.ArkLogsAdapter.Log log = KennelArkAdapters.ArkLogsAdapter.Log.of(h, false);
        assertThat(log.pages()).isEqualTo(h.pages().size());
        ActivityResultReceipt r = new KennelArkAdapters.ArkLogsAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("lk"), log);
        assertThat(r.outcome()).isEqualTo(h.complete() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
        assertThat(r.measures()).containsEntry("days", (long) h.daysUsed()).containsEntry("pages", (long) h.pages().size());
        KennelArkLogs.Hunt young = KennelArkLogs.hunt(new Pup("p", 4, 4, 90, 0), f, List.of());
        ActivityResultReceipt a = new KennelArkAdapters.ArkLogsAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(session("lk2"), KennelArkAdapters.ArkLogsAdapter.Log.of(young, true));
        assertThat(a.outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new KennelArkAdapters.ArkLogsAdapter.Log(true, 3, 5, false)).hasMessageContaining("add up");
    }

    @Test
    void musterReceipt() {
        int completed = 0;
        for (long s = 0; s < 20; s++) {
            KennelArkMuster.QuestResult q = KennelArkMuster.musterAtHullBay(CREW, s);
            KennelArkAdapters.MusterAdapter.Muster m = KennelArkAdapters.MusterAdapter.Muster.of(q, false);
            ActivityResultReceipt r = new KennelArkAdapters.MusterAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("mh" + s), m);
            assertThat(r.outcome()).isEqualTo(q.complete() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            assertThat(r.measures()).containsEntry("posts", 4L).containsEntry("dawns", (long) q.triesUsed())
                    .containsEntry("crew_odds", (long) q.roster().totalPct())
                    .containsEntry("last_holds", (long) q.holdsPerTry().get(q.holdsPerTry().size() - 1));
            completed += q.complete() ? 1 : 0;
        }
        assertThat(completed).isPositive();
        KennelArkMuster.QuestResult shortCrew = KennelArkMuster.musterAtHullBay(List.of(JUVENILE), 1L);
        KennelArkAdapters.MusterAdapter.Muster m = KennelArkAdapters.MusterAdapter.Muster.of(shortCrew, false);
        assertThat(m.dawns()).isZero();
        assertThat(m.lastHolds()).isZero();
        assertThat(new KennelArkAdapters.MusterAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("mx"), m).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new KennelArkAdapters.MusterAdapter.Muster(true, 1, 4, 200, 2, false)).hasMessageContaining("add up");
        assertThatThrownBy(() -> new KennelArkAdapters.MusterAdapter.Muster(false, 1, 2, 250, 1, false)).hasMessageContaining("add up");
    }

    @Test
    void registerAllRoutesThroughARouter() {
        ActivityRouter router = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        KennelArkAdapters.registerAll(router, ActivityMode.AUTHORITATIVE);
        assertThat(router.activities()).contains(KennelArkAdapters.RESCUE_ID, KennelArkAdapters.ARK_LOGS_ID,
                KennelArkAdapters.MUSTER_ID);
        ActivityResultReceipt r = router.receipt(KennelArkAdapters.MUSTER_ID, session("rt"),
                new KennelArkAdapters.MusterAdapter.Muster(true, 2, 4, 201, 3, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
    }
}
