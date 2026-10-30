// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.pilot.FogChannelPilot;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class FogChannelPilotAdapterTest {

    static final ActivityParticipant GULL =
            new ActivityParticipant("life:harbour-gull-2", ActivityParticipant.Kind.LIFE, "bird", "navigation");

    static ActivityResultAdapter.Session session(String id) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "harbour-host", "verify:" + id, List.of(GULL),
                List.of("evt:" + id), 1_761_800_000_000L);
    }

    @Test
    void bestReadingCompletesAndGreedyFails() {
        FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-1");
        FogChannelPilotAdapter a = new FogChannelPilotAdapter(ActivityMode.AUTHORITATIVE);
        ActivityResultReceipt best = a.toReceipt(session("fc-1"), FogChannelPilotAdapter.Reading.of(h, FogChannelPilot.best(h).lanes(), false));
        assertThat(best.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(best.measures()).containsEntry("cost", 13L).containsEntry("over_par", 0L).containsEntry("stars", 3L)
                .containsEntry("quest_done", 1L).containsEntry("blasts", 5L);
        ActivityResultReceipt greedy = a.toReceipt(session("fc-2"),
                FogChannelPilotAdapter.Reading.of(h, FogChannelPilot.loudestEcho(h).lanes(), false));
        assertThat(greedy.outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThat(greedy.measures()).containsEntry("over_par", 6L).containsEntry("stars", 1L);
        ActivityResultReceipt left = a.toReceipt(session("fc-3"), FogChannelPilotAdapter.Reading.of(h, FogChannelPilot.best(h).lanes(), true));
        assertThat(left.outcome()).isEqualTo(ActivityOutcome.ABANDONED);
    }

    @Test
    void everyTierFitsTheMeasureBounds() {
        FogChannelPilotAdapter a = new FogChannelPilotAdapter(ActivityMode.DEVICE_LOCAL);
        for (FogChannelPilot.Tier t : FogChannelPilot.Tier.values()) {
            for (int s = 1; s <= 50; s++) {
                FogChannelPilot.Harbour h = FogChannelPilot.harbour(t.seedPrefix() + s, t);
                assertThat(a.toReceipt(session("fb-" + s), FogChannelPilotAdapter.Reading.of(h, FogChannelPilot.loudestEcho(h).lanes(), false))
                        .measures().get("cost")).isLessThanOrEqualTo(FogChannelPilotAdapter.MAX_COST);
            }
        }
    }

    @Test
    void refusesFakeReadings() {
        FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-7");
        assertThatThrownBy(() -> FogChannelPilotAdapter.Reading.of(h, new int[] {9}, false)).hasMessageContaining("not a track");
        assertThatThrownBy(() -> new FogChannelPilotAdapter.Reading(3, 4, 5, 3, true, false)).hasMessageContaining("range");
        assertThatThrownBy(() -> new FogChannelPilotAdapter.Reading(3, 5, 5, 2, true, false)).hasMessageContaining("range");
        assertThatThrownBy(() -> new FogChannelPilotAdapter.Reading(17, 5, 5, 3, true, false)).hasMessageContaining("range");
    }

    @Test
    void plugsIntoARouterAndSettlesOnce() {
        ActivityRouter r = ActivityRouter.contest(ActivityMode.AUTHORITATIVE);
        r.register(new FogChannelPilotAdapter(ActivityMode.AUTHORITATIVE), FogChannelPilotAdapter.Reading.class,
                AwardPolicy.inactive(FogChannelPilotAdapter.ACTIVITY_ID, "mastery.navigation"));
        FogChannelPilot.Harbour h = FogChannelPilot.harbour("pea-soup-1", FogChannelPilot.Tier.PEA_SOUP);
        FogChannelPilotAdapter.Reading reading = FogChannelPilotAdapter.Reading.of(h, FogChannelPilot.best(h).lanes(), false);
        assertThat(r.receipt(FogChannelPilotAdapter.ACTIVITY_ID, session("fr-1"), reading).outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        r.settle(FogChannelPilotAdapter.ACTIVITY_ID, session("fr-1"), reading);
        assertThat(r.total(GULL.instanceId(), "mastery.navigation")).isZero();
        assertThatThrownBy(() -> r.settle(FogChannelPilotAdapter.ACTIVITY_ID, session("fr-2"), "not a reading"))
                .hasMessageContaining("expects");
    }
}
