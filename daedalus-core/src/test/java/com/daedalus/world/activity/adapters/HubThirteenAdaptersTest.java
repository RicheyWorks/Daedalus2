// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ReceiptJournal;
import com.daedalus.world.audio.BuzzGarden;
import com.daedalus.world.audio.OwlFix;
import com.daedalus.world.battlefield.PatchForager;
import com.daedalus.world.odds.lockers.LockerQuest;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contest G160: receipts hub XIII over four newest landed games, driven by the real cores. */
class HubThirteenAdaptersTest {

    static final ActivityParticipant GULL =
            new ActivityParticipant("life:wreck-gull-1", ActivityParticipant.Kind.LIFE, "bird", "scouting");
    static final ActivityParticipant OWL =
            new ActivityParticipant("life:meadow-owl-2", ActivityParticipant.Kind.LIFE, "bird", "listening");
    static final ActivityParticipant VOLE =
            new ActivityParticipant("life:bramble-vole-3", ActivityParticipant.Kind.LIFE, "animal", "foraging");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_882_000_000L);
    }

    @Test
    void salvageLockersEnoughCompletesShortFailsDealingRefused() {
        SalvageLockersAdapter a = new SalvageLockersAdapter(ActivityMode.AUTHORITATIVE);
        int completed = 0;
        int failed = 0;
        for (long seed = 1; seed <= 40; seed++) {
            LockerQuest q = new LockerQuest(seed);
            if (seed == 1) {
                assertThatThrownBy(() -> SalvageLockersAdapter.Salvage.of(q, false)).hasMessageContaining("READY");
                assertThat(a.toReceipt(session("sl-a", GULL), SalvageLockersAdapter.Salvage.of(q, true)).outcome())
                        .isEqualTo(ActivityOutcome.ABANDONED);
            }
            while (q.stage() == LockerQuest.Stage.READY) {
                if (q.deal()) {
                    q.decide(true);
                }
            }
            var r = a.toReceipt(session("sl-" + seed, GULL), SalvageLockersAdapter.Salvage.of(q, false));
            boolean enough = q.stage() == LockerQuest.Stage.FOUND_ENOUGH;
            assertThat(r.outcome()).isEqualTo(enough ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            assertThat(r.measures()).containsEntry("found", (long) q.found()).containsEntry("rounds",
                    (long) LockerQuest.ROUNDS);
            if (enough) {
                completed++;
            } else {
                failed++;
            }
        }
        assertThat(completed).isPositive();
        assertThat(failed).isPositive();
        assertThatThrownBy(() -> new SalvageLockersAdapter.Salvage(true, 2, 0, 5, false)).hasMessageContaining("goal");
    }

    @Test
    void buzzGardenBestMatchCompletesOtherMatchFails() {
        BuzzGardenAdapter a = new BuzzGardenAdapter(ActivityMode.AUTHORITATIVE);
        int failures = 0;
        for (long seed = 1; seed <= 20; seed++) {
            BuzzGarden g = BuzzGarden.seeded(seed);
            BuzzGarden.Verdict good = g.judge(g.best());
            assertThat(a.toReceipt(session("bg-" + seed, OWL), BuzzGardenAdapter.Garden.of(good, false)).outcome())
                    .isEqualTo(ActivityOutcome.COMPLETED);
            List<Integer> swapped = new ArrayList<>(g.best());
            Collections.swap(swapped, 0, 1);
            BuzzGarden.Verdict v = g.judge(swapped);
            var r = a.toReceipt(session("bg-s" + seed, OWL), BuzzGardenAdapter.Garden.of(v, false));
            assertThat(r.outcome()).isEqualTo(v.best() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            assertThat(r.measures()).containsEntry("pollen", (long) v.pollen());
            if (!v.best()) {
                failures++;
            }
        }
        assertThat(failures).isPositive();
        assertThatThrownBy(() -> new BuzzGardenAdapter.Garden(true, 3, 9, false)).hasMessageContaining("best");
    }

    @Test
    void owlFixExactCellCompletesNearMissFails() {
        OwlFixAdapter a = new OwlFixAdapter(ActivityMode.AUTHORITATIVE);
        for (long seed = 1; seed <= 20; seed++) {
            OwlFix f = OwlFix.seeded(seed);
            var good = a.toReceipt(session("of-" + seed, OWL), OwlFixAdapter.Fix.of(f.judge(f.owl()), false));
            assertThat(good.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
            assertThat(good.measures()).containsEntry("score", 100L);
            OwlFix.Cell owl = f.owl();
            OwlFix.Cell near = new OwlFix.Cell(owl.x() == 0 ? 1 : owl.x() - 1, owl.y());
            OwlFix.Verdict v = f.judge(near);
            var r = a.toReceipt(session("of-n" + seed, OWL), OwlFixAdapter.Fix.of(v, false));
            assertThat(r.outcome()).isEqualTo(ActivityOutcome.FAILED);
            assertThat(r.measures().get("score")).isLessThan(100L);
        }
        assertThat(OwlFixAdapter.Fix.of(OwlFix.seeded(2).judge(null), false).score()).isZero();
        assertThatThrownBy(() -> new OwlFixAdapter.Fix(true, 80, false)).hasMessageContaining("100");
    }

    @Test
    void squirrelsWinterHoardedCompletesShortOrStarvedFails() {
        SquirrelsWinterAdapter a = new SquirrelsWinterAdapter(ActivityMode.AUTHORITATIVE);
        int hoarded = 0;
        for (long seed = 1; seed <= 10; seed++) {
            PatchForager p = PatchForager.meadow(PatchForager.Settings.DEFAULT, seed);
            for (PatchForager.Report rep : List.of(p.rate(p.optimalRate()), p.fixed(0.5), p.fixed(60))) {
                var r = a.toReceipt(session("sw-" + seed + "-" + rep.visits().size(), VOLE),
                        SquirrelsWinterAdapter.Hoard.of(rep, false));
                boolean h = rep.outcome() == PatchForager.Outcome.HOARDED;
                assertThat(r.outcome()).isEqualTo(h ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
                assertThat(r.measures().get("share_pct")).isBetween(0L, (long) SquirrelsWinterAdapter.MAX_SHARE_PCT);
                if (h) {
                    hoarded++;
                }
            }
        }
        assertThat(hoarded).isPositive();
        var gone = new SquirrelsWinterAdapter.Hoard(PatchForager.Outcome.STARVED, 10, 3, true);
        assertThat(a.toReceipt(session("sw-x", VOLE), gone).outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new SquirrelsWinterAdapter.Hoard(null, 1, 1, false)).hasMessageContaining("outcome");
    }

    @Test
    void contestAllRoutesHubThirteenSettlesOnceAndReplays() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(SalvageLockersAdapter.ACTIVITY_ID, BuzzGardenAdapter.ACTIVITY_ID,
                OwlFixAdapter.ACTIVITY_ID, SquirrelsWinterAdapter.ACTIVITY_ID);
        AwardPolicy policy = new AwardPolicy(OwlFixAdapter.ACTIVITY_ID, 1, "mastery.listening",
                Map.of("exact", 1L), 60);
        r.setPolicy(policy);
        OwlFixAdapter.Fix f = new OwlFixAdapter.Fix(true, 100, false);
        r.settle(OwlFixAdapter.ACTIVITY_ID, session("route-of", OWL), f);
        r.settle(OwlFixAdapter.ACTIVITY_ID, session("route-of", OWL), f);
        long once = r.total("life:meadow-owl-2", "mastery.listening");
        assertThat(once).isPositive();
        assertThat(ReceiptJournal.readAll(r.journal())).hasSize(1);
        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        restarted.setPolicy(policy);
        assertThat(restarted.replay(r.journal())).isEqualTo(1);
        assertThat(restarted.total("life:meadow-owl-2", "mastery.listening")).isEqualTo(once);
        assertThatThrownBy(() -> r.settle(BuzzGardenAdapter.ACTIVITY_ID, session("route-x", OWL), f))
                .hasMessageContaining("expects");
    }
}