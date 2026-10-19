// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ReceiptJournal;
import com.daedalus.world.audio.DopplerFlyby;
import com.daedalus.world.audio.HullKnockSurvey;
import com.daedalus.world.audio.ThunderTowers;
import com.daedalus.world.audio.WaveOrgan;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contest G127: receipts hub IX over prometheus's landed island-audio games, driven by the real cores. */
class HubNineAdaptersTest {

    static final ActivityParticipant OWL =
            new ActivityParticipant("life:storm-owl-1", ActivityParticipant.Kind.LIFE, "bird", "listening");
    static final ActivityParticipant HOUND =
            new ActivityParticipant("life:dock-hound-2", ActivityParticipant.Kind.LIFE, "animal", "guarding");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_872_000_000L);
    }

    @Test
    void thunderTowersOutcomeFollowsTheRealVerdict() {
        ThunderTowersAdapter a = new ThunderTowersAdapter(ActivityMode.AUTHORITATIVE);
        for (long seed = 1; seed <= 20; seed++) {
            ThunderTowers t = ThunderTowers.seeded(seed);
            ThunderTowers.Verdict v = t.judge(t.candidates().get(0));
            ThunderTowersAdapter.Storm st = ThunderTowersAdapter.Storm.of(v, false);
            assertThat(st.towers()).isEqualTo(v.errorTenths().size());
            assertThat(a.toReceipt(session("tt-" + seed, OWL), st).outcome())
                    .isEqualTo(v.correct() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
        }
        assertThat(a.toReceipt(session("tt-x", OWL), new ThunderTowersAdapter.Storm(false, 3, 4, true)).outcome())
                .isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new ThunderTowersAdapter.Storm(true, -1, 0, false)).hasMessageContaining("negative");
    }

    @Test
    void dopplerRightArkAndSpeedCompletesWrongSpeedFails() {
        DopplerFlybyAdapter a = new DopplerFlybyAdapter(ActivityMode.AUTHORITATIVE);
        DopplerFlyby d = DopplerFlyby.seeded(7);
        DopplerFlyby.Verdict truth = d.judge("x", 0);
        DopplerFlyby.Verdict good = d.judge(truth.ark(), truth.speed());
        assertThat(a.toReceipt(session("df-1", OWL), DopplerFlybyAdapter.Flyby.of(good, false)).outcome())
                .isEqualTo(ActivityOutcome.COMPLETED);
        DopplerFlyby.Verdict slow = d.judge(truth.ark(), truth.speed() + 5.0);
        var r = a.toReceipt(session("df-2", OWL), DopplerFlybyAdapter.Flyby.of(slow, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThat(r.measures()).containsEntry("right_ark", 1L).containsEntry("right_speed", 0L);
    }

    @Test
    void hullKnockPerfectCompletesMissedCrackFails() {
        HullKnockAdapter a = new HullKnockAdapter(ActivityMode.AUTHORITATIVE);
        HullKnockSurvey h = HullKnockSurvey.seeded(3);
        assertThat(a.toReceipt(session("hk-1", HOUND), HullKnockAdapter.Survey.of(h.judge(h.solution()), false))
                .outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        HullKnockAdapter.Survey bad = new HullKnockAdapter.Survey(1, 1, 2, false);
        assertThat(a.toReceipt(session("hk-2", HOUND), bad).measures())
                .containsEntry("misses", 1L).containsEntry("false_alarms", 2L);
        assertThat(a.toReceipt(session("hk-3", HOUND), bad).outcome()).isEqualTo(ActivityOutcome.FAILED);
    }

    @Test
    void waveOrganTriadCompletesAndCentsAreBounded() {
        WaveOrganAdapter a = new WaveOrganAdapter(ActivityMode.AUTHORITATIVE);
        WaveOrgan w = WaveOrgan.seeded(5);
        WaveOrgan.Verdict v = w.judge(w.solutions().get(0));
        assertThat(v.triad()).isTrue();
        assertThat(a.toReceipt(session("wo-1", OWL), WaveOrganAdapter.Tide.of(v, false)).outcome())
                .isEqualTo(ActivityOutcome.COMPLETED);
        WaveOrganAdapter.Tide odd = WaveOrganAdapter.Tide.of(new WaveOrgan.Verdict(false, "none", Double.NaN, "x"), false);
        assertThat(odd.worstCents()).isEqualTo(1200);
        assertThat(a.toReceipt(session("wo-2", OWL), odd).outcome()).isEqualTo(ActivityOutcome.FAILED);
    }

    @Test
    void contestAllRoutesHubNineSettlesOnceAndReplays() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(ThunderTowersAdapter.ACTIVITY_ID, DopplerFlybyAdapter.ACTIVITY_ID,
                HullKnockAdapter.ACTIVITY_ID, WaveOrganAdapter.ACTIVITY_ID);
        AwardPolicy policy = new AwardPolicy(HullKnockAdapter.ACTIVITY_ID, 1, "mastery.listening",
                Map.of("hits", 3L), 60);
        r.setPolicy(policy);
        HullKnockAdapter.Survey s = new HullKnockAdapter.Survey(4, 0, 0, false);
        r.settle(HullKnockAdapter.ACTIVITY_ID, session("route-hk", HOUND), s);
        r.settle(HullKnockAdapter.ACTIVITY_ID, session("route-hk", HOUND), s);
        long once = r.total("life:dock-hound-2", "mastery.listening");
        assertThat(once).isPositive();
        assertThat(ReceiptJournal.readAll(r.journal())).hasSize(1);
        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        restarted.setPolicy(policy);
        assertThat(restarted.replay(r.journal())).isEqualTo(1);
        assertThat(restarted.total("life:dock-hound-2", "mastery.listening")).isEqualTo(once);
        assertThatThrownBy(() -> r.settle(WaveOrganAdapter.ACTIVITY_ID, session("route-x", OWL), s))
                .hasMessageContaining("expects");
    }
}
