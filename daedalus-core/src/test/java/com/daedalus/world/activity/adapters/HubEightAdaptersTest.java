// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ReceiptJournal;
import com.daedalus.world.brew.cellar.RootCellar;
import com.daedalus.world.brew.hunt.FragmentMap;
import com.daedalus.world.brew.hunt.RecordHunt;
import com.daedalus.world.brew.week.FirstWeek;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contest G115: receipts hub VIII over youtube-master's landed island story chapters (G46-G94). */
class HubEightAdaptersTest {

    static final ActivityParticipant GOAT =
            new ActivityParticipant("life:kettle-goat-1", ActivityParticipant.Kind.LIFE, "animal", "foraging");
    static final ActivityParticipant WREN =
            new ActivityParticipant("life:hum-wren-2", ActivityParticipant.Kind.LIFE, "bird", "listening");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_872_000_000L);
    }

    @Test
    void recordHuntInPlayIsRefusedAbandonedKeepsFactsCompleteCredits() {
        RecordHuntAdapter a = new RecordHuntAdapter(ActivityMode.AUTHORITATIVE);
        RecordHunt h = new RecordHunt(FragmentMap.seeded(7, 16), List.of("rec_a", "rec_b", "rec_c", "rec_d"), 7, 10);
        assertThatThrownBy(() -> RecordHuntAdapter.Hunt.of(h, false)).hasMessageContaining("in progress");
        var gone = a.toReceipt(session("rh-0", GOAT), RecordHuntAdapter.Hunt.of(h, true));
        assertThat(gone.outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThat(gone.measures()).containsEntry("found", 0L).containsEntry("remaining", 4L);
        assertThat(a.toReceipt(session("rh-1", GOAT), new RecordHuntAdapter.Hunt(true, 3, 1, 2, false)).outcome())
                .isEqualTo(ActivityOutcome.COMPLETED);
        assertThatThrownBy(() -> new RecordHuntAdapter.Hunt(true, 2, 2, 1, false)).hasMessageContaining("records");
    }

    @Test
    void choirStonesHeldCompletesCutOffFails() {
        ChoirStonesAdapter a = new ChoirStonesAdapter(ActivityMode.AUTHORITATIVE);
        assertThat(a.toReceipt(session("cs-1", WREN), new ChoirStonesAdapter.Watch(true, false, 4, 3, false))
                .outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        var cut = a.toReceipt(session("cs-2", WREN), new ChoirStonesAdapter.Watch(false, true, 2, 1, false));
        assertThat(cut.outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThat(cut.measures()).containsEntry("cut_off", 1L).containsEntry("held_nights", 1L);
        assertThatThrownBy(() -> new ChoirStonesAdapter.Watch(true, true, 1, 1, false)).hasMessageContaining("cut");
    }

    @Test
    void firstWeekLostToThirstFailsFromTheRealCore() {
        FirstWeekAdapter a = new FirstWeekAdapter(ActivityMode.AUTHORITATIVE);
        FirstWeek w = new FirstWeek(5);
        assertThatThrownBy(() -> FirstWeekAdapter.Week.of(w, false)).hasMessageContaining("in progress");
        for (int i = 0; i < FirstWeek.DAYS && !w.over() && !w.lost(); i++) {
            w.endDay();
        }
        FirstWeekAdapter.Week lost = FirstWeekAdapter.Week.of(w, false);
        assertThat(lost.survived()).as("no water all week").isFalse();
        assertThat(a.toReceipt(session("fw-1", GOAT), lost).outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThat(a.toReceipt(session("fw-2", GOAT), new FirstWeekAdapter.Week(true, 7, 60, false, false))
                .measures()).containsEntry("days", 7L).containsEntry("health", 60L).containsEntry("sick", 0L);
        assertThatThrownBy(() -> new FirstWeekAdapter.Week(true, 7, 0, false, false)).hasMessageContaining("health");
    }

    @Test
    void rootCellarBeforeTheDarkIsRefused() {
        RootCellarAdapter a = new RootCellarAdapter(ActivityMode.AUTHORITATIVE);
        RootCellar c = new RootCellar(3, 4);
        assertThatThrownBy(() -> RootCellarAdapter.Cellar.of(c, false)).hasMessageContaining("in progress");
        assertThat(a.toReceipt(session("rc-0", GOAT), RootCellarAdapter.Cellar.of(c, true)).outcome())
                .isEqualTo(ActivityOutcome.ABANDONED);
        assertThat(a.toReceipt(session("rc-1", GOAT), new RootCellarAdapter.Cellar(false, 5, 1, 9, false))
                .outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new RootCellarAdapter.Cellar(true, 13, 0, 9, false)).hasMessageContaining("jars");
    }

    @Test
    void supperAndSongOutcomes() {
        HomecomingSupperAdapter s = new HomecomingSupperAdapter(ActivityMode.AUTHORITATIVE);
        assertThat(s.toReceipt(session("hs-1", WREN), new HomecomingSupperAdapter.Supper(true, 9, 3, 0, false))
                .outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(s.toReceipt(session("hs-2", WREN), new HomecomingSupperAdapter.Supper(false, 9, 3, 2, false))
                .measures()).containsEntry("discontent", 2L);
        assertThatThrownBy(() -> new HomecomingSupperAdapter.Supper(true, 9, 3, 1, false))
                .hasMessageContaining("warm");

        ThirteenthSongAdapter t = new ThirteenthSongAdapter(ActivityMode.AUTHORITATIVE);
        assertThat(t.toReceipt(session("ts-1", WREN), new ThirteenthSongAdapter.Composing(true, 5, true, false))
                .outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(t.toReceipt(session("ts-2", WREN), new ThirteenthSongAdapter.Composing(false, 3, false, true))
                .outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new ThirteenthSongAdapter.Composing(true, 5, false, false))
                .hasMessageContaining("composed");
    }

    @Test
    void contestAllRoutesHubEightSettlesOnceAndReplaysFromTheJournal() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(RecordHuntAdapter.ACTIVITY_ID, ChoirStonesAdapter.ACTIVITY_ID,
                FirstWeekAdapter.ACTIVITY_ID, RootCellarAdapter.ACTIVITY_ID, HomecomingSupperAdapter.ACTIVITY_ID,
                ThirteenthSongAdapter.ACTIVITY_ID);
        AwardPolicy policy = new AwardPolicy(HomecomingSupperAdapter.ACTIVITY_ID, 1, "mastery.island-story",
                Map.of("seated", 2L, "courses", 5L), 100);
        r.setPolicy(policy);
        HomecomingSupperAdapter.Supper warm = new HomecomingSupperAdapter.Supper(true, 9, 3, 0, false);
        r.settle(HomecomingSupperAdapter.ACTIVITY_ID, session("route-hs", WREN), warm);
        r.settle(HomecomingSupperAdapter.ACTIVITY_ID, session("route-hs", WREN), warm);
        long once = r.total("life:hum-wren-2", "mastery.island-story");
        assertThat(once).isPositive();
        assertThat(r.journal()).hasSize(1);
        assertThat(ReceiptJournal.readAll(r.journal())).hasSize(1);

        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        restarted.setPolicy(policy);
        assertThat(restarted.replay(r.journal())).isEqualTo(1);
        assertThat(restarted.total("life:hum-wren-2", "mastery.island-story")).isEqualTo(once);
        assertThatThrownBy(() -> r.settle(ThirteenthSongAdapter.ACTIVITY_ID, session("route-x", GOAT), warm))
                .hasMessageContaining("expects");
    }
}
