// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.audio.DripCaveChorus;
import com.daedalus.world.audio.FogBellCallSigns;
import com.daedalus.world.audio.WindChimeTuning;
import com.daedalus.world.odds.tournament.SquallCupQuest;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class HubFiveAdaptersTest {

    static final ActivityParticipant GULL =
            new ActivityParticipant("life:fog-gull-4", ActivityParticipant.Kind.LIFE, "bird", "observation");
    static final ActivityParticipant OTTER =
            new ActivityParticipant("life:cup-otter-1", ActivityParticipant.Kind.LIFE, "animal", "fishing");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_872_000_000L);
    }

    @Test
    void fogBellReadsARealCall() {
        FogBellCallSigns f = FogBellCallSigns.seeded(74L);
        FogBellAdapter a = new FogBellAdapter(ActivityMode.AUTHORITATIVE);
        FogBellAdapter.Call right = FogBellAdapter.Call.of(f.judge(f.decode(f.heard())), false);
        assertThat(a.toReceipt(session("fb-1", GULL), right).outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        FogBellAdapter.Call wrong = FogBellAdapter.Call.of(f.judge("Nobody"), false);
        assertThat(a.toReceipt(session("fb-2", GULL), wrong).outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new FogBellAdapter.Call(true, -1, false)).hasMessageContaining("blurred");
    }

    @Test
    void windChimeReadsTheSolvedTubes() {
        WindChimeTuning w = WindChimeTuning.seeded(74L);
        WindChimeAdapter.Tuning t = WindChimeAdapter.Tuning.of(w.judge(w.solution()), false);
        assertThat(t.tuned()).isTrue();
        assertThat(t.tubesOk()).isEqualTo(WindChimeTuning.TUBES);
        assertThat(new WindChimeAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("wc-1", GULL), t).measures())
                .containsEntry("tuned", 1L).containsEntry("tubes_ok", (long) WindChimeTuning.TUBES);
        assertThatThrownBy(() -> new WindChimeAdapter.Tuning(true, 9, 0, 0, false)).hasMessageContaining("range");
    }

    @Test
    void dripCaveReadsTheSharedBeat() {
        DripCaveChorus c = DripCaveChorus.seeded(74L);
        DripCaveAdapter.Chorus hit = DripCaveAdapter.Chorus.of(c.judge(c.answer() * DripCaveChorus.BEAT_MS), false);
        assertThat(hit.correct()).isTrue();
        assertThat(new DripCaveAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("dc-1", GULL), hit).outcome())
                .isEqualTo(ActivityOutcome.COMPLETED);
    }

    @Test
    void squallCupRefusesACupInProgress() {
        assertThat(SquallCupAdapter.Cup.from(SquallCupQuest.Stage.CHAMPION, 3, false).champion()).isTrue();
        SquallCupAdapter.Cup out = SquallCupAdapter.Cup.from(SquallCupQuest.Stage.KNOCKED_OUT, 1, false);
        assertThat(new SquallCupAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("sc-1", OTTER), out).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> SquallCupAdapter.Cup.from(SquallCupQuest.Stage.ODDS_POSTED, 0, false))
                .hasMessageContaining("in progress");
    }

    @Test
    void contestAllRoutesHubFiveAndSettlesOnce() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(FogBellAdapter.ACTIVITY_ID, WindChimeAdapter.ACTIVITY_ID,
                DripCaveAdapter.ACTIVITY_ID, SquallCupAdapter.ACTIVITY_ID);
        r.setPolicy(new AwardPolicy(SquallCupAdapter.ACTIVITY_ID, 1, "mastery.fishing", Map.of("rounds_won", 5L), 30));
        SquallCupAdapter.Cup cup = new SquallCupAdapter.Cup(true, 4, false);
        r.settle(SquallCupAdapter.ACTIVITY_ID, session("route-sc", OTTER), cup);
        r.settle(SquallCupAdapter.ACTIVITY_ID, session("route-sc", OTTER), cup);
        assertThat(r.total("life:cup-otter-1", "mastery.fishing")).isEqualTo(20);
        assertThat(r.journal()).hasSize(1);
    }
}
