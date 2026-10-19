// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.bricks.AssemblyRepair;
import com.daedalus.world.eggs.EggHatchery;
import com.daedalus.world.parcels.MailRoute;
import com.daedalus.world.sports.ThrowableSports;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class HubTwoAdaptersTest {

    static final ActivityParticipant HEN =
            new ActivityParticipant("life:nest-hen-1", ActivityParticipant.Kind.LIFE, "bird", "nursery");
    static final ActivityParticipant PUP =
            new ActivityParticipant("life:inkpup-2", ActivityParticipant.Kind.LIFE, "animal", "fetching");
    static final ActivityParticipant PIGEON =
            new ActivityParticipant("life:carrier-pigeon-5", ActivityParticipant.Kind.LIFE, "bird", "carrying");
    static final ActivityParticipant MAGPIE =
            new ActivityParticipant("life:brick-magpie-1", ActivityParticipant.Kind.LIFE, "bird", "scouting");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_872_000_000L);
    }

    @Test
    void eggCareMapsHatchingAndPerfectCare() {
        EggHatchery.EggType type = new EggHatchery.EggType("Sky Speckle", "spots", "common", Map.of("drake", 1));
        EggHatchery.Hatchling chick = new EggHatchery.Hatchling("Sky Speckle", "drake", "spots", false, "common", 40, true);
        EggHatchery.EggState hatched = new EggHatchery.EggState(type, 7, EggHatchery.Stage.HATCHED, 100, 0, 40, 8, chick);
        EggCareAdapter a = new EggCareAdapter(ActivityMode.AUTHORITATIVE);
        ActivityResultReceipt r = a.toReceipt(session("egg-1", HEN), EggCareAdapter.Care.of(hatched, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("hatched", 1L).containsEntry("perfect_care", 1L).containsEntry("turns", 8L);
        EggHatchery.EggState waiting = new EggHatchery.EggState(type, 7, EggHatchery.Stage.CRACKED, 50, 2, 20, 3, null);
        assertThat(a.toReceipt(session("egg-2", HEN), EggCareAdapter.Care.of(waiting, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new EggCareAdapter.Care(1, 1, 0, false, true, false)).hasMessageContaining("hatching");
    }

    @Test
    void catchRallyUsesTheScoredRally() {
        ThrowableSports.CatchResult res = new ThrowableSports.CatchResult(7, 6, 4, List.of(true, true, true, true, false, true, true));
        ActivityResultReceipt r = new CatchRallyAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(session("catch-1", PUP), CatchRallyAdapter.Rally.of(res, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("throws", 7L).containsEntry("caught", 6L).containsEntry("best_streak", 4L);
        assertThatThrownBy(() -> new CatchRallyAdapter.Rally(2, 3, 0, 0, false)).hasMessageContaining("add up");
    }

    @Test
    void mailRouteReadsARealDay() {
        MailRoute.Day day = MailRoute.day(2026L);
        MailRoute.Receipt idle = new MailRoute.Session(day).finish(MailRoute.depot().at(), 10);
        MailRouteAdapter.Round round = MailRouteAdapter.Round.of(idle, false);
        assertThat(round.delivered()).isZero();
        assertThat(round.undelivered()).isPositive();
        ActivityResultReceipt r = new MailRouteAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("mail-1", PIGEON), round);
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.FAILED);
        MailRouteAdapter.Round perfect = new MailRouteAdapter.Round(8, 0, 0, true, 12, 3, false);
        assertThat(new MailRouteAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("mail-2", PIGEON), perfect)
                .measures()).containsEntry("medal", 3L).containsEntry("ghost_returned", 1L);
    }

    @Test
    void assemblyRepairReadsARealSession() {
        AssemblyRepair.Session s = new AssemblyRepair.Session(AssemblyRepair.scatter(41L));
        AssemblyRepair.Receipt unrestored = s.receipt(AssemblyRepair.Machine.PLANE);
        AssemblyRepairAdapter.Repair rep = AssemblyRepairAdapter.Repair.of(unrestored, false);
        assertThat(rep.restored()).isFalse();
        assertThat(new AssemblyRepairAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("brick-1", MAGPIE), rep)
                .outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new AssemblyRepairAdapter.Repair(false, 0, 0, 0, 0, true, false))
                .hasMessageContaining("sky gate");
    }

    @Test
    void contestAllRoutesHubTwoGamesAndSettlesOnce() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).hasSizeGreaterThanOrEqualTo(7).contains(EggCareAdapter.ACTIVITY_ID, CatchRallyAdapter.ACTIVITY_ID,
                MailRouteAdapter.ACTIVITY_ID, AssemblyRepairAdapter.ACTIVITY_ID);
        r.setPolicy(new AwardPolicy(CatchRallyAdapter.ACTIVITY_ID, 1, "mastery.play", Map.of("caught", 1L, "best_streak", 2L), 40));
        CatchRallyAdapter.Rally rally = new CatchRallyAdapter.Rally(10, 8, 5, 9, false);
        r.settle(CatchRallyAdapter.ACTIVITY_ID, session("route-catch", PUP), rally);
        r.settle(CatchRallyAdapter.ACTIVITY_ID, session("route-catch", PUP), rally);
        assertThat(r.total("life:inkpup-2", "mastery.play")).isEqualTo(18);
        assertThatThrownBy(() -> r.settle(MailRouteAdapter.ACTIVITY_ID, session("route-x", PIGEON), rally))
                .hasMessageContaining("expects Round");
    }
}
