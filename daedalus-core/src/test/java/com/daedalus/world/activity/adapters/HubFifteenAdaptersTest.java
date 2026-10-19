// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ProgressionLedger;
import com.daedalus.world.activity.ReceiptJournal;
import com.daedalus.world.audio.CricketThermometer;
import com.daedalus.world.battlefield.MarkRecapture;
import com.daedalus.world.brew.cellar.Preserve;
import com.daedalus.world.brew.parting.PartingJar;
import com.daedalus.world.brew.parting.PartingJars;
import com.daedalus.world.odds.match.BirthNightQuest;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.OptionalDouble;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** G187 exercises real game outcomes and the unchanged G12/G49 settlement boundary. */
class HubFifteenAdaptersTest {
    private static final ActivityParticipant OBSERVER = participant("observer", "observation");
    private static final ActivityParticipant LISTENER = participant("listener", "listening");
    private static final ActivityParticipant HAULER = participant("hauler", "hauling");

    private static ActivityParticipant participant(String id, String role) {
        return new ActivityParticipant("life:" + id, ActivityParticipant.Kind.LIFE, "animal", role);
    }

    private static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_882_000_000L);
    }

    private static MarkRecapture.Census census(double tagLoss) {
        // All hares are caught; removing every tag gives a deterministic misleading census.
        var settings = new MarkRecapture.Settings(240, 60, 0.999, tagLoss, 1, 0);
        return MarkRecapture.refuge(settings, 7).run();
    }

    private static BirthNightQuest muster(boolean correct, long seed) {
        BirthNightQuest q = new BirthNightQuest();
        q.guess(correct ? q.sameAnswer() : BirthNightQuest.NIGHTS + 1,
                correct ? q.nearAnswer() : BirthNightQuest.NIGHTS + 1, seed);
        return q;
    }

    private static PartingJars jars() {
        return new PartingJars(List.of(
                new PartingJar("a", "Moonbean", Preserve.Method.DRY, 1, 3, 3),
                new PartingJar("b", "fish", Preserve.Method.SALT, 1, 1, 2),
                new PartingJar("c", "fish", Preserve.Method.SALT, 1, 1, 2)), 0);
    }

    private static PartingJars fullShelf() {
        PartingJars p = jars();
        assertThat(p.plan("full", List.of("b", "c"))).isEqualTo(PartingJars.Outcome.FULL_SHELF);
        return p;
    }

    @Test
    void censusUsesCoreAccuracyAndNeverRunsOrHarvestsForTheHost() {
        var adapter = new TagAndCountAdapter(ActivityMode.AUTHORITATIVE);
        var good = census(0);
        var bad = census(1);
        assertThat(good.verdict()).isEqualTo(MarkRecapture.Verdict.ACCURATE);
        assertThat(bad.verdict()).isEqualTo(MarkRecapture.Verdict.MISLEADING);
        assertThat(adapter.toReceipt(session("census-good", OBSERVER), TagAndCountAdapter.Census.of(good, false))
                .outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        var failed = adapter.toReceipt(session("census-bad", OBSERVER), TagAndCountAdapter.Census.of(bad, false));
        assertThat(failed.outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThat(failed.measures()).containsEntry("recaptured", 0L).doesNotContainKey("truth");
        assertThat(adapter.toReceipt(session("census-abandon", OBSERVER), TagAndCountAdapter.Census.of(good, true))
                .outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> TagAndCountAdapter.Census.of(null, false)).hasMessageContaining("progress");
        assertThat(adapter.toReceipt(session("census-unrun", OBSERVER), TagAndCountAdapter.Census.of(null, true))
                .outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThat(good).isEqualTo(census(0));
    }

    @Test
    void censusRejectsMalformedFactsAndBoundsLargeMeasures() {
        assertThatThrownBy(() -> new TagAndCountAdapter.Census(1, 2, 2, true, false))
                .hasMessageContaining("counts");
        assertThatThrownBy(() -> TagAndCountAdapter.Census.of(new MarkRecapture.Census(1, 1, 0, 0), false))
                .hasMessageContaining("population");
        var receipt = new TagAndCountAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("large", OBSERVER),
                new TagAndCountAdapter.Census(Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MAX_VALUE, false, false));
        assertThat(receipt.measures()).containsEntry("marked", (long) TagAndCountAdapter.MAX_COUNT)
                .containsEntry("caught", (long) TagAndCountAdapter.MAX_COUNT)
                .containsEntry("recaptured", (long) TagAndCountAdapter.MAX_COUNT);
    }

    @Test
    void lanternsJudgeTheTwoGuessesRatherThanRandomCrewMatches() {
        var adapter = new BirthNightLanternsAdapter(ActivityMode.AUTHORITATIVE);
        BirthNightQuest pending = new BirthNightQuest();
        assertThatThrownBy(() -> BirthNightLanternsAdapter.Muster.of(pending, false)).hasMessageContaining("progress");
        assertThat(adapter.toReceipt(session("birth-unrun", OBSERVER), BirthNightLanternsAdapter.Muster.of(pending, true))
                .outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThat(pending.stage()).isEqualTo(BirthNightQuest.Stage.GUESSING);
        for (long seed = 1; seed <= 4; seed++) {
            BirthNightQuest good = muster(true, seed);
            String before = good.keeperLine();
            var snapshot = BirthNightLanternsAdapter.Muster.of(good, false);
            var receipt = adapter.toReceipt(session("birth-good-" + seed, OBSERVER), snapshot);
            assertThat(receipt.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
            assertThat(receipt.measures()).containsEntry("nods", 2L)
                    .containsEntry("closest_gap", (long) good.closestGap());
            assertThat(good.keeperLine()).isEqualTo(before);
            assertThat(snapshot).isEqualTo(BirthNightLanternsAdapter.Muster.of(muster(true, seed), false));
        }
        assertThat(adapter.toReceipt(session("birth-bad", OBSERVER), BirthNightLanternsAdapter.Muster.of(muster(false, 1), false))
                .outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThat(adapter.toReceipt(session("birth-left", OBSERVER), BirthNightLanternsAdapter.Muster.of(muster(true, 1), true))
                .outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new BirthNightLanternsAdapter.Muster(3, 0, false, false))
                .hasMessageContaining("range");
        assertThatThrownBy(() -> new BirthNightLanternsAdapter.Muster(2, 1, true, false))
                .hasMessageContaining("zero gap");
    }

    @Test
    void cricketUsesJudgedWarmAndSilentAnswersWithoutSerializingNanErrors() {
        var adapter = new CricketThermometerAdapter(ActivityMode.AUTHORITATIVE);
        boolean warmSeen = false;
        boolean coldSeen = false;
        for (long seed = 0; seed < 32; seed++) {
            CricketThermometer night = CricketThermometer.seeded(seed);
            boolean cold = night.tempC() < CricketThermometer.SILENT_BELOW_C;
            warmSeen |= !cold;
            coldSeen |= cold;
            OptionalDouble right = cold ? OptionalDouble.empty() : OptionalDouble.of(night.tempC());
            OptionalDouble wrong = cold ? OptionalDouble.of(20) : OptionalDouble.empty();
            var voices = night.voices();
            var snapshot = CricketThermometerAdapter.Listening.of(night.judge(right), false);
            assertThat(adapter.toReceipt(session("cricket-good-" + seed, LISTENER), snapshot).outcome())
                    .isEqualTo(ActivityOutcome.COMPLETED);
            assertThat(adapter.toReceipt(session("cricket-bad-" + seed, LISTENER),
                    CricketThermometerAdapter.Listening.of(night.judge(wrong), false)).outcome())
                    .isEqualTo(ActivityOutcome.FAILED);
            assertThat(adapter.toReceipt(session("cricket-left-" + seed, LISTENER),
                    CricketThermometerAdapter.Listening.of(night.judge(right), true)).outcome())
                    .isEqualTo(ActivityOutcome.ABANDONED);
            assertThat(night.voices()).isEqualTo(voices);
        }
        assertThat(warmSeen).isTrue();
        assertThat(coldSeen).isTrue();
        assertThatThrownBy(() -> CricketThermometerAdapter.Listening.of(null, false)).hasMessageContaining("progress");
        assertThat(adapter.toReceipt(session("cricket-unjudged", LISTENER), CricketThermometerAdapter.Listening.of(null, true))
                .outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new CricketThermometerAdapter.Listening(true, 99, false))
                .hasMessageContaining("100");
        assertThatThrownBy(() -> new CricketThermometerAdapter.Listening(false, 101, false))
                .hasMessageContaining("range");
    }

    @Test
    void jarsRequireAnAcceptedPlanAndPreserveCoreEventDeduplication() {
        var adapter = new PartingJarsAdapter(ActivityMode.AUTHORITATIVE);
        PartingJars pending = jars();
        assertThat(pending.plan("empty", List.of())).isEqualTo(PartingJars.Outcome.EMPTY);
        assertThat(pending.plan("unknown", List.of("nobody"))).isEqualTo(PartingJars.Outcome.UNKNOWN_FAMILY);
        assertThatThrownBy(() -> PartingJarsAdapter.Shelf.of(pending, false)).hasMessageContaining("progress");
        assertThat(adapter.toReceipt(session("jars-left", HAULER), PartingJarsAdapter.Shelf.of(pending, true))
                .outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThat(pending.last()).isNull();
        assertThat(pending.plan("short", List.of("a", "b", "c"))).isEqualTo(PartingJars.Outcome.SHORT);
        assertThat(adapter.toReceipt(session("jars-short", HAULER), PartingJarsAdapter.Shelf.of(pending, false))
                .outcome()).isEqualTo(ActivityOutcome.FAILED);
        PartingJars full = fullShelf();
        var snapshot = PartingJarsAdapter.Shelf.of(full, false);
        int step = full.quest().stepIndex();
        assertThat(adapter.toReceipt(session("jars-full", HAULER), snapshot).outcome())
                .isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(full.quest().stepIndex()).isEqualTo(step);
        assertThat(full.plan("full", List.of("a"))).isEqualTo(PartingJars.Outcome.DUPLICATE);
        assertThat(full.plan("invalid", List.of("nobody"))).isEqualTo(PartingJars.Outcome.UNKNOWN_FAMILY);
        assertThat(PartingJarsAdapter.Shelf.of(full, false)).isEqualTo(snapshot);
        assertThat(adapter.toReceipt(session("jars-abandon-full", HAULER), PartingJarsAdapter.Shelf.of(full, true))
                .outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new PartingJarsAdapter.Shelf(2, 3, 2, false)).hasMessageContaining("counts");
        var bounded = adapter.toReceipt(session("jars-large", HAULER),
                new PartingJarsAdapter.Shelf(Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MAX_VALUE, false));
        assertThat(bounded.measures()).containsEntry("orders", 64L).containsEntry("on_time", 64L)
                .containsEntry("best", 64L);
    }

    private record RouteCase(String id, Object snapshot, ActivityParticipant participant, String track, String measure) { }

    private static List<RouteCase> routes() {
        CricketThermometer night = CricketThermometer.seeded(3);
        OptionalDouble answer = night.tempC() < CricketThermometer.SILENT_BELOW_C
                ? OptionalDouble.empty() : OptionalDouble.of(night.tempC());
        return List.of(
                new RouteCase(TagAndCountAdapter.ACTIVITY_ID, TagAndCountAdapter.Census.of(census(0), false),
                        OBSERVER, "mastery.observation", "accurate"),
                new RouteCase(BirthNightLanternsAdapter.ACTIVITY_ID, BirthNightLanternsAdapter.Muster.of(muster(true, 3), false),
                        OBSERVER, "mastery.reckoning", "nods"),
                new RouteCase(CricketThermometerAdapter.ACTIVITY_ID,
                        CricketThermometerAdapter.Listening.of(night.judge(answer), false),
                        LISTENER, "mastery.listening", "correct"),
                new RouteCase(PartingJarsAdapter.ACTIVITY_ID, PartingJarsAdapter.Shelf.of(fullShelf(), false),
                        HAULER, "mastery.island-story", "on_time"));
    }

    @Test
    void contestAllDefaultsAreInactiveAndJournalledOnceForAllFourActivities() {
        ActivityRouter router = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        for (RouteCase c : routes()) {
            assertThat(router.activities()).contains(c.id());
            var s = session(c.id(), c.participant());
            var first = router.settle(c.id(), s, c.snapshot());
            assertThat(router.settle(c.id(), s, c.snapshot())).isEqualTo(first);
            assertThat(first).hasSize(1).allSatisfy(a -> assertThat(a.points()).isZero());
            assertThat(router.total(c.participant().instanceId(), c.track())).isZero();
        }
        assertThat(ReceiptJournal.readAll(router.journal())).hasSize(4);
        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(restarted.replay(router.journal())).isEqualTo(4);
        assertThat(restarted.replay(router.journal())).isZero();
        assertThat(restarted.journal()).isEqualTo(router.journal());
    }

    @Test
    void ownerEnabledPolicySettlesOnceReplaysAndRejectsChangedPayloadOrMode() {
        ActivityRouter router = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        for (RouteCase c : routes()) {
            AwardPolicy enabled = new AwardPolicy(c.id(), 1, c.track(), Map.of(c.measure(), 1L), 60);
            router.setPolicy(enabled);
            restarted.setPolicy(enabled);
            var s = session("enabled-" + c.id(), c.participant());
            var once = router.settle(c.id(), s, c.snapshot());
            assertThat(once).allSatisfy(a -> assertThat(a.points()).isPositive());
            assertThat(router.settle(c.id(), s, c.snapshot())).isEqualTo(once);
        }
        assertThat(restarted.replay(router.journal())).isEqualTo(4);
        assertThat(restarted.replay(router.journal())).isZero();
        for (RouteCase c : routes()) {
            assertThat(restarted.total(c.participant().instanceId(), c.track()))
                    .isEqualTo(router.total(c.participant().instanceId(), c.track()));
        }
        assertThatThrownBy(() -> router.settle(TagAndCountAdapter.ACTIVITY_ID,
                session("enabled-" + TagAndCountAdapter.ACTIVITY_ID, OBSERVER),
                TagAndCountAdapter.Census.of(census(1), false))).isInstanceOf(ProgressionLedger.ConflictException.class);
        assertThatThrownBy(() -> router.receipt(TagAndCountAdapter.ACTIVITY_ID, session("wrong-type", OBSERVER),
                PartingJarsAdapter.Shelf.of(fullShelf(), false))).hasMessageContaining("expects");
        ActivityRouter local = ActivityRouter.contestAll(ActivityMode.DEVICE_LOCAL);
        assertThatThrownBy(() -> local.replay(router.journal())).hasMessageContaining("AUTHORITATIVE");
        assertThat(local.journal()).isEmpty();
    }
}
