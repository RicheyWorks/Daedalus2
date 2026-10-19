// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ReceiptJournal;
import com.daedalus.world.audio.DawnChorusCensus;
import com.daedalus.world.audio.FrogPondNiches;
import com.daedalus.world.audio.KeepersCall;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contest G137: receipts hub X over prometheus's newest landed island-audio games, driven by the real cores. */
class HubTenAdaptersTest {

    static final ActivityParticipant WREN =
            new ActivityParticipant("life:harbour-wren-1", ActivityParticipant.Kind.LIFE, "bird", "singing");
    static final ActivityParticipant HOUND =
            new ActivityParticipant("life:marsh-hound-2", ActivityParticipant.Kind.LIFE, "animal", "listening");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_875_000_000L);
    }

    @Test
    void keepersCallFullEchoCompletesEarlyMissFailsInPlayRefused() {
        KeepersCallAdapter a = new KeepersCallAdapter(ActivityMode.AUTHORITATIVE);
        KeepersCall k = KeepersCall.seeded(11);
        KeepersCall.Run perfect = k.start();
        while (!perfect.over()) {
            assertThat(perfect.echo(perfect.call())).isTrue();
        }
        var done = a.toReceipt(session("kc-1", WREN), KeepersCallAdapter.Echo.of(perfect, false));
        assertThat(done.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(done.measures()).containsEntry("score", (long) KeepersCall.MAX_LENGTH).containsEntry("stars", 3L);

        KeepersCall.Run miss = k.start();
        KeepersCall.Stroke first = miss.call().get(0);
        assertThat(miss.echo(List.of(new KeepersCall.Stroke((first.bell() + 1) % KeepersCall.BELLS, first.isLong()))))
                .isFalse();
        assertThat(a.toReceipt(session("kc-2", WREN), KeepersCallAdapter.Echo.of(miss, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);

        KeepersCall.Run live = k.start();
        live.echo(live.call());
        assertThatThrownBy(() -> KeepersCallAdapter.Echo.of(live, false)).hasMessageContaining("in play");
        assertThat(a.toReceipt(session("kc-3", WREN), KeepersCallAdapter.Echo.of(live, true)).outcome())
                .isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new KeepersCallAdapter.Echo(9, 3, false)).hasMessageContaining("stars");
    }

    @Test
    void dawnChorusOutcomeFollowsTheRealVerdict() {
        DawnChorusAdapter a = new DawnChorusAdapter(ActivityMode.AUTHORITATIVE);
        for (long seed = 1; seed <= 20; seed++) {
            DawnChorusCensus d = DawnChorusCensus.seeded(seed);
            List<String> sol = d.solution();
            DawnChorusCensus.Verdict good = d.judge(sol.get(0), sol.get(1));
            assertThat(good.correct()).isTrue();
            assertThat(a.toReceipt(session("dc-" + seed, HOUND), DawnChorusAdapter.Census.of(good, false)).outcome())
                    .isEqualTo(ActivityOutcome.COMPLETED);
            DawnChorusCensus.Verdict half = d.judge(sol.get(0), "albatross");
            var r = a.toReceipt(session("dc-h" + seed, HOUND), DawnChorusAdapter.Census.of(half, false));
            assertThat(r.outcome()).isEqualTo(ActivityOutcome.FAILED);
            assertThat(r.measures()).containsEntry("right_loudest", 1L).containsEntry("right_missing", 0L);
        }
        DawnChorusCensus.Verdict v = DawnChorusCensus.seeded(3).judge("x", "y");
        assertThat(a.toReceipt(session("dc-x", HOUND), DawnChorusAdapter.Census.of(v, true)).outcome())
                .isEqualTo(ActivityOutcome.ABANDONED);
    }

    @Test
    void frogPondClearAssignmentCompletesMaskingPondFails() {
        FrogPondAdapter a = new FrogPondAdapter(ActivityMode.AUTHORITATIVE);
        int failures = 0;
        for (long seed = 1; seed <= 30; seed++) {
            FrogPondNiches w = FrogPondNiches.seeded(seed);
            FrogPondNiches.Verdict ok = w.judge(w.solution());
            var r = a.toReceipt(session("fp-" + seed, HOUND), FrogPondAdapter.Wetland.of(w, ok, false));
            assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
            assertThat(r.measures().get("species")).isBetween(5L, 7L);
            List<Integer> onePond = new ArrayList<>();
            w.frogs().forEach(f -> onePond.add(0));
            FrogPondNiches.Verdict crowded = w.judge(onePond);
            var c = a.toReceipt(session("fp-c" + seed, HOUND), FrogPondAdapter.Wetland.of(w, crowded, false));
            assertThat(c.outcome()).isEqualTo(crowded.ok() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            if (!crowded.ok()) {
                failures++;
                assertThat(c.measures()).containsEntry("clear", 0L);
            }
        }
        assertThat(failures).isPositive();
        assertThatThrownBy(() -> new FrogPondAdapter.Wetland(true, 11, false)).hasMessageContaining("species");
    }

    @Test
    void contestAllRoutesHubTenSettlesOnceAndReplays() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(KeepersCallAdapter.ACTIVITY_ID, DawnChorusAdapter.ACTIVITY_ID,
                FrogPondAdapter.ACTIVITY_ID);
        AwardPolicy policy = new AwardPolicy(KeepersCallAdapter.ACTIVITY_ID, 1, "mastery.listening",
                Map.of("score", 6L), 60);
        r.setPolicy(policy);
        KeepersCallAdapter.Echo e = new KeepersCallAdapter.Echo(12, 3, false);
        r.settle(KeepersCallAdapter.ACTIVITY_ID, session("route-kc", WREN), e);
        r.settle(KeepersCallAdapter.ACTIVITY_ID, session("route-kc", WREN), e);
        long once = r.total("life:harbour-wren-1", "mastery.listening");
        assertThat(once).isPositive();
        assertThat(ReceiptJournal.readAll(r.journal())).hasSize(1);
        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        restarted.setPolicy(policy);
        assertThat(restarted.replay(r.journal())).isEqualTo(1);
        assertThat(restarted.total("life:harbour-wren-1", "mastery.listening")).isEqualTo(once);
        assertThatThrownBy(() -> r.settle(FrogPondAdapter.ACTIVITY_ID, session("route-x", HOUND), e))
                .hasMessageContaining("expects");
    }
}