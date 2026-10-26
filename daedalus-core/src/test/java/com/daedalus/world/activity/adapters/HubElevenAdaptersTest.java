// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ReceiptJournal;
import com.daedalus.world.audio.BroodCycles;
import com.daedalus.world.audio.DrumRollId;
import com.daedalus.world.odds.collect.ChartCollectorQuest;
import com.daedalus.world.odds.stopping.CaptainChoiceQuest;
import com.daedalus.world.odds.walk.LifeboatQuest;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contest G146: receipts hub XI over oddsreaper's and prometheus's newest landed games, driven by the real cores. */
class HubElevenAdaptersTest {

    static final ActivityParticipant GULL =
            new ActivityParticipant("life:dock-gull-1", ActivityParticipant.Kind.LIFE, "bird", "scouting");
    static final ActivityParticipant PUP =
            new ActivityParticipant("life:ark-pup-2", ActivityParticipant.Kind.LIFE, "animal", "companionship");
    static final ActivityParticipant OWL =
            new ActivityParticipant("life:snag-owl-3", ActivityParticipant.Kind.LIFE, "bird", "listening");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_878_000_000L);
    }

    @Test
    void captainBestHireCompletesOtherHireFailsInterviewsRefused() {
        CaptainChoiceAdapter a = new CaptainChoiceAdapter(ActivityMode.AUTHORITATIVE);
        int completed = 0;
        int failed = 0;
        for (long seed = 1; seed <= 40; seed++) {
            CaptainChoiceQuest q = new CaptainChoiceQuest(seed);
            q.interview();
            q.hire();
            var r = a.toReceipt(session("cc-" + seed, GULL), CaptainChoiceAdapter.Hiring.of(q, false));
            boolean best = q.stage() == CaptainChoiceQuest.Stage.BEST_HIRED;
            assertThat(r.outcome()).isEqualTo(best ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            assertThat(r.measures()).containsEntry("rank", (long) q.hiredRank()).containsEntry("seen", 1L);
            if (best) {
                completed++;
            } else {
                failed++;
            }
        }
        assertThat(completed).isPositive();
        assertThat(failed).isPositive();
        CaptainChoiceQuest live = new CaptainChoiceQuest(9);
        live.interview();
        assertThatThrownBy(() -> CaptainChoiceAdapter.Hiring.of(live, false)).hasMessageContaining("INTERVIEWING");
        var gone = a.toReceipt(session("cc-x", GULL), CaptainChoiceAdapter.Hiring.of(live, true));
        assertThat(gone.outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThat(gone.measures()).containsEntry("rank", 0L);
        assertThatThrownBy(() -> new CaptainChoiceAdapter.Hiring(true, 2, 3, false)).hasMessageContaining("rank 1");
    }

    @Test
    void starChartFullHaulCompletesShortHaulFailsPlanningRefused() {
        StarChartAdapter a = new StarChartAdapter(ActivityMode.AUTHORITATIVE);
        ChartCollectorQuest big = new ChartCollectorQuest();
        assertThat(big.haul(ChartCollectorQuest.MAX_CRATES, 5)).isEqualTo(ChartCollectorQuest.Stage.CHARTED);
        assertThat(a.toReceipt(session("sc-1", GULL), StarChartAdapter.Haul.of(big, false)).outcome())
                .isEqualTo(ActivityOutcome.COMPLETED);
        ChartCollectorQuest small = new ChartCollectorQuest();
        assertThat(small.haul(1, 5)).isEqualTo(ChartCollectorQuest.Stage.TORN);
        var torn = a.toReceipt(session("sc-2", GULL), StarChartAdapter.Haul.of(small, false));
        assertThat(torn.outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThat(torn.measures()).containsEntry("charted", 0L).containsEntry("traded", 0L);
        ChartCollectorQuest planning = new ChartCollectorQuest();
        assertThatThrownBy(() -> StarChartAdapter.Haul.of(planning, false)).hasMessageContaining("PLANNING");
        assertThat(a.toReceipt(session("sc-3", GULL), StarChartAdapter.Haul.of(planning, true)).outcome())
                .isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new StarChartAdapter.Haul(false, 2, false)).hasMessageContaining("charted");
    }

    @Test
    void lifeboatOutcomeFollowsTheVoyageAndAdriftIsRefused() {
        LifeboatDriftAdapter a = new LifeboatDriftAdapter(ActivityMode.AUTHORITATIVE);
        int home = 0;
        int reef = 0;
        for (long seed = 1; seed <= 40; seed++) {
            LifeboatQuest q = new LifeboatQuest();
            LifeboatQuest.Stage end = q.followKeeper(seed);
            var r = a.toReceipt(session("lb-" + seed, PUP), LifeboatDriftAdapter.Voyage.of(q, false));
            assertThat(r.outcome()).isEqualTo(end == LifeboatQuest.Stage.HARBOUR
                    ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            assertThat(r.measures()).containsEntry("watches", (long) q.watches());
            if (end == LifeboatQuest.Stage.HARBOUR) {
                home++;
            } else {
                reef++;
            }
        }
        assertThat(home).isPositive();
        assertThat(reef).isPositive();
        LifeboatQuest adrift = new LifeboatQuest();
        assertThatThrownBy(() -> LifeboatDriftAdapter.Voyage.of(adrift, false)).hasMessageContaining("ADRIFT");
        assertThat(a.toReceipt(session("lb-x", PUP), LifeboatDriftAdapter.Voyage.of(adrift, true)).outcome())
                .isEqualTo(ActivityOutcome.ABANDONED);
    }

    @Test
    void broodBestCycleCompletesWorseCycleFails() {
        BroodCyclesAdapter a = new BroodCyclesAdapter(ActivityMode.AUTHORITATIVE);
        for (long seed = 1; seed <= 20; seed++) {
            BroodCycles b = BroodCycles.seeded(seed);
            BroodCycles.Verdict good = b.judge(b.bestCycles().get(0));
            assertThat(a.toReceipt(session("bc-" + seed, OWL), BroodCyclesAdapter.Brood.of(good, false)).outcome())
                    .isEqualTo(ActivityOutcome.COMPLETED);
            for (int c = BroodCycles.MIN_CYCLE; c <= BroodCycles.MAX_CYCLE; c++) {
                BroodCycles.Verdict v = b.judge(c);
                var r = a.toReceipt(session("bc-" + seed + "-" + c, OWL), BroodCyclesAdapter.Brood.of(v, false));
                assertThat(r.outcome()).isEqualTo(v.best() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
                assertThat(r.measures()).containsEntry("meetings", (long) v.meetings());
            }
        }
        assertThatThrownBy(() -> new BroodCyclesAdapter.Brood(true, 9, 4, false)).hasMessageContaining("best");
    }

    @Test
    void drumRollRightWoodpeckerCompletesWrongOneFails() {
        DrumRollAdapter a = new DrumRollAdapter(ActivityMode.AUTHORITATIVE);
        for (long seed = 1; seed <= 20; seed++) {
            DrumRollId d = DrumRollId.seeded(seed);
            var good = a.toReceipt(session("dr-" + seed, OWL), DrumRollAdapter.Roll.of(d, d.answer(), false));
            assertThat(good.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
            assertThat(good.measures()).containsEntry("beats", (long) d.onsets().size());
            String wrong = DrumRollId.CARD.stream().map(DrumRollId.Drummer::name)
                    .filter(n -> !n.equals(d.answer())).findFirst().orElseThrow();
            assertThat(a.toReceipt(session("dr-w" + seed, OWL), DrumRollAdapter.Roll.of(d, wrong, false)).outcome())
                    .isEqualTo(ActivityOutcome.FAILED);
        }
    }

    @Test
    void contestAllRoutesHubElevenSettlesOnceAndReplays() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(CaptainChoiceAdapter.ACTIVITY_ID, StarChartAdapter.ACTIVITY_ID,
                LifeboatDriftAdapter.ACTIVITY_ID, BroodCyclesAdapter.ACTIVITY_ID, DrumRollAdapter.ACTIVITY_ID);
        AwardPolicy policy = new AwardPolicy(StarChartAdapter.ACTIVITY_ID, 1, "mastery.reckoning",
                Map.of("charted", 1L), 60);
        r.setPolicy(policy);
        StarChartAdapter.Haul h = new StarChartAdapter.Haul(true, 1, false);
        r.settle(StarChartAdapter.ACTIVITY_ID, session("route-sc", GULL), h);
        r.settle(StarChartAdapter.ACTIVITY_ID, session("route-sc", GULL), h);
        long once = r.total("life:dock-gull-1", "mastery.reckoning");
        assertThat(once).isPositive();
        assertThat(ReceiptJournal.readAll(r.journal())).hasSize(1);
        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        restarted.setPolicy(policy);
        assertThat(restarted.replay(r.journal())).isEqualTo(1);
        assertThat(restarted.total("life:dock-gull-1", "mastery.reckoning")).isEqualTo(once);
        assertThatThrownBy(() -> r.settle(DrumRollAdapter.ACTIVITY_ID, session("route-x", OWL), h))
                .hasMessageContaining("expects");
    }
}